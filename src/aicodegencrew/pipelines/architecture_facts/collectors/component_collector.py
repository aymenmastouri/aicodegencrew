"""
ComponentCollector - Aggregates component facts from specialists.

This is an AGGREGATOR that:
1. Receives container info from orchestrator
2. Routes to ecosystem-specific specialists based on container technology
3. Merges all component facts

Container-Aware:
- Spring specialists run in containers with type="backend"
- Angular specialists run in containers with type="frontend"
- Each specialist searches in the container's root_path

Output -> components.json
"""

from pathlib import Path

from ....shared.ecosystems import EcosystemRegistry
from ....shared.utils.logger import logger
from .base import CollectorOutput, DimensionCollector, RawComponent


class ComponentCollector(DimensionCollector):
    """
    Aggregates component facts from technology-specific specialists.

    Uses ecosystem registry to route containers to the appropriate
    ecosystem's component collectors.
    """

    DIMENSION = "components"

    def __init__(self, repo_path: Path, containers: list[dict] = None):
        """
        Initialize with container context.

        Args:
            repo_path: Repository root
            containers: List of detected containers with technology and root_path
        """
        super().__init__(repo_path)
        self.containers = containers or []
        self._ecosystem_registry = EcosystemRegistry()

    def collect(self) -> CollectorOutput:
        """Collect components from all relevant specialists."""
        self._log_start()

        collected_any = False

        # For each container, find the ecosystem and run its component collectors
        for container in self.containers:
            technology = container.get("technology", "")
            ecosystem = self._ecosystem_registry.get_ecosystem_for_technology(technology)
            if ecosystem is not None:
                logger.info(
                    f"[ComponentCollector] Running {ecosystem.name} specialists for "
                    f"'{container.get('name', '')}' ({technology})"
                )
                facts, relations = ecosystem.collect_components(container, self.repo_path)
                for fact in facts:
                    if isinstance(fact, RawComponent):
                        self.output.add_fact(fact)
                for relation in relations:
                    self.output.add_relation(relation)
                collected_any = True

        # Fallback: if no containers at all, detect and run anyway
        if not collected_any:
            self._fallback_detection()

        self._log_end()
        return self.output

    def _get_container_root(self, container: dict) -> Path:
        """Get the root path for a container."""
        root_path = container.get("root_path", "")
        if root_path and root_path != ".":
            return self.repo_path / root_path
        return self.repo_path

    def _fallback_detection(self):
        """Fallback: detect technologies without container info."""
        logger.info("[ComponentCollector] No containers provided, running fallback detection...")

        # Detect Spring
        if self._detect_spring():
            logger.info("[ComponentCollector] Detected Spring Boot, running specialists...")
            ecosystem = self._ecosystem_registry.get_ecosystem_for_technology("Spring Boot")
            if ecosystem:
                facts, relations = ecosystem.collect_components(
                    {"name": "backend", "root_path": ""}, self.repo_path
                )
                for fact in facts:
                    if isinstance(fact, RawComponent):
                        self.output.add_fact(fact)
                for relation in relations:
                    self.output.add_relation(relation)

        # Detect Angular — search in subdirectories too
        angular_root = self._find_angular_root()
        if angular_root:
            logger.info(f"[ComponentCollector] Detected Angular in {angular_root}")
            ecosystem = self._ecosystem_registry.get_ecosystem_for_technology("Angular")
            if ecosystem:
                facts, relations = ecosystem.collect_components(
                    {"name": "frontend", "root_path": str(angular_root.relative_to(self.repo_path))},
                    self.repo_path,
                )
                for fact in facts:
                    if isinstance(fact, RawComponent):
                        self.output.add_fact(fact)
                for relation in relations:
                    self.output.add_relation(relation)

        # Detect Python (Django/Flask/FastAPI)
        if self._detect_python():
            logger.info("[ComponentCollector] Detected Python project, running specialists...")
            ecosystem = self._ecosystem_registry.get_ecosystem_for_technology("Python")
            if ecosystem:
                facts, relations = ecosystem.collect_components(
                    {"name": "backend", "root_path": ""}, self.repo_path
                )
                for fact in facts:
                    if isinstance(fact, RawComponent):
                        self.output.add_fact(fact)
                for relation in relations:
                    self.output.add_relation(relation)

        # Detect C/C++ (CMake)
        if self._detect_cpp():
            logger.info("[ComponentCollector] Detected C/C++ project, running specialists...")
            ecosystem = self._ecosystem_registry.get_ecosystem_for_technology("C/C++")
            if not ecosystem:
                ecosystem = self._ecosystem_registry.get_ecosystem_for_technology("C++/CMake")
            if ecosystem:
                facts, relations = ecosystem.collect_components(
                    {"name": "backend", "root_path": ""}, self.repo_path
                )
                for fact in facts:
                    if isinstance(fact, RawComponent):
                        self.output.add_fact(fact)
                for relation in relations:
                    self.output.add_relation(relation)

    def _detect_spring(self) -> bool:
        """Detect if project has Spring Boot."""
        for pom in self._find_files("pom.xml"):
            try:
                content = pom.read_text(encoding="utf-8", errors="ignore")
                if "spring-boot" in content.lower():
                    return True
            except Exception:
                continue

        for gradle in self._find_files("build.gradle") + self._find_files("build.gradle.kts"):
            try:
                content = gradle.read_text(encoding="utf-8", errors="ignore")
                if "org.springframework.boot" in content or "spring-boot" in content.lower():
                    return True
            except Exception:
                continue

        return False

    def _detect_python(self) -> bool:
        """Detect if project has Python (Django/Flask/FastAPI)."""
        for marker in ("pyproject.toml", "setup.py", "requirements.txt"):
            if self._find_files(marker):
                return True
        return False

    def _detect_cpp(self) -> bool:
        """Detect if project has C/C++ (CMake/Makefile)."""
        if (self.repo_path / "CMakeLists.txt").exists():
            return True
        if (self.repo_path / "Makefile").exists():
            return True
        if (self.repo_path / "meson.build").exists():
            return True
        return False

    def _find_angular_root(self) -> Path | None:
        """Find Angular root directory (looks in subdirectories)."""
        if (self.repo_path / "angular.json").exists():
            return self.repo_path

        for subdir in ["frontend", "client", "web", "ui", "angular"]:
            angular_json = self.repo_path / subdir / "angular.json"
            if angular_json.exists():
                return angular_json.parent

        for angular_json in self._find_files("angular.json"):
            return angular_json.parent

        return None

    def _merge_output(self, other: CollectorOutput):
        """Merge another collector's output into this one (only RawComponent facts)."""
        for fact in other.facts:
            if isinstance(fact, RawComponent):
                self.output.add_fact(fact)

        for relation in other.relations:
            self.output.add_relation(relation)
