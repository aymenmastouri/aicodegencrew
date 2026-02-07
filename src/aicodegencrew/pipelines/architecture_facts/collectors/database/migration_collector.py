"""
MigrationCollector - Extracts database migration and SQL script facts.

Detects:
- Liquibase changelogs (XML/YAML)
- Flyway migrations (SQL/Java)
- DB-Admin correction/fix scripts
- Custom SQL scripts (init, setup, data patches)
- Migration history and dependencies

Output feeds -> data_model.json
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..base import DimensionCollector, CollectorOutput, RawEntity, RawFact
from .....shared.utils.logger import logger


class MigrationCollector(DimensionCollector):
    """
    Extracts database migration and SQL script facts.
    """

    DIMENSION = "migrations"

    # Skip directories
    SKIP_DIRS = {'node_modules', 'dist', 'build', 'target', '.git', 'bin'}

    # Known SQL script directories
    SQL_SCRIPT_DIRS = [
        'sql', 'scripts', 'db', 'database', 'migration', 'migrations',
        'patches', 'fixes', 'corrections', 'admin', 'dba',
        'init', 'setup', 'data', 'ddl', 'dml',
    ]

    def __init__(self, repo_path: Path, container_id: str = "database"):
        super().__init__(repo_path)
        self.container_id = container_id
        self._processed_files: Set[Path] = set()

    def collect(self) -> CollectorOutput:
        """Collect migration and SQL script facts."""
        self._log_start()

        # Detect and collect Liquibase
        self._collect_liquibase()

        # Detect and collect Flyway
        self._collect_flyway()

        # Detect and collect custom SQL scripts (DB-Admin, corrections, etc.)
        self._collect_custom_sql_scripts()

        self._log_end()
        return self.output

    def _should_skip(self, path: Path) -> bool:
        """Check if path should be skipped."""
        path_str = str(path).lower()
        return any(skip_dir in path_str for skip_dir in self.SKIP_DIRS)
    
    def _collect_liquibase(self):
        """Collect Liquibase changelog facts."""
        # Find Liquibase files
        patterns = [
            "**/db/changelog/**/*.xml",
            "**/db/changelog/**/*.yaml",
            "**/db/changelog/**/*.yml",
            "**/liquibase/**/*.xml",
        ]

        changelog_files = []
        for pattern in patterns:
            changelog_files.extend(self._find_files(pattern.split('/')[-1]))

        if not changelog_files:
            return

        logger.info(f"[MigrationCollector] Found {len(changelog_files)} Liquibase files")

        for changelog_file in changelog_files:
            self._process_liquibase_file(changelog_file)
            self._processed_files.add(changelog_file)
    
    def _process_liquibase_file(self, file_path: Path):
        """Process a Liquibase changelog file."""
        content = self._read_file_content(file_path)
        rel_path = self._relative_path(file_path)
        
        if file_path.suffix == '.xml':
            self._parse_liquibase_xml(content, rel_path)
        else:
            self._parse_liquibase_yaml(content, rel_path)
    
    def _parse_liquibase_xml(self, content: str, file_path: str):
        """Parse Liquibase XML changelog."""
        # Find changesets
        changeset_pattern = re.compile(
            r'<changeSet\s+[^>]*id\s*=\s*["\']([^"\']+)["\'][^>]*author\s*=\s*["\']([^"\']+)["\']',
            re.IGNORECASE | re.DOTALL
        )
        
        # Find table operations
        create_table_pattern = re.compile(r'<createTable\s+tableName\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
        add_column_pattern = re.compile(r'<addColumn\s+tableName\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
        drop_table_pattern = re.compile(r'<dropTable\s+tableName\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
        
        for match in changeset_pattern.finditer(content):
            changeset_id = match.group(1)
            author = match.group(2)
            line_num = content[:match.start()].count('\n') + 1
            
            # Find what this changeset does
            # Look for operations between this changeset and the next
            start = match.end()
            next_match = changeset_pattern.search(content, start)
            end = next_match.start() if next_match else len(content)
            changeset_content = content[start:end]
            
            operations = []
            tables_affected = set()
            
            for table_match in create_table_pattern.finditer(changeset_content):
                operations.append(f"CREATE TABLE {table_match.group(1)}")
                tables_affected.add(table_match.group(1))
            
            for table_match in add_column_pattern.finditer(changeset_content):
                operations.append(f"ADD COLUMN to {table_match.group(1)}")
                tables_affected.add(table_match.group(1))
            
            for table_match in drop_table_pattern.finditer(changeset_content):
                operations.append(f"DROP TABLE {table_match.group(1)}")
                tables_affected.add(table_match.group(1))
            
            migration = RawFact(
                name=f"changeset-{changeset_id}",
                metadata={
                    "type": "liquibase_changeset",
                    "id": changeset_id,
                    "author": author,
                    "operations": operations[:5],
                    "tables": list(tables_affected),
                }
            )
            
            migration.tags.append("liquibase")
            
            migration.add_evidence(
                path=file_path,
                line_start=line_num,
                line_end=line_num + 10,
                reason=f"Liquibase changeset: {changeset_id} by {author}"
            )
            
            self.output.add_fact(migration)
    
    def _parse_liquibase_yaml(self, content: str, file_path: str):
        """Parse Liquibase YAML changelog."""
        # Simple YAML parsing for changesets
        changeset_pattern = re.compile(r'changeSet:\s*\n\s+id:\s*["\']?([^"\'\n]+)', re.MULTILINE)
        
        for match in changeset_pattern.finditer(content):
            changeset_id = match.group(1).strip()
            line_num = content[:match.start()].count('\n') + 1
            
            migration = RawFact(
                name=f"changeset-{changeset_id}",
                metadata={
                    "type": "liquibase_changeset",
                    "id": changeset_id,
                    "format": "yaml",
                }
            )
            
            migration.tags.append("liquibase")
            
            migration.add_evidence(
                path=file_path,
                line_start=line_num,
                line_end=line_num + 5,
                reason=f"Liquibase changeset (YAML): {changeset_id}"
            )
            
            self.output.add_fact(migration)
    
    def _collect_flyway(self):
        """Collect Flyway migration facts."""
        # Flyway naming: V{version}__{description}.sql
        flyway_pattern = re.compile(r'^[VUR]\d+.*\.sql$', re.IGNORECASE)
        
        # Find potential Flyway directories
        migration_dirs = [
            "db/migration",
            "src/main/resources/db/migration",
            "flyway/sql",
        ]
        
        flyway_files = []
        for migration_dir in migration_dirs:
            dir_path = self.repo_path / migration_dir
            if dir_path.exists():
                for sql_file in dir_path.glob("*.sql"):
                    if flyway_pattern.match(sql_file.name):
                        flyway_files.append(sql_file)
        
        if not flyway_files:
            # Search more broadly
            for sql_file in self._find_files("*.sql"):
                if flyway_pattern.match(sql_file.name):
                    flyway_files.append(sql_file)
        
        if not flyway_files:
            return
        
        logger.info(f"[MigrationCollector] Found {len(flyway_files)} Flyway migrations")
        
        for flyway_file in flyway_files:
            self._process_flyway_file(flyway_file)
    
    def _process_flyway_file(self, file_path: Path):
        """Process a Flyway migration file."""
        content = self._read_file_content(file_path)
        rel_path = self._relative_path(file_path)
        
        # Parse filename: V1__Create_table.sql
        name_pattern = re.compile(r'^([VUR])(\d+(?:\.\d+)*)__(.+)\.sql$', re.IGNORECASE)
        match = name_pattern.match(file_path.name)
        
        if match:
            migration_type = match.group(1).upper()
            version = match.group(2)
            description = match.group(3).replace('_', ' ')
        else:
            migration_type = "V"
            version = "unknown"
            description = file_path.stem
        
        # Detect what the migration does
        operations = []
        tables = set()
        
        if re.search(r'CREATE\s+TABLE', content, re.IGNORECASE):
            for m in re.finditer(r'CREATE\s+TABLE\s+(?:\w+\.)?(\w+)', content, re.IGNORECASE):
                operations.append(f"CREATE TABLE {m.group(1)}")
                tables.add(m.group(1))
        
        if re.search(r'ALTER\s+TABLE', content, re.IGNORECASE):
            for m in re.finditer(r'ALTER\s+TABLE\s+(?:\w+\.)?(\w+)', content, re.IGNORECASE):
                operations.append(f"ALTER TABLE {m.group(1)}")
                tables.add(m.group(1))
        
        if re.search(r'DROP\s+TABLE', content, re.IGNORECASE):
            for m in re.finditer(r'DROP\s+TABLE\s+(?:\w+\.)?(\w+)', content, re.IGNORECASE):
                operations.append(f"DROP TABLE {m.group(1)}")
                tables.add(m.group(1))
        
        migration = RawFact(
            name=f"flyway-{version}",
            metadata={
                "type": "flyway_migration",
                "version": version,
                "migration_type": migration_type,
                "description": description,
                "operations": operations[:10],
                "tables": list(tables),
            }
        )
        
        migration.tags.append("flyway")
        if migration_type == "R":
            migration.tags.append("repeatable")
        elif migration_type == "U":
            migration.tags.append("undo")
        
        migration.add_evidence(
            path=rel_path,
            line_start=1,
            line_end=min(20, content.count('\n') + 1),
            reason=f"Flyway migration: {version} - {description}"
        )

        self.output.add_fact(migration)
        self._processed_files.add(file_path)

    def _collect_custom_sql_scripts(self):
        """Collect custom SQL scripts (DB-Admin, corrections, init, etc.)."""
        sql_files: List[Path] = []

        # Search in known SQL directories
        for sql_dir in self.SQL_SCRIPT_DIRS:
            for search_path in self.repo_path.rglob(sql_dir):
                if not search_path.is_dir() or self._should_skip(search_path):
                    continue

                for sql_file in search_path.glob("*.sql"):
                    if sql_file not in self._processed_files:
                        sql_files.append(sql_file)

        # Also search for SQL files with specific naming patterns
        patterns = [
            "*.sql",
            "*_fix*.sql",
            "*_patch*.sql",
            "*_correction*.sql",
            "*_hotfix*.sql",
            "*init*.sql",
            "*setup*.sql",
            "*seed*.sql",
        ]

        for pattern in patterns:
            for sql_file in self.repo_path.rglob(pattern):
                if sql_file not in self._processed_files and not self._should_skip(sql_file):
                    sql_files.append(sql_file)

        # Remove duplicates
        sql_files = list(set(sql_files) - self._processed_files)

        if not sql_files:
            return

        logger.info(f"[MigrationCollector] Found {len(sql_files)} custom SQL scripts")

        for sql_file in sql_files:
            self._process_custom_sql_file(sql_file)

    def _process_custom_sql_file(self, file_path: Path):
        """Process a custom SQL script file."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return

        rel_path = self._relative_path(file_path)

        # Categorize the script based on name and content
        script_type = self._categorize_sql_script(file_path.name, content, rel_path)

        # Detect operations and affected tables
        operations = []
        tables = set()

        # DDL operations
        for pattern, op_type in [
            (r'CREATE\s+TABLE', 'CREATE TABLE'),
            (r'ALTER\s+TABLE', 'ALTER TABLE'),
            (r'DROP\s+TABLE', 'DROP TABLE'),
            (r'CREATE\s+INDEX', 'CREATE INDEX'),
            (r'CREATE\s+VIEW', 'CREATE VIEW'),
            (r'CREATE\s+OR\s+REPLACE\s+VIEW', 'CREATE VIEW'),
            (r'CREATE\s+PROCEDURE', 'CREATE PROCEDURE'),
            (r'CREATE\s+FUNCTION', 'CREATE FUNCTION'),
            (r'CREATE\s+TRIGGER', 'CREATE TRIGGER'),
        ]:
            for m in re.finditer(pattern + r'\s+(?:\w+\.)?(\w+)', content, re.IGNORECASE):
                operations.append(f"{op_type} {m.group(1)}")
                tables.add(m.group(1))

        # DML operations
        for pattern, op_type in [
            (r'INSERT\s+INTO', 'INSERT'),
            (r'UPDATE\s+', 'UPDATE'),
            (r'DELETE\s+FROM', 'DELETE'),
        ]:
            for m in re.finditer(pattern + r'\s+(?:\w+\.)?(\w+)', content, re.IGNORECASE):
                operations.append(f"{op_type} {m.group(1)}")
                tables.add(m.group(1))

        script = RawFact(
            name=file_path.stem,
            metadata={
                "type": script_type,
                "file": rel_path,
                "operations": operations[:15],  # Limit
                "tables": list(tables)[:20],
                "line_count": content.count('\n') + 1,
            }
        )

        script.tags.append("sql_script")
        script.tags.append(script_type.replace('_', '-'))

        # Add path-based tags
        path_lower = rel_path.lower()
        if 'admin' in path_lower or 'dba' in path_lower:
            script.tags.append("admin")
        if 'fix' in path_lower or 'patch' in path_lower or 'correction' in path_lower:
            script.tags.append("correction")
        if 'init' in path_lower or 'setup' in path_lower:
            script.tags.append("initialization")

        script.add_evidence(
            path=rel_path,
            line_start=1,
            line_end=min(30, content.count('\n') + 1),
            reason=f"SQL script: {file_path.name} ({script_type})"
        )

        self.output.add_fact(script)
        self._processed_files.add(file_path)

    def _categorize_sql_script(self, filename: str, content: str, path: str) -> str:
        """Categorize a SQL script based on its name and content."""
        filename_lower = filename.lower()
        path_lower = path.lower()
        content_lower = content.lower()

        # Check filename patterns
        if any(p in filename_lower for p in ['fix', 'patch', 'correction', 'hotfix']):
            return 'correction_script'
        if any(p in filename_lower for p in ['init', 'setup', 'bootstrap']):
            return 'init_script'
        if any(p in filename_lower for p in ['seed', 'data', 'insert']):
            return 'data_script'
        if any(p in filename_lower for p in ['cleanup', 'purge', 'archive']):
            return 'cleanup_script'
        if any(p in filename_lower for p in ['rollback', 'undo', 'revert']):
            return 'rollback_script'

        # Check path patterns
        if any(p in path_lower for p in ['admin', 'dba']):
            return 'admin_script'
        if any(p in path_lower for p in ['correction', 'fixes', 'patches']):
            return 'correction_script'

        # Check content patterns
        if re.search(r'CREATE\s+TABLE', content, re.IGNORECASE):
            return 'ddl_script'
        if re.search(r'INSERT\s+INTO|UPDATE\s+|DELETE\s+FROM', content, re.IGNORECASE):
            return 'dml_script'
        if re.search(r'CREATE\s+(PROCEDURE|FUNCTION|TRIGGER|PACKAGE)', content, re.IGNORECASE):
            return 'plsql_script'
        if re.search(r'GRANT|REVOKE', content, re.IGNORECASE):
            return 'security_script'

        return 'sql_script'
