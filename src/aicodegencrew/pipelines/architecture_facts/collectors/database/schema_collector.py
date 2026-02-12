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

from ..base import CollectorOutput, DimensionCollector, RawEntity, RawEvidence, RelationHint


class OracleSchemaCollector(DimensionCollector):
    """Extracts Oracle schema-level facts."""

    def collect(self) -> CollectorOutput:
        """Collect schema facts from SQL files."""
        facts: list[RawEntity] = []
        relations: list[RelationHint] = []

        # Find SQL files
        sql_patterns = ["*.sql", "*.ddl", "*.pls"]
        sql_files = []
        for pattern in sql_patterns:
            sql_files.extend(self.repo_path.rglob(pattern))

        detected_schemas = set()

        for sql_file in sql_files:
            try:
                content = sql_file.read_text(encoding="utf-8", errors="ignore").upper()

                # Extract schemas
                schemas = self._extract_schemas(sql_file, content)
                for schema in schemas:
                    if schema.name not in detected_schemas:
                        facts.append(schema)
                        detected_schemas.add(schema.name)

                # Extract tablespaces
                facts.extend(self._extract_tablespaces(sql_file, content))

                # Extract synonyms
                facts.extend(self._extract_synonyms(sql_file, content))

                # Extract database links
                facts.extend(self._extract_db_links(sql_file, content))

            except Exception:
                continue

        # Also check Liquibase/Flyway for schema info
        for xml_file in self.repo_path.rglob("*.xml"):
            if "liquibase" in str(xml_file).lower() or "changelog" in xml_file.name.lower():
                try:
                    content = xml_file.read_text(encoding="utf-8", errors="ignore")
                    schemas = self._extract_schemas_from_liquibase(xml_file, content)
                    for schema in schemas:
                        if schema.name not in detected_schemas:
                            facts.append(schema)
                            detected_schemas.add(schema.name)
                except Exception:
                    continue

        return CollectorOutput(facts=facts, relations=relations)

    def _extract_schemas(self, file_path: Path, content: str) -> list[RawEntity]:
        """Extract schema names from SQL."""
        facts = []

        # CREATE SCHEMA
        schema_matches = re.finditer(r"CREATE\s+SCHEMA\s+(?:AUTHORIZATION\s+)?(\w+)", content, re.IGNORECASE)
        for match in schema_matches:
            schema_name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1

            facts.append(
                RawEntity(
                    name=schema_name,
                    entity_type="schema",
                    file_path=file_path,
                    description=f"Database schema: {schema_name}",
                    evidence=RawEvidence(
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num + 1,
                        reason=f"CREATE SCHEMA {schema_name}",
                    ),
                )
            )

        # Schema references in qualified names (SCHEMA.TABLE)
        qualified_matches = re.finditer(r"(?:FROM|INTO|UPDATE|JOIN)\s+(\w+)\.(\w+)", content, re.IGNORECASE)
        seen_schemas = set()
        for match in qualified_matches:
            schema_name = match.group(1)
            # Skip common keywords
            if schema_name.upper() in ("SYS", "SYSTEM", "PUBLIC", "DBA"):
                continue
            if schema_name not in seen_schemas:
                seen_schemas.add(schema_name)
                line_num = content[: match.start()].count("\n") + 1

                facts.append(
                    RawEntity(
                        name=schema_name,
                        entity_type="schema_reference",
                        file_path=file_path,
                        description=f"Schema reference: {schema_name}",
                        evidence=RawEvidence(
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num + 1,
                            reason="Schema reference in qualified name",
                        ),
                    )
                )

        return facts

    def _extract_tablespaces(self, file_path: Path, content: str) -> list[RawEntity]:
        """Extract tablespace definitions."""
        facts = []

        # CREATE TABLESPACE
        ts_matches = re.finditer(r"CREATE\s+(?:BIGFILE\s+)?TABLESPACE\s+(\w+)", content, re.IGNORECASE)
        for match in ts_matches:
            ts_name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1

            facts.append(
                RawEntity(
                    name=ts_name,
                    entity_type="tablespace",
                    file_path=file_path,
                    description=f"Tablespace: {ts_name}",
                    evidence=RawEvidence(
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num + 5,
                        reason=f"CREATE TABLESPACE {ts_name}",
                    ),
                )
            )

        # TABLESPACE clauses in CREATE TABLE
        ts_refs = re.finditer(r"TABLESPACE\s+(\w+)", content, re.IGNORECASE)
        seen = set()
        for match in ts_refs:
            ts_name = match.group(1)
            if ts_name not in seen:
                seen.add(ts_name)
                line_num = content[: match.start()].count("\n") + 1

                facts.append(
                    RawEntity(
                        name=ts_name,
                        entity_type="tablespace_reference",
                        file_path=file_path,
                        description=f"Tablespace reference: {ts_name}",
                        evidence=RawEvidence(
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num + 1,
                            reason=f"TABLESPACE {ts_name} clause",
                        ),
                    )
                )

        return facts

    def _extract_synonyms(self, file_path: Path, content: str) -> list[RawEntity]:
        """Extract synonym definitions."""
        facts = []

        # CREATE SYNONYM
        syn_matches = re.finditer(
            r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:PUBLIC\s+)?SYNONYM\s+(\w+)\s+FOR\s+(\S+)", content, re.IGNORECASE
        )
        for match in syn_matches:
            syn_name = match.group(1)
            target = match.group(2)
            line_num = content[: match.start()].count("\n") + 1

            facts.append(
                RawEntity(
                    name=syn_name,
                    entity_type="synonym",
                    file_path=file_path,
                    description=f"Synonym {syn_name} -> {target}",
                    evidence=RawEvidence(
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num + 1,
                        reason=f"CREATE SYNONYM {syn_name} FOR {target}",
                    ),
                )
            )

        return facts

    def _extract_db_links(self, file_path: Path, content: str) -> list[RawEntity]:
        """Extract database link definitions."""
        facts = []

        # CREATE DATABASE LINK
        link_matches = re.finditer(
            r"CREATE\s+(?:SHARED\s+)?(?:PUBLIC\s+)?DATABASE\s+LINK\s+(\w+)", content, re.IGNORECASE
        )
        for match in link_matches:
            link_name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1

            facts.append(
                RawEntity(
                    name=link_name,
                    entity_type="database_link",
                    file_path=file_path,
                    description=f"Database link: {link_name}",
                    evidence=RawEvidence(
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num + 5,
                        reason=f"CREATE DATABASE LINK {link_name}",
                    ),
                )
            )

        return facts

    def _extract_schemas_from_liquibase(self, file_path: Path, content: str) -> list[RawEntity]:
        """Extract schema references from Liquibase."""
        facts = []

        # schemaName attribute
        schema_matches = re.finditer(r'schemaName\s*=\s*["\'](\w+)["\']', content, re.IGNORECASE)
        seen = set()
        for match in schema_matches:
            schema_name = match.group(1)
            if schema_name not in seen:
                seen.add(schema_name)
                line_num = content[: match.start()].count("\n") + 1

                facts.append(
                    RawEntity(
                        name=schema_name,
                        entity_type="schema",
                        file_path=file_path,
                        description=f"Schema from Liquibase: {schema_name}",
                        evidence=RawEvidence(
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num + 1,
                            reason=f"Liquibase schemaName={schema_name}",
                        ),
                    )
                )

        return facts
