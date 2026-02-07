"""
OracleTableCollector - Extracts database table facts from SQL/DDL.

Supports multiple dialects:
- Oracle (VARCHAR2, NUMBER, etc.)
- PostgreSQL (VARCHAR, INTEGER, etc.)
- MySQL/MariaDB
- SQL Server
- Generic ANSI SQL

Detects:
- CREATE TABLE statements
- Column definitions (various data types)
- Constraints (PK, FK, UNIQUE)
- Indexes
- Views

Output feeds -> data_model.json
"""

import re
from pathlib import Path
from typing import Dict, List, Optional

from ..base import DimensionCollector, CollectorOutput, RawEntity, RelationHint
from .....shared.utils.logger import logger


class OracleTableCollector(DimensionCollector):
    """
    Extracts database table facts from SQL files.
    """
    
    DIMENSION = "database_tables"
    
    # Patterns
    CREATE_TABLE_PATTERN = re.compile(
        r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:(\w+)\.)?(\w+)\s*\(',
        re.IGNORECASE | re.DOTALL
    )
    
    COLUMN_PATTERN = re.compile(
        r'(\w+)\s+(VARCHAR2?|NUMBER|INTEGER|INT|BIGINT|DECIMAL|DATE|TIMESTAMP|BOOLEAN|CLOB|BLOB|TEXT)(?:\s*\(([^)]+)\))?',
        re.IGNORECASE
    )
    
    PRIMARY_KEY_PATTERN = re.compile(
        r'(?:CONSTRAINT\s+(\w+)\s+)?PRIMARY\s+KEY\s*\(([^)]+)\)',
        re.IGNORECASE
    )
    
    FOREIGN_KEY_PATTERN = re.compile(
        r'(?:CONSTRAINT\s+(\w+)\s+)?FOREIGN\s+KEY\s*\(([^)]+)\)\s+REFERENCES\s+(?:(\w+)\.)?(\w+)\s*\(([^)]+)\)',
        re.IGNORECASE
    )
    
    CREATE_INDEX_PATTERN = re.compile(
        r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+(\w+)\s+ON\s+(?:(\w+)\.)?(\w+)\s*\(([^)]+)\)',
        re.IGNORECASE
    )
    
    CREATE_VIEW_PATTERN = re.compile(
        r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+(?:(\w+)\.)?(\w+)\s+AS',
        re.IGNORECASE
    )
    
    def __init__(self, repo_path: Path, container_id: str = "database"):
        super().__init__(repo_path)
        self.container_id = container_id
    
    def collect(self) -> CollectorOutput:
        """Collect database table facts."""
        self._log_start()
        
        # Find SQL files
        sql_files = self._find_files("*.sql")
        logger.info(f"[OracleTableCollector] Found {len(sql_files)} SQL files")
        
        for sql_file in sql_files:
            self._process_sql_file(sql_file)
        
        self._log_end()
        return self.output
    
    def _process_sql_file(self, file_path: Path):
        """Process a SQL file."""
        content = self._read_file_content(file_path)
        lines = self._read_file(file_path)
        rel_path = self._relative_path(file_path)
        
        # Extract tables
        for match in self.CREATE_TABLE_PATTERN.finditer(content):
            schema = match.group(1)
            table_name = match.group(2)
            
            # Find the full CREATE TABLE statement
            start_pos = match.start()
            # Find matching closing parenthesis
            paren_count = 0
            end_pos = start_pos
            for i, char in enumerate(content[start_pos:]):
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                    if paren_count == 0:
                        end_pos = start_pos + i + 1
                        break
            
            table_content = content[start_pos:end_pos]
            line_num = content[:start_pos].count('\n') + 1
            
            # Extract columns
            columns = self._extract_columns(table_content)
            
            # Extract primary key
            pk_match = self.PRIMARY_KEY_PATTERN.search(table_content)
            pk_columns = []
            if pk_match:
                pk_columns = [c.strip() for c in pk_match.group(2).split(',')]
            
            # Extract foreign keys
            foreign_keys = self._extract_foreign_keys(table_content)
            
            # Create entity
            entity = RawEntity(
                name=table_name,
                type="table",
                schema=schema,
                columns=columns,
            )
            
            if pk_columns:
                entity.metadata["primary_key"] = pk_columns
            if foreign_keys:
                entity.constraints = foreign_keys
                
            entity.add_evidence(
                path=rel_path,
                line_start=line_num,
                line_end=line_num + table_content.count('\n'),
                reason=f"CREATE TABLE: {table_name}"
            )
            
            self.output.add_fact(entity)
            
            # Create relations for foreign keys
            for fk in foreign_keys:
                relation = RelationHint(
                    from_name=table_name,
                    to_name=fk["references_table"],
                    type="references",
                    from_stereotype_hint="table",
                    to_stereotype_hint="table",
                )
                self.output.add_relation(relation)
        
        # Extract views
        for match in self.CREATE_VIEW_PATTERN.finditer(content):
            schema = match.group(1)
            view_name = match.group(2)
            line_num = content[:match.start()].count('\n') + 1
            
            view = RawEntity(
                name=view_name,
                type="view",
                schema=schema,
            )
            
            view.add_evidence(
                path=rel_path,
                line_start=line_num,
                line_end=line_num + 5,
                reason=f"CREATE VIEW: {view_name}"
            )
            
            self.output.add_fact(view)
        
        # Extract indexes
        for match in self.CREATE_INDEX_PATTERN.finditer(content):
            index_name = match.group(1)
            table_name = match.group(3)
            columns = match.group(4)
            line_num = content[:match.start()].count('\n') + 1
            
            is_unique = 'UNIQUE' in content[max(0, match.start()-10):match.start()].upper()
            
            # Add index info to table if we have it
            # For now, create as metadata
            index_fact = RawEntity(
                name=index_name,
                type="index",
                metadata={
                    "table": table_name,
                    "columns": [c.strip() for c in columns.split(',')],
                    "unique": is_unique,
                }
            )
            
            index_fact.add_evidence(
                path=rel_path,
                line_start=line_num,
                line_end=line_num + 1,
                reason=f"CREATE INDEX: {index_name} on {table_name}"
            )
            
            self.output.add_fact(index_fact)
    
    def _extract_columns(self, table_content: str) -> List[Dict]:
        """Extract column definitions."""
        columns = []
        
        for match in self.COLUMN_PATTERN.finditer(table_content):
            col_name = match.group(1)
            col_type = match.group(2).upper()
            col_size = match.group(3)
            
            # Skip if it looks like a constraint keyword
            if col_name.upper() in ('PRIMARY', 'FOREIGN', 'CONSTRAINT', 'UNIQUE', 'CHECK'):
                continue
            
            col = {
                "name": col_name,
                "type": col_type,
            }
            if col_size:
                col["size"] = col_size
            
            # Check for NOT NULL
            col_line = table_content[match.start():].split('\n')[0]
            if 'NOT NULL' in col_line.upper():
                col["nullable"] = False
            
            columns.append(col)
        
        return columns
    
    def _extract_foreign_keys(self, table_content: str) -> List[Dict]:
        """Extract foreign key constraints."""
        fks = []
        
        for match in self.FOREIGN_KEY_PATTERN.finditer(table_content):
            constraint_name = match.group(1)
            columns = [c.strip() for c in match.group(2).split(',')]
            ref_schema = match.group(3)
            ref_table = match.group(4)
            ref_columns = [c.strip() for c in match.group(5).split(',')]
            
            fk = {
                "type": "foreign_key",
                "columns": columns,
                "references_table": ref_table,
                "references_columns": ref_columns,
            }
            if constraint_name:
                fk["name"] = constraint_name
            if ref_schema:
                fk["references_schema"] = ref_schema
            
            fks.append(fk)
        
        return fks
