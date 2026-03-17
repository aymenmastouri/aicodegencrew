"""Python Data Model Specialist — Extracts Python ORM model facts.

Detects:
- SQLAlchemy models (Base, DeclarativeBase, db.Model)
- SQLAlchemy columns, relationships
- Django models (models.Model)
- Django fields, ForeignKey, ManyToManyField
"""

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawEntity, RelationHint


class PythonDataModelCollector(DimensionCollector):
    """Extracts Python ORM data model facts."""

    DIMENSION = "data_model"

    # SQLAlchemy patterns
    SQLALCHEMY_MODEL_PATTERN = re.compile(r"class\s+(\w+)\s*\(\s*(?:Base|DeclarativeBase|db\.Model)\s*\)")
    SQLALCHEMY_COLUMN = re.compile(r"(\w+)\s*=\s*(?:Column|mapped_column|db\.Column)\s*\(\s*(\w+)")
    SQLALCHEMY_RELATIONSHIP = re.compile(r"(\w+)\s*=\s*(?:relationship|db\.relationship)\s*\(\s*['\"](\w+)['\"]")

    # Django patterns
    DJANGO_MODEL_PATTERN = re.compile(r"class\s+(\w+)\s*\(\s*(?:models\.Model|Model)\s*\)")
    DJANGO_FIELD_PATTERN = re.compile(r"(\w+)\s*=\s*models\.(\w+Field)\s*\(")
    DJANGO_FK_PATTERN = re.compile(r"(\w+)\s*=\s*models\.(?:ForeignKey|OneToOneField)\s*\(\s*['\"]?(\w+)")
    DJANGO_M2M_PATTERN = re.compile(r"(\w+)\s*=\s*models\.ManyToManyField\s*\(\s*['\"]?(\w+)")

    def __init__(self, repo_path: Path, container_id: str = "backend"):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect Python data model facts: SQLAlchemy and Django ORM."""
        self._log_start()

        py_files = self._find_files("*.py")

        for py_file in py_files:
            content = self._read_file_content(py_file)
            if not content:
                continue

            rel_path = self._relative_path(py_file)
            lines = self._read_file(py_file)

            # SQLAlchemy models
            for match in self.SQLALCHEMY_MODEL_PATTERN.finditer(content):
                entity_name = match.group(1)
                class_line = self._find_line_number(lines, f"class {entity_name}")

                # Extract columns
                class_start = match.end()
                next_class = re.search(r"^class\s+\w+", content[class_start:], re.MULTILINE)
                class_body = content[class_start:class_start + next_class.start()] if next_class else content[class_start:]

                fields = []
                for col_match in self.SQLALCHEMY_COLUMN.finditer(class_body):
                    fields.append({"name": col_match.group(1), "type": col_match.group(2)})

                # Extract table name
                tablename_match = re.search(r'__tablename__\s*=\s*["\']([^"\']+)["\']', class_body)
                table_name = tablename_match.group(1) if tablename_match else entity_name.lower()

                entity = RawEntity(
                    name=entity_name,
                    type="entity",
                    columns=fields,
                    metadata={"table_name": table_name, "file_path": rel_path, "orm": "sqlalchemy"},
                )
                entity.add_evidence(
                    path=rel_path, line_start=max(1, class_line - 2), line_end=class_line + 5,
                    reason=f"SQLAlchemy model: {entity_name} -> {table_name}",
                )
                self.output.add_fact(entity)

                # Relationships — use specific cardinality types consistent with JPA
                for rel_match in self.SQLALCHEMY_RELATIONSHIP.finditer(class_body):
                    field_name = rel_match.group(1)
                    target = rel_match.group(2)
                    # Heuristic: if field is plural -> one_to_many, else -> many_to_one
                    rel_type = "one_to_many" if field_name.endswith("s") else "many_to_one"
                    self.output.add_relation(RelationHint(
                        from_name=entity_name, to_name=target, type=rel_type,
                        from_stereotype_hint="entity", to_stereotype_hint="entity",
                    ))

            # Django models
            for match in self.DJANGO_MODEL_PATTERN.finditer(content):
                entity_name = match.group(1)
                class_line = self._find_line_number(lines, f"class {entity_name}")

                class_start = match.end()
                next_class = re.search(r"^class\s+\w+", content[class_start:], re.MULTILINE)
                class_body = content[class_start:class_start + next_class.start()] if next_class else content[class_start:]

                fields = []
                for field_match in self.DJANGO_FIELD_PATTERN.finditer(class_body):
                    fields.append({"name": field_match.group(1), "type": field_match.group(2)})

                # Table name: Django uses app_modelname by default
                table_name = entity_name.lower()
                meta_match = re.search(r'db_table\s*=\s*["\']([^"\']+)["\']', class_body)
                if meta_match:
                    table_name = meta_match.group(1)

                entity = RawEntity(
                    name=entity_name,
                    type="entity",
                    columns=fields,
                    metadata={"table_name": table_name, "file_path": rel_path, "orm": "django"},
                )
                entity.add_evidence(
                    path=rel_path, line_start=max(1, class_line - 2), line_end=class_line + 5,
                    reason=f"Django model: {entity_name} -> {table_name}",
                )
                self.output.add_fact(entity)

                # ForeignKey relationships
                for fk_match in self.DJANGO_FK_PATTERN.finditer(class_body):
                    target = fk_match.group(2)
                    self.output.add_relation(RelationHint(
                        from_name=entity_name, to_name=target, type="many_to_one",
                        from_stereotype_hint="entity", to_stereotype_hint="entity",
                    ))

                # ManyToManyField relationships
                for m2m_match in self.DJANGO_M2M_PATTERN.finditer(class_body):
                    target = m2m_match.group(2)
                    self.output.add_relation(RelationHint(
                        from_name=entity_name, to_name=target, type="many_to_many",
                        from_stereotype_hint="entity", to_stereotype_hint="entity",
                    ))

        self._log_end()
        return self.output
