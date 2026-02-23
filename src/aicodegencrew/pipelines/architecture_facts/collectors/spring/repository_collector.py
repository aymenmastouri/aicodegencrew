"""
SpringRepositoryCollector - Extracts repository layer facts.

Detects:
- @Repository classes
- JpaRepository / CrudRepository interfaces
- Custom query methods (@Query)
- Entity associations

Output feeds -> components.json (repositories)
             -> relations (repository -> entity)
"""

import re
from pathlib import Path

from .....shared.utils.logger import logger
from ..base import CollectorOutput, DimensionCollector, RawComponent, RelationHint


class SpringRepositoryCollector(DimensionCollector):
    """
    Extracts repository layer facts from Spring Boot code.
    """

    DIMENSION = "spring_repositories"

    # Patterns
    REPOSITORY_PATTERN = re.compile(r"@Repository")
    INTERFACE_PATTERN = re.compile(r"^(?:public\s+)?interface\s+([A-Z]\w*)", re.MULTILINE)

    # JpaRepository<Entity, ID>
    EXTENDS_REPO_PATTERN = re.compile(r"interface\s+(\w+)\s+extends\s+(?:Jpa|Crud|Paging|Mongo)Repository\s*<\s*(\w+)")

    # Custom @Query
    QUERY_PATTERN = re.compile(r'@Query\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']')

    # Method patterns for derived queries
    DERIVED_QUERY_PATTERN = re.compile(
        r"(?:List|Optional|Set|Page|Slice)?\s*<?(\w+)>?\s+(findBy|countBy|deleteBy|existsBy)(\w+)\s*\("
    )

    def __init__(self, repo_path: Path, container_id: str = "backend"):
        super().__init__(repo_path)
        self.container_id = container_id
        self._java_root: Path | None = None
        self._entity_names: set[str] = set()

    def collect(self) -> CollectorOutput:
        """Collect repository layer facts."""
        self._log_start()

        self._java_root = self._find_java_root()
        if not self._java_root:
            logger.debug("[SpringRepositoryCollector] No Java/Kotlin source root in %s (skipping)", self.repo_path)
            return self.output

        # Collect Java and Kotlin files
        java_files = self._find_files("*.java", self._java_root)
        kotlin_files = self._find_files("*.kt", self._java_root)
        all_files = java_files + kotlin_files

        # First pass: find all entities
        for src_file in all_files:
            self._find_entities(src_file)

        # Second pass: extract repositories
        for src_file in all_files:
            self._process_repository(src_file)

        self._log_end()
        return self.output

    def _find_java_root(self) -> Path | None:
        """Find Java/Kotlin source root."""
        candidates = [
            self.repo_path / "src" / "main" / "java",
            self.repo_path / "src" / "main" / "kotlin",
            self.repo_path / "backend" / "src" / "main" / "java",
            self.repo_path / "backend" / "src" / "main" / "kotlin",
        ]
        for c in candidates:
            if c.exists():
                return c

        for path in self.repo_path.rglob("src/main/java"):
            if path.is_dir():
                return path
        return None

    def _find_entities(self, file_path: Path):
        """Find JPA entities for relation building."""
        content = self._read_file_content(file_path)

        if "@Entity" in content:
            class_match = re.search(r"class\s+(\w+)", content)
            if class_match:
                self._entity_names.add(class_match.group(1))

    def _process_repository(self, file_path: Path):
        """Process a potential repository file."""
        content = self._read_file_content(file_path)
        lines = self._read_file(file_path)
        rel_path = self._relative_path(file_path)

        # Check if it's a repository
        is_annotated = self.REPOSITORY_PATTERN.search(content)
        extends_match = self.EXTENDS_REPO_PATTERN.search(content)

        if not is_annotated and not extends_match:
            return

        # Get interface/class name
        name_match = self.INTERFACE_PATTERN.search(content)
        if not name_match:
            # Try class pattern
            name_match = re.search(r"class\s+(\w+)", content)

        if not name_match:
            return

        repo_name = name_match.group(1)
        repo_line = self._find_line_number(lines, repo_name)

        # Determine entity if JpaRepository
        entity_name = None
        if extends_match:
            entity_name = extends_match.group(2)

        # Create repository component
        repo = RawComponent(
            name=repo_name,
            stereotype="repository",
            container_hint=self.container_id,
            module=self._derive_module(rel_path),
            file_path=rel_path,
            layer_hint="data_access",
        )

        if entity_name:
            repo.metadata["manages_entity"] = entity_name

        # Find custom queries
        custom_queries = self._extract_custom_queries(content)
        if custom_queries:
            repo.metadata["custom_queries"] = custom_queries

        # Find derived queries
        derived_queries = self._extract_derived_queries(content)
        if derived_queries:
            repo.metadata["derived_queries"] = derived_queries

        repo.add_evidence(
            path=rel_path,
            line_start=repo_line - 1,
            line_end=repo_line + 5,
            reason=f"Repository: {repo_name}" + (f" for {entity_name}" if entity_name else ""),
        )

        self.output.add_fact(repo)

        # Create relation to entity
        if entity_name and entity_name in self._entity_names:
            relation = RelationHint(
                from_name=repo_name,
                to_name=entity_name,
                type="manages",
                from_stereotype_hint="repository",
                to_stereotype_hint="entity",
                from_file_hint=str(rel_path),
            )

            relation.evidence.append(
                self._create_evidence(file_path, repo_line, repo_line + 2, f"Repository manages entity: {entity_name}")
            )

            self.output.add_relation(relation)

    def _extract_custom_queries(self, content: str) -> list[dict]:
        """Extract @Query annotations."""
        queries = []
        for match in self.QUERY_PATTERN.finditer(content):
            query = match.group(1)
            queries.append(
                {
                    "type": "custom",
                    "query": query[:100] + "..." if len(query) > 100 else query,
                }
            )
        return queries

    def _extract_derived_queries(self, content: str) -> list[dict]:
        """Extract Spring Data derived query methods."""
        queries = []
        for match in self.DERIVED_QUERY_PATTERN.finditer(content):
            return_type = match.group(1)
            prefix = match.group(2)
            suffix = match.group(3)
            queries.append(
                {
                    "type": "derived",
                    "method": f"{prefix}{suffix}",
                    "returns": return_type,
                }
            )
        return queries
