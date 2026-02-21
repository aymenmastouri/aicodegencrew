"""
Oracle Schema Collector - Extracts schema-level database facts.

Detects:
- Schema names
- Tablespaces
- Users/Roles
- Synonyms
- Database links

Output: Schema facts for data_model.json
"""

import re
from pathlib import Path

from ..base import DimensionCollector, RawEntity


class OracleSchemaCollector(DimensionCollector):
    """Extracts Oracle schema-level facts."""

    DIMENSION = "database_schemas"

    def collect(self):
        """Collect schema facts from SQL files."""
        self._log_start()

        # Find SQL files (using _find_files for SKIP_DIRS pruning)
        sql_files = []
        for pattern in ["*.sql", "*.ddl", "*.pls"]:
            sql_files.extend(self._find_files(pattern))

        detected_schemas: set[str] = set()

        for sql_file in sql_files:
            try:
                content = self._read_file_content(sql_file)
                rel_path = self._relative_path(sql_file)

                # Extract schemas
                for schema in self._extract_schemas(rel_path, content):
                    if schema.name not in detected_schemas:
                        self.output.add_fact(schema)
                        detected_schemas.add(schema.name)

                # Extract tablespaces
                for ts in self._extract_tablespaces(rel_path, content):
                    self.output.add_fact(ts)

                # Extract synonyms
                for syn in self._extract_synonyms(rel_path, content):
                    self.output.add_fact(syn)

                # Extract database links
                for link in self._extract_db_links(rel_path, content):
                    self.output.add_fact(link)

            except Exception:
                continue

        # Also check Liquibase/Flyway for schema info
        for xml_file in self._find_files("*.xml"):
            if "liquibase" in str(xml_file).lower() or "changelog" in xml_file.name.lower():
                try:
                    content = self._read_file_content(xml_file)
                    rel_path = self._relative_path(xml_file)
                    for schema in self._extract_schemas_from_liquibase(rel_path, content):
                        if schema.name not in detected_schemas:
                            self.output.add_fact(schema)
                            detected_schemas.add(schema.name)
                except Exception:
                    continue

        self._log_end()
        return self.output

    def _extract_schemas(self, rel_path: str, content: str) -> list[RawEntity]:
        """Extract schema names from SQL."""
        facts = []

        # CREATE SCHEMA
        for match in re.finditer(r"CREATE\s+SCHEMA\s+(?:AUTHORIZATION\s+)?(\w+)", content, re.IGNORECASE):
            schema_name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1

            entity = RawEntity(name=schema_name, type="schema")
            entity.add_evidence(
                path=rel_path, line_start=line_num, line_end=line_num + 1,
                reason=f"CREATE SCHEMA {schema_name}",
            )
            facts.append(entity)

        # Schema references in qualified names (SCHEMA.TABLE)
        seen_schemas: set[str] = set()
        for match in re.finditer(r"(?:FROM|INTO|UPDATE|JOIN)\s+(\w+)\.(\w+)", content, re.IGNORECASE):
            schema_name = match.group(1)
            if schema_name.upper() in ("SYS", "SYSTEM", "PUBLIC", "DBA"):
                continue
            if schema_name not in seen_schemas:
                seen_schemas.add(schema_name)
                line_num = content[: match.start()].count("\n") + 1

                entity = RawEntity(name=schema_name, type="schema_reference")
                entity.add_evidence(
                    path=rel_path, line_start=line_num, line_end=line_num + 1,
                    reason="Schema reference in qualified name",
                )
                facts.append(entity)

        return facts

    def _extract_tablespaces(self, rel_path: str, content: str) -> list[RawEntity]:
        """Extract tablespace definitions."""
        facts = []

        # CREATE TABLESPACE
        for match in re.finditer(r"CREATE\s+(?:BIGFILE\s+)?TABLESPACE\s+(\w+)", content, re.IGNORECASE):
            ts_name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1

            entity = RawEntity(name=ts_name, type="tablespace")
            entity.add_evidence(
                path=rel_path, line_start=line_num, line_end=line_num + 5,
                reason=f"CREATE TABLESPACE {ts_name}",
            )
            facts.append(entity)

        # TABLESPACE clauses in CREATE TABLE
        seen: set[str] = set()
        for match in re.finditer(r"TABLESPACE\s+(\w+)", content, re.IGNORECASE):
            ts_name = match.group(1)
            if ts_name not in seen:
                seen.add(ts_name)
                line_num = content[: match.start()].count("\n") + 1

                entity = RawEntity(name=ts_name, type="tablespace_reference")
                entity.add_evidence(
                    path=rel_path, line_start=line_num, line_end=line_num + 1,
                    reason=f"TABLESPACE {ts_name} clause",
                )
                facts.append(entity)

        return facts

    def _extract_synonyms(self, rel_path: str, content: str) -> list[RawEntity]:
        """Extract synonym definitions."""
        facts = []

        for match in re.finditer(
            r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:PUBLIC\s+)?SYNONYM\s+(\w+)\s+FOR\s+(\S+)", content, re.IGNORECASE
        ):
            syn_name = match.group(1)
            target = match.group(2)
            line_num = content[: match.start()].count("\n") + 1

            entity = RawEntity(
                name=syn_name, type="synonym",
                metadata={"target": target},
            )
            entity.add_evidence(
                path=rel_path, line_start=line_num, line_end=line_num + 1,
                reason=f"CREATE SYNONYM {syn_name} FOR {target}",
            )
            facts.append(entity)

        return facts

    def _extract_db_links(self, rel_path: str, content: str) -> list[RawEntity]:
        """Extract database link definitions."""
        facts = []

        for match in re.finditer(
            r"CREATE\s+(?:SHARED\s+)?(?:PUBLIC\s+)?DATABASE\s+LINK\s+(\w+)", content, re.IGNORECASE
        ):
            link_name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1

            entity = RawEntity(name=link_name, type="database_link")
            entity.add_evidence(
                path=rel_path, line_start=line_num, line_end=line_num + 5,
                reason=f"CREATE DATABASE LINK {link_name}",
            )
            facts.append(entity)

        return facts

    def _extract_schemas_from_liquibase(self, rel_path: str, content: str) -> list[RawEntity]:
        """Extract schema references from Liquibase."""
        facts = []

        seen: set[str] = set()
        for match in re.finditer(r'schemaName\s*=\s*["\'](\w+)["\']', content, re.IGNORECASE):
            schema_name = match.group(1)
            if schema_name not in seen:
                seen.add(schema_name)
                line_num = content[: match.start()].count("\n") + 1

                entity = RawEntity(name=schema_name, type="schema")
                entity.add_evidence(
                    path=rel_path, line_start=line_num, line_end=line_num + 1,
                    reason=f"Liquibase schemaName={schema_name}",
                )
                facts.append(entity)

        return facts
