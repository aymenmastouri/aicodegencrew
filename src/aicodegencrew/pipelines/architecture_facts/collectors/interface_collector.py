"""
InterfaceCollector - Aggregates interface facts.

Collects:
- REST endpoints (from Spring @RestController, *RestService)
- Angular routes
- OpenAPI/Swagger specifications
- Schedulers (@Scheduled)
- Message listeners (Kafka, RabbitMQ)

Output -> interfaces.json
"""

import re
from pathlib import Path

from ....shared.utils.logger import logger
from .angular import AngularRoutingCollector, OpenAPICollector
from .base import CollectorOutput, DimensionCollector, RawInterface
from .spring import SpringRestCollector


class InterfaceCollector(DimensionCollector):
    """
    Aggregates interface facts from all sources.
    """

    DIMENSION = "interfaces"

    def __init__(self, repo_path: Path, containers: list[dict] = None):
        super().__init__(repo_path)
        self.containers = containers or []

    def collect(self) -> CollectorOutput:
        """Collect all interface facts."""
        self._log_start()

        # Collect REST endpoints from Spring containers
        spring_containers = [c for c in self.containers if c.get("technology") == "Spring Boot"]
        for container in spring_containers:
            self._collect_rest_endpoints(container)

        # Collect routes from Angular containers
        angular_containers = [c for c in self.containers if c.get("technology") == "Angular"]
        for container in angular_containers:
            self._collect_angular_routes(container)

        # Fallback detection
        if not spring_containers and not angular_containers:
            self._fallback_detection()

        # Collect OpenAPI/Swagger specifications (always run)
        self._collect_openapi_specs()

        # Collect schedulers (always run for any Java project)
        self._collect_schedulers()

        # Collect message listeners
        self._collect_listeners()

        self._log_end()
        return self.output

    def _get_container_root(self, container: dict) -> Path:
        """Get container root path."""
        root = container.get("root_path", "")
        if root and root != ".":
            return self.repo_path / root
        return self.repo_path

    def _collect_rest_endpoints(self, container: dict):
        """Collect REST endpoints from a Spring container."""
        container_root = self._get_container_root(container)
        container_name = container.get("name", "backend")

        logger.info(f"[InterfaceCollector] Collecting REST endpoints from '{container_name}'")

        rest_collector = SpringRestCollector(container_root, container_id=container_name)
        rest_output = rest_collector.collect()

        # Only take interfaces
        for fact in rest_output.facts:
            if isinstance(fact, RawInterface):
                self.output.add_fact(fact)

    def _collect_angular_routes(self, container: dict):
        """Collect Angular routes from a frontend container."""
        container_root = self._get_container_root(container)
        container_name = container.get("name", "frontend")

        logger.info(f"[InterfaceCollector] Collecting Angular routes from '{container_name}'")

        routing_collector = AngularRoutingCollector(container_root, container_id=container_name)
        routing_output = routing_collector.collect()

        for fact in routing_output.facts:
            if isinstance(fact, RawInterface):
                self.output.add_fact(fact)

        for relation in routing_output.relations:
            self.output.add_relation(relation)

    def _fallback_detection(self):
        """Fallback detection without container info."""
        # Detect Spring
        if self._detect_spring():
            self._collect_rest_endpoints({"name": "backend", "root_path": ""})

        # Detect Angular
        angular_root = self._find_angular_root()
        if angular_root:
            rel_path = str(angular_root.relative_to(self.repo_path)) if angular_root != self.repo_path else ""
            self._collect_angular_routes({"name": "frontend", "root_path": rel_path})

    def _collect_openapi_specs(self):
        """Collect OpenAPI/Swagger specifications from the project."""
        logger.info("[InterfaceCollector] Collecting OpenAPI/Swagger specifications...")

        openapi_collector = OpenAPICollector(self.repo_path)
        openapi_output = openapi_collector.collect()

        # Add all interfaces (endpoints from specs)
        for fact in openapi_output.facts:
            if isinstance(fact, RawInterface):
                self.output.add_fact(fact)

        # Add relations
        for relation in openapi_output.relations:
            self.output.add_relation(relation)

    def _detect_spring(self) -> bool:
        """Detect if project has Spring Boot."""
        for gradle in list(self.repo_path.rglob("build.gradle")) + list(self.repo_path.rglob("build.gradle.kts")):
            if "node_modules" in str(gradle) or "deployment" in str(gradle):
                continue
            try:
                content = gradle.read_text(encoding="utf-8", errors="ignore")
                if "org.springframework.boot" in content:
                    return True
            except Exception:
                continue
        return False

    def _find_angular_root(self) -> Path | None:
        """Find Angular root directory."""
        for subdir in ["", "frontend", "client", "web"]:
            check_path = self.repo_path / subdir if subdir else self.repo_path
            if (check_path / "angular.json").exists():
                return check_path
        return None

    def _collect_schedulers(self):
        """Collect @Scheduled methods."""
        SCHEDULED_PATTERN = re.compile(r"@Scheduled\s*\(([^)]+)\)")
        METHOD_PATTERN = re.compile(r"(?:public|private|protected)?\s*(?:void|[\w<>]+)\s+(\w+)\s*\(")

        # Search in all Java files
        java_files = list(self.repo_path.rglob("*.java"))
        java_files = [f for f in java_files if "node_modules" not in str(f) and "deployment" not in str(f)]

        for java_file in java_files:
            try:
                content = java_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            for match in SCHEDULED_PATTERN.finditer(content):
                config = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                # Find method name
                method_search = METHOD_PATTERN.search(content[match.end() : match.end() + 200])
                method_name = method_search.group(1) if method_search else "unknown"

                # Parse cron/rate
                cron_match = re.search(r'cron\s*=\s*["\']([^"\']+)["\']', config)
                rate_match = re.search(r"fixedRate\s*=\s*(\d+)", config)

                scheduler = RawInterface(
                    name=method_name,
                    type="scheduler",
                    path=None,
                    method=None,
                    implemented_by_hint=java_file.stem,
                    container_hint="backend",
                )

                if cron_match:
                    scheduler.metadata["cron"] = cron_match.group(1)
                if rate_match:
                    scheduler.metadata["fixed_rate_ms"] = int(rate_match.group(1))

                rel_path = str(java_file.relative_to(self.repo_path))
                scheduler.add_evidence(
                    path=rel_path, line_start=line_num, line_end=line_num + 3, reason=f"@Scheduled: {method_name}"
                )

                self.output.add_fact(scheduler)

    def _collect_listeners(self):
        """Collect message listeners (Kafka, RabbitMQ)."""
        KAFKA_LISTENER = re.compile(r"@KafkaListener\s*\(([^)]+)\)")
        RABBIT_LISTENER = re.compile(r"@RabbitListener\s*\(([^)]+)\)")
        re.compile(r"(?:public|private|protected)?\s*(?:void|[\w<>]+)\s+(\w+)\s*\(")

        java_files = list(self.repo_path.rglob("*.java"))
        java_files = [f for f in java_files if "node_modules" not in str(f) and "deployment" not in str(f)]

        for java_file in java_files:
            try:
                content = java_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # Kafka listeners
            for match in KAFKA_LISTENER.finditer(content):
                self._extract_listener(match, content, java_file, "kafka_listener")

            # RabbitMQ listeners
            for match in RABBIT_LISTENER.finditer(content):
                self._extract_listener(match, content, java_file, "rabbit_listener")

    def _extract_listener(self, match, content: str, file_path: Path, listener_type: str):
        """Extract a message listener."""
        config = match.group(1)
        line_num = content[: match.start()].count("\n") + 1

        METHOD_PATTERN = re.compile(r"(?:public|private|protected)?\s*(?:void|[\w<>]+)\s+(\w+)\s*\(")
        method_search = METHOD_PATTERN.search(content[match.end() : match.end() + 200])
        method_name = method_search.group(1) if method_search else "unknown"

        # Extract topic/queue
        topic_match = re.search(r'topics?\s*=\s*["\']([^"\']+)["\']', config)
        queue_match = re.search(r'queues?\s*=\s*["\']([^"\']+)["\']', config)

        listener = RawInterface(
            name=method_name,
            type=listener_type,
            path=topic_match.group(1) if topic_match else (queue_match.group(1) if queue_match else None),
            method=None,
            implemented_by_hint=file_path.stem,
            container_hint="backend",
        )

        rel_path = str(file_path.relative_to(self.repo_path))
        listener.add_evidence(
            path=rel_path, line_start=line_num, line_end=line_num + 5, reason=f"Message listener: {method_name}"
        )

        self.output.add_fact(listener)
