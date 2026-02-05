"""
Oracle View Collector - Extracts database view facts.

Detects:
- CREATE VIEW
- CREATE MATERIALIZED VIEW
- View columns
- View dependencies

Output: View facts for data_model.json
"""

import re
from pathlib import Path
from typing import List

from ..base import DimensionCollector, CollectorOutput, RawEntity, RawEvidence, RelationHint


class OracleViewCollector(DimensionCollector):
    """Extracts Oracle view facts."""
    
    def collect(self) -> CollectorOutput:
        """Collect view facts from SQL files."""
        facts: List[RawEntity] = []
        relations: List[RelationHint] = []
        
        # Find SQL files
        sql_patterns = ['*.sql', '*.ddl', '*.vw']
        sql_files = []
        for pattern in sql_patterns:
            sql_files.extend(self.repo_path.rglob(pattern))
        
        for sql_file in sql_files:
            try:
                content = sql_file.read_text(encoding='utf-8', errors='ignore')
                
                # Regular views
                facts.extend(self._extract_views(sql_file, content))
                
                # Materialized views
                facts.extend(self._extract_materialized_views(sql_file, content))
                
                # Extract view-table dependencies
                relations.extend(self._extract_view_dependencies(sql_file, content))
                
            except Exception:
                continue
        
        return CollectorOutput(facts=facts, relations=relations)
    
    def _extract_views(self, file_path: Path, content: str) -> List[RawEntity]:
        """Extract regular view definitions."""
        facts = []
        
        # CREATE [OR REPLACE] VIEW [schema.]viewname AS SELECT...
        view_pattern = re.compile(
            r'CREATE\s+(?:OR\s+REPLACE\s+)?(?:FORCE\s+)?VIEW\s+'
            r'(?:(\w+)\.)?(\w+)\s*'
            r'(?:\([^)]+\))?\s*AS\s*'
            r'(SELECT\s+.+?)(?:;|$)',
            re.IGNORECASE | re.DOTALL
        )
        
        for match in view_pattern.finditer(content):
            schema = match.group(1) or ""
            view_name = match.group(2)
            select_stmt = match.group(3)[:200]  # Truncate for evidence
            line_num = content[:match.start()].count('\n') + 1
            line_end = content[:match.end()].count('\n') + 1
            
            # Extract columns from SELECT
            columns = self._extract_view_columns(select_stmt)
            
            facts.append(RawEntity(
                name=view_name,
                entity_type="view",
                file_path=file_path,
                description=f"View: {schema + '.' if schema else ''}{view_name}",
                evidence=RawEvidence(
                    file_path=file_path,
                    line_start=line_num,
                    line_end=min(line_end, line_num + 30),
                    reason=f"CREATE VIEW {view_name}",
                ),
                columns=columns,
                schema=schema,
            ))
        
        return facts
    
    def _extract_materialized_views(self, file_path: Path, content: str) -> List[RawEntity]:
        """Extract materialized view definitions."""
        facts = []
        
        # CREATE MATERIALIZED VIEW
        mv_pattern = re.compile(
            r'CREATE\s+MATERIALIZED\s+VIEW\s+'
            r'(?:(\w+)\.)?(\w+)\s*'
            r'(?:BUILD\s+(?:IMMEDIATE|DEFERRED)\s*)?'
            r'(?:REFRESH\s+(?:FAST|COMPLETE|FORCE)\s*(?:ON\s+(?:DEMAND|COMMIT))?\s*)?'
            r'AS\s*(SELECT\s+.+?)(?:;|$)',
            re.IGNORECASE | re.DOTALL
        )
        
        for match in mv_pattern.finditer(content):
            schema = match.group(1) or ""
            mv_name = match.group(2)
            select_stmt = match.group(3)[:200]
            line_num = content[:match.start()].count('\n') + 1
            line_end = content[:match.end()].count('\n') + 1
            
            # Detect refresh type
            refresh_type = "unknown"
            if 'REFRESH FAST' in content[match.start():match.end()].upper():
                refresh_type = "fast"
            elif 'REFRESH COMPLETE' in content[match.start():match.end()].upper():
                refresh_type = "complete"
            
            facts.append(RawEntity(
                name=mv_name,
                entity_type="materialized_view",
                file_path=file_path,
                description=f"Materialized view: {mv_name} (refresh: {refresh_type})",
                evidence=RawEvidence(
                    file_path=file_path,
                    line_start=line_num,
                    line_end=min(line_end, line_num + 40),
                    reason=f"CREATE MATERIALIZED VIEW {mv_name}",
                ),
                schema=schema,
                tags=[f"refresh_{refresh_type}"],
            ))
        
        return facts
    
    def _extract_view_columns(self, select_stmt: str) -> List[str]:
        """Extract column names from SELECT statement."""
        columns = []
        
        # Simple extraction: between SELECT and FROM
        select_match = re.search(
            r'SELECT\s+(.+?)\s+FROM',
            select_stmt,
            re.IGNORECASE | re.DOTALL
        )
        
        if select_match:
            column_part = select_match.group(1)
            # Split by comma, handle aliases
            for col in column_part.split(','):
                col = col.strip()
                # Handle "expr AS alias" or "expr alias"
                alias_match = re.search(r'(?:AS\s+)?(\w+)\s*$', col, re.IGNORECASE)
                if alias_match:
                    columns.append(alias_match.group(1))
        
        return columns[:20]  # Limit
    
    def _extract_view_dependencies(self, file_path: Path, content: str) -> List[RelationHint]:
        """Extract which tables a view depends on."""
        relations = []
        
        # Find view names and their source tables
        view_pattern = re.compile(
            r'CREATE\s+(?:OR\s+REPLACE\s+)?(?:MATERIALIZED\s+)?VIEW\s+'
            r'(?:\w+\.)?(\w+)\s*.+?AS\s*SELECT.+?FROM\s+(.+?)(?:WHERE|GROUP|ORDER|;|$)',
            re.IGNORECASE | re.DOTALL
        )
        
        for match in view_pattern.finditer(content):
            view_name = match.group(1)
            from_clause = match.group(2)
            
            # Extract table names from FROM clause
            # Handle: table, schema.table, table alias, JOINs
            table_matches = re.finditer(
                r'(?:FROM|JOIN)\s+(?:(\w+)\.)?(\w+)(?:\s+(\w+))?',
                from_clause,
                re.IGNORECASE
            )
            
            for tm in table_matches:
                table_name = tm.group(2)
                # Skip if it looks like a keyword
                if table_name.upper() in ('SELECT', 'WHERE', 'AND', 'OR', 'ON', 'AS'):
                    continue
                
                relations.append(RelationHint(
                    from_name=view_name,
                    to_name=table_name,
                    relation_type="view_depends_on",
                    evidence=RawEvidence(
                        file_path=file_path,
                        line_start=content[:match.start()].count('\n') + 1,
                        line_end=content[:match.end()].count('\n') + 1,
                        reason=f"View {view_name} references table {table_name}",
                    ),
                ))
        
        return relations
