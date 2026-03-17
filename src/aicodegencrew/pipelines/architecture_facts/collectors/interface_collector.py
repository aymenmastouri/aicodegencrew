"""
InterfaceCollector - Aggregates interface facts.

Thin router that delegates ecosystem-specific collection to specialist
collectors. Container-based routing uses EcosystemRegistry for technology
matching. Cross-cutting: OpenAPI/Swagger specifications.

Collects:
- REST endpoints (Spring, Flask, FastAPI, Django)
- Angular routes
- C/C++ public APIs
- OpenAPI/Swagger specifications
- Schedulers and message listeners (via ecosystem delegation)

Output -> interfaces.json
"""

from pathlib import Path

from ....shared.ecosystems.registry import EcosystemRegistry
from ....shared.utils.logger import logger
from .angular import AngularRoutingCollector, OpenAPICollector
from .base import CollectorOutput, DimensionCollector, RawInterface
from .spring import SpringRestCollector


class InterfaceCollector(DimensionCollector):
    """
    Aggregates interface facts from all sources.

    Routes container-based collection to ecosystem specialist collectors.
    Uses EcosystemRegistry for fallback detection and scheduler/listener delegation.
    """

    DIMENSION = "interfaces"

    def __init__(self, repo_path: Path, containers: list[dict] = None):
        super().__init__(repo_path)
        self.containers = containers or []
        self._registry = EcosystemRegistry()

    def collect(self) -> CollectorOutput:
        """Collect all interface facts."""
        self._log_start()

        if self.containers:
            # Container-based routing via ecosystem registry
            for container in self.containers:
                technology = container.get("technology", "")
                eco = self._registry.get_ecosystem_for_technology(technology)
                if eco is None:
                    continue

                container_root = self._get_container_root(container)
                container_name = container.get("name", "backend")

                if eco.id == "java_jvm":
                    self._collect_rest_endpoints(container_root, container_name)
                elif eco.id == "javascript_typescript" and technology == "Angular":
                    self._collect_angular_routes(container_root, container_name)
                elif eco.id == "python":
                    self._collect_python_interfaces(container_root, container_name)
                elif eco.id == "c_cpp":
                    self._collect_cpp_interfaces(container_root, container_name)
        else:
            # Fallback: use ecosystem detection
            self._fallback_detection()

        # Cross-cutting: OpenAPI/Swagger specifications (always run)
        self._collect_openapi_specs()

        # Ecosystem delegation for schedulers and listeners
        for eco in self._registry.detect(self.repo_path):
            facts, rels = eco.collect_dimension(self.DIMENSION, self.repo_path)
            for f in facts:
                self.output.add_fact(f)
            for r in rels:
                self.output.add_relation(r)

        self._log_end()
        return self.output

    def _get_container_root(self, container: dict) -> Path:
        """Get container root path."""
        root = container.get("root_path", "")
        if root and root != ".":
            return self.repo_path / root
        return self.repo_path

    def _collect_rest_endpoints(self, container_root: Path, container_name: str):
        """Collect REST endpoints from a Spring container."""
        logger.info(f"[InterfaceCollector] Collecting REST endpoints from '{container_name}'")

        rest_collector = SpringRestCollector(container_root, container_id=container_name)
        rest_output = rest_collector.collect()

        for fact in rest_output.facts:
            if isinstance(fact, RawInterface):
                self.output.add_fact(fact)

    def _collect_angular_routes(self, container_root: Path, container_name: str):
        """Collect Angular routes from a frontend container."""
        logger.info(f"[InterfaceCollector] Collecting Angular routes from '{container_name}'")

        routing_collector = AngularRoutingCollector(container_root, container_id=container_name)
        routing_output = routing_collector.collect()

        for fact in routing_output.facts:
            if isinstance(fact, RawInterface):
                self.output.add_fact(fact)

        for relation in routing_output.relations:
            self.output.add_relation(relation)

    def _collect_python_interfaces(self, container_root: Path, container_name: str):
        """Collect Python REST endpoints."""
        from .python_eco import PythonInterfaceCollector

        logger.info(f"[InterfaceCollector] Collecting Python interfaces from '{container_name}'")

        collector = PythonInterfaceCollector(container_root, container_id=container_name)
        output = collector.collect()

        for fact in output.facts:
            if isinstance(fact, RawInterface):
                self.output.add_fact(fact)

    def _collect_cpp_interfaces(self, container_root: Path, container_name: str):
        """Collect C/C++ interfaces."""
        from .cpp import CppInterfaceCollector

        logger.info(f"[InterfaceCollector] Collecting C/C++ interfaces from '{container_name}'")

        collector = CppInterfaceCollector(container_root, container_id=container_name)
        output = collector.collect()

        for fact in output.facts:
            if isinstance(fact, RawInterface):
                self.output.add_fact(fact)

    def _fallback_detection(self):
        """Fallback detection using EcosystemRegistry."""
        active_ecosystems = self._registry.detect(self.repo_path)

        for eco in active_ecosystems:
            if eco.id == "java_jvm":
                self._collect_rest_endpoints(self.repo_path, "backend")
            elif eco.id == "javascript_typescript":
                angular_root = self._find_angular_root()
                if angular_root:
                    rel_path = str(angular_root.relative_to(self.repo_path)) if angular_root != self.repo_path else ""
                    container_root = self.repo_path / rel_path if rel_path else self.repo_path
                    self._collect_angular_routes(container_root, "frontend")
            elif eco.id == "python":
                self._collect_python_interfaces(self.repo_path, "backend")
            elif eco.id == "c_cpp":
                self._collect_cpp_interfaces(self.repo_path, "backend")

    def _collect_openapi_specs(self):
        """Collect OpenAPI/Swagger specifications from the project."""
        logger.info("[InterfaceCollector] Collecting OpenAPI/Swagger specifications...")

        openapi_collector = OpenAPICollector(self.repo_path)
        openapi_output = openapi_collector.collect()

        for fact in openapi_output.facts:
            if isinstance(fact, RawInterface):
                self.output.add_fact(fact)

        for relation in openapi_output.relations:
            self.output.add_relation(relation)

    def _find_angular_root(self) -> Path | None:
        """Find Angular root directory."""
        for subdir in ["", "frontend", "client", "web", "ui", "angular"]:
            check_path = self.repo_path / subdir if subdir else self.repo_path
            if (check_path / "angular.json").exists():
                return check_path

        for angular_json in self._find_files("angular.json"):
            return angular_json.parent

        return None
