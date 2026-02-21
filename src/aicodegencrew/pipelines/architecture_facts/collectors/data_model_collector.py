"""
DataModelCollector - Aggregates data model facts.

Collects:
- JPA Entities (@Entity)
- Database tables (from SQL/migrations)
- Entity relationships

Output -> data_model.json
"""

import re
from pathlib import Path

from .base import CollectorOutput, DimensionCollector, RawEntity, RelationHint
from .database import MigrationCollector, OracleTableCollector


class DataModelCollector(DimensionCollector):
    """
    Aggregates data model facts from JPA entities and database schemas.
    """

    DIMENSION = "data_model"

    # JPA patterns
    ENTITY_PATTERN = re.compile(r"@Entity")
    TABLE_PATTERN = re.compile(r'@Table\s*\(\s*name\s*=\s*["\']([^"\']+)["\']')
    CLASS_PATTERN = re.compile(r"^(?:public\s+)?class\s+([A-Z]\w*)", re.MULTILINE)

    # Field patterns
    ID_PATTERN = re.compile(r"@Id")
    COLUMN_PATTERN = re.compile(r"@Column\s*\(([^)]*)\)")

    # Relationship patterns
    ONE_TO_MANY = re.compile(r"@OneToMany")
    MANY_TO_ONE = re.compile(r"@ManyToOne")
    ONE_TO_ONE = re.compile(r"@OneToOne")
    MANY_TO_MANY = re.compile(r"@ManyToMany")

    def __init__(self, repo_path: Path, container_id: str = "backend"):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect all data model facts."""
        self._log_start()

        # Collect JPA entities
        self._collect_jpa_entities()

        # Collect from database collectors
        self._collect_database_schema()

        # Collect migrations
        self._collect_migrations()

        self._log_end()
        return self.output

    def _collect_jpa_entities(self):
        """Collect JPA entity facts."""
        java_files = self._find_files("*.java")

        for java_file in java_files:
            content = self._read_file_content(java_file)

            if not self.ENTITY_PATTERN.search(content):
                continue

            lines = self._read_file(java_file)
            rel_path = self._relative_path(java_file)

            # Get class name
            class_match = self.CLASS_PATTERN.search(content)
            if not class_match:
                continue

            entity_name = class_match.group(1)
            class_line = self._find_line_number(lines, f"class {entity_name}")

            # Get table name if specified
            table_match = self.TABLE_PATTERN.search(content)
            table_name = table_match.group(1) if table_match else entity_name.lower()

            # Extract fields
            fields = self._extract_entity_fields(content)

            # Detect relationships
            relationships = self._extract_relationships(content, entity_name)

            entity = RawEntity(
                name=entity_name,
                type="entity",
                columns=fields,
                metadata={
                    "table_name": table_name,
                    "file_path": rel_path,
                },
            )

            entity.add_evidence(
                path=rel_path,
                line_start=max(1, class_line - 2),
                line_end=class_line + 5,
                reason=f"JPA Entity: {entity_name} -> {table_name}",
            )

            self.output.add_fact(entity)

            # Add relationship hints
            for rel in relationships:
                self.output.add_relation(rel)

    def _extract_entity_fields(self, content: str) -> list[dict]:
        """Extract entity field definitions."""
        fields = []

        # Simple field pattern: private Type name;
        field_pattern = re.compile(
            r"(?:@\w+(?:\([^)]*\))?\s*)*"
            r"private\s+(\w+(?:<[^>]+>)?)\s+(\w+)\s*;"
        )

        for match in field_pattern.finditer(content):
            field_type = match.group(1)
            field_name = match.group(2)

            # Skip collection relationships (handled separately)
            # Only skip known collection types, not all generics (Map, Optional are data fields)
            collection_prefixes = ("List", "Set", "Collection", "Iterable")
            if field_type in collection_prefixes or any(field_type.startswith(p + "<") for p in collection_prefixes):
                continue

            field_area = content[max(0, match.start() - 100) : match.start()]

            field = {
                "name": field_name,
                "type": field_type,
            }

            # Check if it's the ID
            if self.ID_PATTERN.search(field_area):
                field["primary_key"] = True

            # Check for column annotation
            col_match = self.COLUMN_PATTERN.search(field_area)
            if col_match:
                col_config = col_match.group(1)
                if "nullable = false" in col_config or "nullable=false" in col_config:
                    field["nullable"] = False
                name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', col_config)
                if name_match:
                    field["column_name"] = name_match.group(1)

            fields.append(field)

        return fields

    def _extract_relationships(self, content: str, entity_name: str) -> list[RelationHint]:
        """Extract JPA relationship annotations."""
        relationships = []

        # Pattern to find relationship + field
        rel_patterns = [
            (self.ONE_TO_MANY, "one_to_many"),
            (self.MANY_TO_ONE, "many_to_one"),
            (self.ONE_TO_ONE, "one_to_one"),
            (self.MANY_TO_MANY, "many_to_many"),
        ]

        for pattern, rel_type in rel_patterns:
            for match in pattern.finditer(content):
                # Find the target type
                after_annotation = content[match.end() : match.end() + 200]
                type_match = re.search(r"(?:List|Set|Collection)?<?\s*(\w+)>?\s+\w+", after_annotation)

                if type_match:
                    target_entity = type_match.group(1)

                    # Skip primitives
                    if target_entity.lower() in ("string", "long", "integer", "boolean", "date"):
                        continue

                    relation = RelationHint(
                        from_name=entity_name,
                        to_name=target_entity,
                        type=rel_type,
                        from_stereotype_hint="entity",
                        to_stereotype_hint="entity",
                    )

                    relationships.append(relation)

        return relationships

    def _collect_database_schema(self):
        """Collect database schema from SQL files."""
        table_collector = OracleTableCollector(self.repo_path)
        table_output = table_collector.collect()

        for fact in table_output.facts:
            self.output.add_fact(fact)

        for relation in table_output.relations:
            self.output.add_relation(relation)

    def _collect_migrations(self):
        """Collect migration facts."""
        migration_collector = MigrationCollector(self.repo_path)
        migration_output = migration_collector.collect()

        for fact in migration_output.facts:
            # Store migrations separately in metadata
            fact.tags.append("migration")
            self.output.add_fact(fact)
