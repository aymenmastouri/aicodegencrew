"""
ContainerCollector - Detects deployable units (containers).

A Container in C4 terms is:
- A separately deployable unit
- Has its own build system (pom.xml, build.gradle, package.json)
- Runs as its own process

Detection Strategy:
1. RECURSIVE scan for build files (package.json, build.gradle, pom.xml)
2. Use DIRECTORY NAME as container name (not settings.gradle)
3. Determine type from build system + markers via ecosystem modules
4. Skip: node_modules, dist, build, deployment, .git, etc.

Container Types:
- backend: Java/Kotlin backend (Spring Boot, Quarkus, etc.)
- frontend: Web frontend (Angular, React, Vue, etc.)
- test: E2E tests, integration tests
- batch: Spring Batch jobs
- library: Shared libraries (no main class)
- database: From docker-compose
- external: External system references

Output -> containers.json
"""

import json
import re
from pathlib import Path

from ....shared.ecosystems import CollectorContext, EcosystemRegistry
from ....shared.utils.logger import logger
from .base import CollectorOutput, DimensionCollector, RawContainer


class ContainerCollector(DimensionCollector):
    """
    Detects deployable containers by RECURSIVE scanning for build files.

    Key Principle: Directory name = Container name
    """

    DIMENSION = "containers"

    # Directories to completely skip
    SKIP_DIRS = {
        "node_modules",
        ".git",
        "__pycache__",
        "dist",
        "build",
        "target",
        ".venv",
        "venv",
        "deployment",
        "buildSrc",
        ".gradle",
        ".idea",
        ".continue",
        "test-results",
        "coverage",
        ".nyc_output",
        "bin",
        "obj",
        "out",
        ".cache",
        "logs",
        "tmp",
        "temp",
    }

    # Directories that indicate test containers
    TEST_DIR_PATTERNS = {"e2e", "test", "tests", "integration-test", "it"}

    # Maximum recursion depth for sub-project detection
    MAX_DEPTH = 5

    def __init__(self, repo_path: Path):
        super().__init__(repo_path)
        self._ecosystem_registry = EcosystemRegistry()

    def collect(self) -> CollectorOutput:
        """Collect container facts by RECURSIVELY scanning build files."""
        self._log_start()

        detected: dict[str, RawContainer] = {}  # name -> container

        # Strategy 1: RECURSIVE scan for build files at all levels
        self._scan_recursive(self.repo_path, detected, depth=0)

        # Strategy 2: Detect from docker-compose (databases, external)
        self._detect_from_docker_compose(detected)

        # Add all detected containers
        for container in detected.values():
            self.output.add_fact(container)

        logger.info(f"[ContainerCollector] Total containers found: {len(detected)}")
        self._log_end()
        return self.output

    def _scan_recursive(self, current_path: Path, detected: dict[str, RawContainer], depth: int):
        """Recursively scan directories for containers (sub-projects)."""
        if depth > self.MAX_DEPTH:
            return

        # Check if current directory is a container
        container = self._detect_container_in_dir(current_path)
        if container and container.name not in detected:
            detected[container.name] = container
            logger.info(
                f"[ContainerCollector] Found {container.type}: {container.name} ({container.technology}) at depth {depth}"
            )

        # Recurse into subdirectories
        try:
            for item in current_path.iterdir():
                if not item.is_dir():
                    continue

                # Skip excluded directories
                if item.name in self.SKIP_DIRS or item.name.startswith("."):
                    continue

                # Recurse
                self._scan_recursive(item, detected, depth + 1)
        except PermissionError:
            pass  # Skip directories we can't access

    def _build_context(self) -> CollectorContext:
        """Create a CollectorContext for ecosystem container detection."""
        ctx = CollectorContext(self.repo_path)
        ctx.is_test_directory = self._is_test_directory
        ctx.find_files = self._find_files
        return ctx

    def _detect_container_in_dir(self, dir_path: Path) -> RawContainer | None:
        """Detect container type from directory contents using ecosystem modules."""
        name = dir_path.name
        ctx = self._build_context()

        # Iterate ecosystems in priority order — first match wins
        for ecosystem in self._ecosystem_registry.get_ecosystems_by_priority():
            result = ecosystem.detect_container(dir_path, name, ctx)
            if result is not None:
                return self._dict_to_raw_container(result)

        return None

    def _dict_to_raw_container(self, data: dict) -> RawContainer:
        """Convert ecosystem dict result to RawContainer."""
        container = RawContainer(
            name=data["name"],
            type=data["type"],
            technology=data["technology"],
            root_path=data["root_path"],
            category=data.get("category", ""),
            metadata=data.get("metadata", {}),
        )
        for ev in data.get("evidence", []):
            container.add_evidence(
                path=ev["path"],
                line_start=ev["line_start"],
                line_end=ev["line_end"],
                reason=ev["reason"],
            )
        return container

    def _is_test_directory(self, name: str) -> bool:
        """Check if directory name indicates a test container."""
        name_lower = name.lower()
        # Use exact match or hyphenated prefix/suffix to avoid false positives
        # (e.g. "it" must not match "audit", "credit", "security")
        for pattern in self.TEST_DIR_PATTERNS:
            if name_lower == pattern:
                return True
            if name_lower.startswith(pattern + "-") or name_lower.endswith("-" + pattern):
                return True
            if name_lower.startswith(pattern + "_") or name_lower.endswith("_" + pattern):
                return True
        return False

    def _detect_from_docker_compose(self, detected: dict[str, RawContainer]):
        """Detect database and external containers from docker-compose."""
        compose_names = ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]

        for name in compose_names:
            compose_path = self.repo_path / name
            if not compose_path.exists():
                continue

            content = self._read_file_content(compose_path)
            lines = self._read_file(compose_path)

            # Database patterns
            db_patterns = {
                "postgres": ("PostgreSQL", "database"),
                "mysql": ("MySQL", "database"),
                "mariadb": ("MariaDB", "database"),
                "oracle": ("Oracle Database", "database"),
                "mongodb": ("MongoDB", "database"),
                "redis": ("Redis", "cache"),
                "elasticsearch": ("Elasticsearch", "search"),
                "rabbitmq": ("RabbitMQ", "messaging"),
                "kafka": ("Kafka", "messaging"),
            }

            for db_key, (technology, category) in db_patterns.items():
                if db_key in content.lower():
                    # Find service name: last service-level entry (2-space indent) before this db occurrence
                    db_pos = content.lower().find(db_key)
                    if db_pos >= 0:
                        before = content[:db_pos]
                        svc_matches = list(re.finditer(r"^  ([\w][\w-]*):\s*(?:#.*)?$", before, re.MULTILINE))
                        service_name = svc_matches[-1].group(1) if svc_matches else db_key
                    else:
                        service_name = db_key

                    if service_name in detected:
                        continue

                    container = RawContainer(
                        name=service_name,
                        type=category,
                        technology=technology,
                        root_path=".",
                        category="infrastructure",
                    )

                    line_num = self._find_line_number(lines, db_key) or 1
                    container.add_evidence(
                        path=self._relative_path(compose_path),
                        line_start=line_num,
                        line_end=line_num + 5,
                        reason=f"Docker Compose service: {service_name} ({technology})",
                    )

                    detected[service_name] = container
                    logger.info(f"[ContainerCollector] Found {category}: {service_name} ({technology})")
