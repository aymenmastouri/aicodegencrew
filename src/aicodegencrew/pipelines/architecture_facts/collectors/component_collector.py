"""
ComponentCollector - Aggregates component facts from specialists.

This is an AGGREGATOR that:
1. Receives container info from orchestrator
2. Runs specialists based on container technology
3. Merges all component facts

Container-Aware:
- Spring specialists run in containers with type="backend"
- Angular specialists run in containers with type="frontend"
- Each specialist searches in the container's root_path

Output -> components.json
"""

from pathlib import Path

from ....shared.utils.logger import logger
from .angular import AngularComponentCollector, AngularModuleCollector, AngularServiceCollector
from .base import CollectorOutput, DimensionCollector, RawComponent
from .spring import SpringRepositoryCollector, SpringRestCollector, SpringServiceCollector


class ComponentCollector(DimensionCollector):
    """
    Aggregates component facts from technology-specific specialists.

    Uses container information to determine:
    - Which specialists to run
    - Where to search (container root paths)
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

    # Technologies handled by Spring specialists (Java-based)
    _SPRING_TECHNOLOGIES = {"Spring Boot", "Java/Gradle", "Java/Maven"}

    def collect(self) -> CollectorOutput:
        """Collect components from all relevant specialists."""
        self._log_start()

        # Collect from Java-based containers (Spring Boot, Java/Gradle, Java/Maven)
        java_containers = self._get_containers_by_technologies(self._SPRING_TECHNOLOGIES)
        for container in java_containers:
            self._collect_spring_components(container)

        # Collect from Angular containers
        angular_containers = self._get_containers_by_technology("Angular")
        for container in angular_containers:
            self._collect_angular_components(container)

        # Collect from Node.js containers (basic TS/JS class detection)
        node_containers = self._get_containers_by_technologies({"Node.js", "Node.js/TypeScript"})
        for container in node_containers:
            self._collect_node_components(container)

        # Fallback: if no containers at all, detect and run anyway
        if not java_containers and not angular_containers and not node_containers:
            self._fallback_detection()

        self._log_end()
        return self.output

    def _get_containers_by_technology(self, technology: str) -> list[dict]:
        """Get containers matching a technology."""
        return [c for c in self.containers if c.get("technology") == technology]

    def _get_containers_by_technologies(self, technologies: set) -> list[dict]:
        """Get containers matching any of the given technologies."""
        return [c for c in self.containers if c.get("technology") in technologies]

    def _get_container_root(self, container: dict) -> Path:
        """Get the root path for a container."""
        root_path = container.get("root_path", "")
        if root_path and root_path != ".":
            return self.repo_path / root_path
        return self.repo_path

    def _collect_spring_components(self, container: dict):
        """Run Spring specialists for a container."""
        container_root = self._get_container_root(container)
        container_name = container.get("name", "backend")

        logger.info(f"[ComponentCollector] Running Spring specialists for '{container_name}' in {container_root}")

        # Controllers
        rest_collector = SpringRestCollector(container_root, container_id=container_name)
        rest_output = rest_collector.collect()
        self._merge_output(rest_output)

        # Services
        service_collector = SpringServiceCollector(container_root, container_id=container_name)
        service_output = service_collector.collect()
        self._merge_output(service_output)

        # Repositories
        repo_collector = SpringRepositoryCollector(container_root, container_id=container_name)
        repo_output = repo_collector.collect()
        self._merge_output(repo_output)

    def _collect_angular_components(self, container: dict):
        """Run Angular specialists for a container."""
        container_root = self._get_container_root(container)
        container_name = container.get("name", "frontend")

        logger.info(f"[ComponentCollector] Running Angular specialists for '{container_name}' in {container_root}")

        # Modules
        module_collector = AngularModuleCollector(container_root, container_id=container_name)
        module_output = module_collector.collect()
        self._merge_output(module_output)

        # Components
        component_collector = AngularComponentCollector(container_root, container_id=container_name)
        component_output = component_collector.collect()
        self._merge_output(component_output)

        # Services
        service_collector = AngularServiceCollector(container_root, container_id=container_name)
        service_output = service_collector.collect()
        self._merge_output(service_output)

    def _collect_node_components(self, container: dict):
        """Detect exported classes/functions in a Node.js/TypeScript container."""
        import re

        container_root = self._get_container_root(container)
        container_name = container.get("name", "node")

        logger.info(f"[ComponentCollector] Scanning Node.js/TS exports for '{container_name}' in {container_root}")

        ts_files = self._find_files("*.ts", container_root) + self._find_files("*.js", container_root)

        count = 0
        for fpath in ts_files:
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # Match: export class Foo / export function bar / export default class
            for m in re.finditer(r"export\s+(?:default\s+)?(?:class|function|const)\s+(\w+)", content):
                name = m.group(1)
                # Determine stereotype from naming conventions
                lower = name.lower()
                if lower.endswith("service"):
                    stereo = "service"
                elif lower.endswith("controller") or lower.endswith("handler"):
                    stereo = "controller"
                elif lower.endswith("model") or lower.endswith("entity"):
                    stereo = "entity"
                elif lower.endswith("spec") or lower.endswith("test"):
                    stereo = "test"
                else:
                    stereo = "component"

                rel_path = self._relative_path(fpath)
                self.output.add_fact(
                    RawComponent(
                        name=name,
                        stereotype=stereo,
                        container_hint=container_name,
                        file_path=rel_path,
                        metadata={
                            "source": "node_export_scan",
                            "technology": "TypeScript" if fpath.suffix == ".ts" else "JavaScript",
                            "line_number": content[: m.start()].count("\n") + 1,
                        },
                    )
                )
                count += 1

        logger.info(f"[ComponentCollector] Found {count} Node.js/TS exports in '{container_name}'")

    def _fallback_detection(self):
        """Fallback: detect technologies without container info."""
        logger.info("[ComponentCollector] No containers provided, running fallback detection...")

        # Detect Spring
        if self._detect_spring():
            logger.info("[ComponentCollector] Detected Spring Boot, running specialists...")
            self._collect_spring_components({"name": "backend", "root_path": ""})

        # Detect Angular - search in subdirectories too
        angular_root = self._find_angular_root()
        if angular_root:
            logger.info(f"[ComponentCollector] Detected Angular in {angular_root}")
            self._collect_angular_components(
                {"name": "frontend", "root_path": str(angular_root.relative_to(self.repo_path))}
            )

    def _detect_spring(self) -> bool:
        """Detect if project has Spring Boot."""
        # Check Maven
        for pom in self._find_files("pom.xml"):
            try:
                content = pom.read_text(encoding="utf-8", errors="ignore")
                if "spring-boot" in content.lower():
                    return True
            except Exception:
                continue

        # Check Gradle
        for gradle in self._find_files("build.gradle") + self._find_files("build.gradle.kts"):
            try:
                content = gradle.read_text(encoding="utf-8", errors="ignore")
                if "org.springframework.boot" in content or "spring-boot" in content.lower():
                    return True
            except Exception:
                continue

        return False

    def _find_angular_root(self) -> Path | None:
        """Find Angular root directory (looks in subdirectories)."""
        # Check root
        if (self.repo_path / "angular.json").exists():
            return self.repo_path

        # Check common subdirectories
        for subdir in ["frontend", "client", "web", "ui", "angular"]:
            angular_json = self.repo_path / subdir / "angular.json"
            if angular_json.exists():
                return angular_json.parent

        # Search deeper (using _find_files for proper pruning)
        for angular_json in self._find_files("angular.json"):
            return angular_json.parent

        return None

    def _merge_output(self, other: CollectorOutput):
        """Merge another collector's output into this one (only RawComponent facts)."""
        for fact in other.facts:
            # Only add actual components, not interfaces
            if isinstance(fact, RawComponent):
                self.output.add_fact(fact)

        for relation in other.relations:
            self.output.add_relation(relation)
