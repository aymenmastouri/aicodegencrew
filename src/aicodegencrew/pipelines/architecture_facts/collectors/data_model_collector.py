"""
DataModelCollector - Aggregates data model facts.

Thin router that delegates ecosystem-specific collection to specialist
collectors via the EcosystemRegistry.

Cross-cutting (language-agnostic) collection:
- Database tables (from SQL/DDL files via OracleTableCollector)
- Migrations (Flyway, Liquibase via MigrationCollector)

Delegated to ecosystems:
- Java: SpringDataModelCollector (JPA @Entity, relationships)
- Python: PythonDataModelCollector (SQLAlchemy, Django ORM)

Output -> data_model.json
"""

from pathlib import Path

from ....shared.ecosystems.registry import EcosystemRegistry
from .base import CollectorOutput, DimensionCollector
from .database import MigrationCollector, OracleTableCollector


class DataModelCollector(DimensionCollector):
    """
    Aggregates data model facts from database schemas and ORM models.

    Thin router: runs cross-cutting database/migration collection, then
    delegates to ecosystem specialists via EcosystemRegistry.
    """

    DIMENSION = "data_model"

    def __init__(self, repo_path: Path, container_id: str = "backend"):
        super().__init__(repo_path)
        self.container_id = container_id
        self._registry = EcosystemRegistry()

    def collect(self) -> CollectorOutput:
        """Collect all data model facts."""
        self._log_start()

        # Cross-cutting: database schema from SQL files
        self._collect_database_schema()

        # Cross-cutting: migration facts
        self._collect_migrations()

        # Delegate to ecosystem specialists
        for eco in self._registry.detect(self.repo_path):
            facts, rels = eco.collect_dimension(self.DIMENSION, self.repo_path, self.container_id)
            for f in facts:
                self.output.add_fact(f)
            for r in rels:
                self.output.add_relation(r)

        self._log_end()
        return self.output

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
