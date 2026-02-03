"""Database Collector - Extracts database architecture facts.

Detects:
- Liquibase (XML/YAML changelogs)
- Flyway (migration scripts)
- SQL scripts
- Database tables and schemas
- Stored procedures
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple, Set

from .base_collector import (
    BaseCollector,
    CollectedComponent,
    CollectedInterface,
    CollectedRelation,
    CollectedEvidence,
)


class DatabaseCollector(BaseCollector):
    """Collects database and migration tool architecture facts."""
    
    def __init__(self, project_root: Path, container_id: str = "infrastructure"):
        super().__init__(project_root, container_id)
        self._component_counter = 0
    
    def collect(self) -> Tuple[List[CollectedComponent], List[CollectedInterface], List[CollectedRelation], Dict[str, CollectedEvidence]]:
        """Collect all database-related architecture facts."""
        self._detect_liquibase()
        self._detect_flyway()
        self._detect_sql_scripts()
        
        return self.components, self.interfaces, self.relations, self.evidence
    
    def _create_evidence(self, file_path: Path, reason: str, line_start: int = 1, line_end: int = 1) -> str:
        """Create an evidence entry and return its ID."""
        try:
            rel_path = str(file_path.relative_to(self.repo_path))
        except ValueError:
            rel_path = str(file_path)
        
        return self._add_evidence(rel_path, line_start, line_end, reason, prefix="ev_db")
    
    def _create_component(self, name: str, stereotype: str, file_path: str, 
                         evidence_ids: List[str], metadata: Dict = None) -> CollectedComponent:
        """Create a component."""
        cid = f"cmp_db_{self._component_counter:04d}"
        self._component_counter += 1
        
        component = CollectedComponent(
            id=cid,
            container=self.container_id,
            name=name,
            stereotype=stereotype,
            file_path=file_path,
            evidence_ids=evidence_ids,
            module=self._derive_module_from_path(file_path)
        )
        self.components.append(component)
        return component
    
    def _detect_liquibase(self):
        """Detect Liquibase configuration and changelogs."""
        # Look for Liquibase files
        liquibase_patterns = [
            "**/db/changelog/**/*.xml",
            "**/liquibase/**/*.xml",
            "**/db.changelog*.xml",
            "**/db/changelog/**/*.yaml",
            "**/db/changelog/**/*.yml",
            "**/liquibase.properties",
        ]
        
        liquibase_files = []
        for pattern in liquibase_patterns:
            liquibase_files.extend(self.repo_path.rglob(pattern))
        
        if not liquibase_files:
            return
        
        # Create Liquibase component
        evidence_ids = []
        tables = set()
        
        for file_path in liquibase_files:
            if file_path.suffix in ['.xml', '.yaml', '.yml']:
                file_tables = self._parse_liquibase_changelog(file_path)
                tables.update(file_tables)
                
                reason = f"Liquibase changelog: {file_path.name}"
                if file_tables:
                    reason += f" (tables: {', '.join(list(file_tables)[:5])})"
                eid = self._create_evidence(file_path, reason)
                evidence_ids.append(eid)
            elif file_path.name == "liquibase.properties":
                eid = self._create_evidence(file_path, "Liquibase configuration file")
                evidence_ids.append(eid)
        
        if evidence_ids:
            try:
                rel_path = str(liquibase_files[0].relative_to(self.repo_path))
            except ValueError:
                rel_path = str(liquibase_files[0])
            
            self._create_component(
                name="liquibase_migration",
                stereotype="database_migration",
                file_path=rel_path,
                evidence_ids=evidence_ids,
            )
            
            # Create database schema component if tables found
            if tables:
                self._create_database_schema_component(tables, evidence_ids, rel_path)
    
    def _parse_liquibase_changelog(self, file_path: Path) -> Set[str]:
        """Parse Liquibase changelog for table names."""
        tables = set()
        
        try:
            if file_path.suffix == '.xml':
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                # Use regex to find tableName attributes (namespace-agnostic)
                table_matches = re.findall(r'tableName\s*=\s*["\']([^"\']+)["\']', content)
                tables.update(table_matches)
            
            elif file_path.suffix in ['.yaml', '.yml']:
                # Simple YAML parsing for table names
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                # Look for tableName: xxx pattern
                table_matches = re.findall(r'tableName:\s*([a-zA-Z_][a-zA-Z0-9_]*)', content)
                tables.update(table_matches)
        
        except Exception:
            # Ignore parsing errors
            pass
        
        return tables
    
    def _detect_flyway(self):
        """Detect Flyway migrations."""
        # Look for Flyway migration folders and config
        migration_patterns = [
            "**/db/migration/**/*.sql",
            "**/flyway/**/*.sql",
            "**/migrations/**/*.sql",
        ]
        
        config_files = list(self.repo_path.rglob("flyway.conf")) + \
                      list(self.repo_path.rglob("flyway.properties"))
        
        migration_files = []
        for pattern in migration_patterns:
            migration_files.extend(self.repo_path.rglob(pattern))
        
        # Filter for Flyway naming convention: V{version}__{description}.sql
        flyway_migrations = [
            f for f in migration_files 
            if re.match(r'V\d+__.+\.sql', f.name, re.IGNORECASE)
        ]
        
        if not flyway_migrations and not config_files:
            return
        
        # Create Flyway component
        evidence_ids = []
        tables = set()
        
        for config_file in config_files:
            eid = self._create_evidence(config_file, f"Flyway configuration: {config_file.name}")
            evidence_ids.append(eid)
        
        for migration_file in flyway_migrations:
            file_tables = self._parse_sql_for_tables(migration_file)
            tables.update(file_tables)
            
            reason = f"Flyway migration: {migration_file.name}"
            eid = self._create_evidence(migration_file, reason)
            evidence_ids.append(eid)
            
            # Also create SQL script component
            try:
                rel_path = str(migration_file.relative_to(self.repo_path))
            except ValueError:
                rel_path = str(migration_file)
            
            self._create_component(
                name=migration_file.stem,
                stereotype="sql_script",
                file_path=rel_path,
                evidence_ids=[eid],
            )
        
        if evidence_ids:
            try:
                rel_path = str((config_files[0] if config_files else flyway_migrations[0]).relative_to(self.repo_path))
            except ValueError:
                rel_path = str(config_files[0] if config_files else flyway_migrations[0])
            
            self._create_component(
                name="flyway_migration",
                stereotype="database_migration",
                file_path=rel_path,
                evidence_ids=evidence_ids,
            )
            
            # Create database schema component if tables found
            if tables:
                self._create_database_schema_component(tables, evidence_ids, rel_path)
    
    def _detect_sql_scripts(self):
        """Detect standalone SQL scripts."""
        # Find SQL files not in migration folders
        all_sql_files = list(self.repo_path.rglob("*.sql"))
        
        # Filter out files already processed by Flyway
        migration_folders = ['migration', 'migrations', 'flyway', 'liquibase', 'changelog']
        standalone_sql = [
            f for f in all_sql_files
            if not any(folder in f.parts for folder in migration_folders)
            and not re.match(r'V\d+__.+\.sql', f.name, re.IGNORECASE)
        ]
        
        tables_all = set()
        
        for sql_file in standalone_sql:
            tables = self._parse_sql_for_tables(sql_file)
            tables_all.update(tables)
            
            # Determine script type
            script_type = self._determine_sql_script_type(sql_file)
            
            reason = f"SQL script: {sql_file.name}"
            if tables:
                reason += f" (tables: {', '.join(list(tables)[:3])})"
            
            eid = self._create_evidence(sql_file, reason)
            
            try:
                rel_path = str(sql_file.relative_to(self.repo_path))
            except ValueError:
                rel_path = str(sql_file)
            
            self._create_component(
                name=sql_file.stem,
                stereotype="sql_script",
                file_path=rel_path,
                evidence_ids=[eid],
            )
        
        # Create database schema component if tables found
        if tables_all:
            evidence_ids = [
                eid for comp in self.components 
                if comp.stereotype == "sql_script"
                for eid in comp.evidence_ids
            ]
            if evidence_ids:
                self._create_database_schema_component(tables_all, evidence_ids[:10], "database/schema")
    
    def _parse_sql_for_tables(self, file_path: Path) -> Set[str]:
        """Parse SQL file for table names."""
        tables = set()
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Find CREATE TABLE statements
            create_table_pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:(\w+)\.)?(\w+)'
            matches = re.findall(create_table_pattern, content, re.IGNORECASE)
            
            for schema, table in matches:
                if table and table.upper() not in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']:
                    tables.add(table)
            
        except Exception:
            pass
        
        return tables
    
    def _determine_sql_script_type(self, file_path: Path) -> str:
        """Determine the type of SQL script based on content."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore').lower()
            
            if 'create table' in content or 'alter table' in content:
                return 'schema'
            elif 'create function' in content or 'create procedure' in content:
                return 'stored_procedure'
            elif 'create view' in content:
                return 'view'
            elif 'insert into' in content:
                return 'data'
            else:
                return 'unknown'
        except Exception:
            return 'unknown'
    
    def _create_database_schema_component(self, tables: Set[str], evidence_ids: List[str], file_path: str):
        """Create a database schema component with table information."""
        self._create_component(
            name="database_schema",
            stereotype="database_schema",
            file_path=file_path,
            evidence_ids=evidence_ids[:10],  # Limit evidence to avoid bloat
        )
