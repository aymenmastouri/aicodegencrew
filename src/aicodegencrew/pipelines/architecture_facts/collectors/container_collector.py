"""
ContainerCollector - Detects deployable units (containers).

A Container in C4 terms is:
- A separately deployable unit
- Has its own build system (pom.xml, build.gradle, package.json)
- Runs as its own process

Detection Strategy:
1. Scan top-level directories for build files
2. Use DIRECTORY NAME as container name (not settings.gradle)
3. Determine type from build system + markers
4. Skip: node_modules, dist, build, deployment, .git, etc.

Container Types:
- backend: Spring Boot, Java backend
- frontend: Angular, React, Vue
- test: E2E tests, integration tests
- batch: Spring Batch jobs
- library: Shared libraries (no main class)
- database: From docker-compose
- external: External system references

Output -> containers.json
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .base import DimensionCollector, CollectorOutput, RawContainer
from ....shared.utils.logger import logger


class ContainerCollector(DimensionCollector):
    """
    Detects deployable containers by scanning for build files.
    
    Key Principle: Directory name = Container name
    """
    
    DIMENSION = "containers"
    
    # Directories to completely skip
    SKIP_DIRS = {
        'node_modules', '.git', '__pycache__', 'dist', 'build', 'target',
        '.venv', 'venv', 'deployment', 'buildSrc', '.gradle', '.idea',
        '.continue', 'test-results', 'coverage', '.nyc_output'
    }
    
    # Directories that indicate test containers
    TEST_DIR_PATTERNS = {'e2e', 'test', 'tests', 'integration-test', 'it'}
    
    def collect(self) -> CollectorOutput:
        """Collect container facts by scanning build files."""
        self._log_start()
        
        detected: Dict[str, RawContainer] = {}  # name -> container
        
        # Strategy 1: Scan top-level directories for build files
        self._scan_top_level_dirs(detected)
        
        # Strategy 2: Detect from docker-compose (databases, external)
        self._detect_from_docker_compose(detected)
        
        # Add all detected containers
        for container in detected.values():
            self.output.add_fact(container)
        
        self._log_end()
        return self.output
    
    def _scan_top_level_dirs(self, detected: Dict[str, RawContainer]):
        """Scan top-level directories for containers."""
        for item in self.repo_path.iterdir():
            if not item.is_dir():
                continue
            
            # Skip excluded directories
            if item.name in self.SKIP_DIRS or item.name.startswith('.'):
                continue
            
            # Check for build files
            container = self._detect_container_in_dir(item)
            if container and container.name not in detected:
                detected[container.name] = container
                logger.info(f"[ContainerCollector] Found {container.type}: {container.name} ({container.technology})")
    
    def _detect_container_in_dir(self, dir_path: Path) -> Optional[RawContainer]:
        """Detect container type from directory contents."""
        name = dir_path.name
        
        # Check for Spring Boot (Gradle)
        build_gradle = dir_path / "build.gradle"
        build_gradle_kts = dir_path / "build.gradle.kts"
        
        if build_gradle.exists() or build_gradle_kts.exists():
            gradle_file = build_gradle if build_gradle.exists() else build_gradle_kts
            return self._detect_gradle_container(gradle_file, name)
        
        # Check for Maven
        pom_xml = dir_path / "pom.xml"
        if pom_xml.exists():
            return self._detect_maven_container(pom_xml, name)
        
        # Check for Node.js (Angular, React, E2E tests)
        package_json = dir_path / "package.json"
        if package_json.exists():
            return self._detect_node_container(package_json, name)
        
        return None
    
    def _detect_gradle_container(self, gradle_path: Path, name: str) -> Optional[RawContainer]:
        """Detect container from Gradle build file."""
        content = self._read_file_content(gradle_path)
        lines = self._read_file(gradle_path)
        
        # Determine technology and type
        is_spring = (
            "org.springframework.boot" in content or
            "spring-boot" in content.lower()
        )
        
        is_batch = "spring-boot-starter-batch" in content
        
        # Check for main class to distinguish library vs application
        has_main = self._find_spring_main_class(gradle_path.parent) is not None
        
        if is_spring:
            container_type = "batch" if is_batch else "backend"
            technology = "Spring Batch" if is_batch else "Spring Boot"
        else:
            container_type = "library"
            technology = "Java/Gradle"
        
        # Override for test directories
        if self._is_test_directory(name):
            container_type = "test"
        
        container = RawContainer(
            name=name,
            type=container_type,
            technology=technology,
            root_path=self._relative_path(gradle_path.parent),
            category="application" if has_main else "library",
            metadata={
                "build_system": "gradle",
                "has_main_class": has_main,
            }
        )
        
        # Add evidence
        spring_line = self._find_line_number(lines, "spring") or 1
        container.add_evidence(
            path=self._relative_path(gradle_path),
            line_start=spring_line,
            line_end=spring_line + 10,
            reason=f"{technology} project: {name}"
        )
        
        return container
    
    def _detect_maven_container(self, pom_path: Path, name: str) -> Optional[RawContainer]:
        """Detect container from Maven pom.xml."""
        content = self._read_file_content(pom_path)
        lines = self._read_file(pom_path)
        
        # Skip parent POMs
        if "<modules>" in content and "<packaging>pom</packaging>" in content:
            return None
        
        is_spring = "spring-boot" in content.lower()
        is_batch = "spring-boot-starter-batch" in content
        
        has_main = self._find_spring_main_class(pom_path.parent) is not None
        
        if is_spring:
            container_type = "batch" if is_batch else "backend"
            technology = "Spring Batch" if is_batch else "Spring Boot"
        else:
            container_type = "library"
            technology = "Java/Maven"
        
        if self._is_test_directory(name):
            container_type = "test"
        
        container = RawContainer(
            name=name,
            type=container_type,
            technology=technology,
            root_path=self._relative_path(pom_path.parent),
            category="application" if has_main else "library",
            metadata={
                "build_system": "maven",
                "has_main_class": has_main,
            }
        )
        
        artifact_line = self._find_line_number(lines, "<artifactId>") or 1
        container.add_evidence(
            path=self._relative_path(pom_path),
            line_start=artifact_line,
            line_end=artifact_line + 10,
            reason=f"{technology} project: {name}"
        )
        
        return container
    
    def _detect_node_container(self, package_path: Path, name: str) -> Optional[RawContainer]:
        """Detect container from package.json."""
        try:
            content = package_path.read_text(encoding='utf-8')
            pkg = json.loads(content)
        except Exception:
            return None
        
        deps = pkg.get("dependencies", {})
        dev_deps = pkg.get("devDependencies", {})
        all_deps = {**deps, **dev_deps}
        
        # Detect framework
        technology = None
        container_type = "frontend"
        
        # Angular
        if "@angular/core" in all_deps:
            technology = "Angular"
        # React
        elif "react" in all_deps:
            technology = "React"
        # Vue
        elif "vue" in all_deps:
            technology = "Vue"
        # E2E Test frameworks
        elif "cypress" in all_deps or "playwright" in all_deps or "protractor" in all_deps:
            technology = "Cypress" if "cypress" in all_deps else "Playwright" if "playwright" in all_deps else "Protractor"
            container_type = "test"
        # Generic Node.js
        else:
            technology = "Node.js"
        
        # Override type for test directories
        if self._is_test_directory(name):
            container_type = "test"
        
        container = RawContainer(
            name=name,
            type=container_type,
            technology=technology,
            root_path=self._relative_path(package_path.parent),
            category="application" if container_type != "test" else "test",
            metadata={
                "build_system": "npm",
                "version": pkg.get("version"),
            }
        )
        
        container.add_evidence(
            path=self._relative_path(package_path),
            line_start=1,
            line_end=20,
            reason=f"{technology} project: {name}"
        )
        
        return container
    
    def _is_test_directory(self, name: str) -> bool:
        """Check if directory name indicates a test container."""
        name_lower = name.lower()
        # Check for test patterns
        for pattern in self.TEST_DIR_PATTERNS:
            if pattern in name_lower:
                return True
        return False
    
    def _find_spring_main_class(self, root: Path) -> Optional[Dict]:
        """Find @SpringBootApplication class."""
        # Search in src/main/java
        java_root = root / "src" / "main" / "java"
        if not java_root.exists():
            java_root = root
        
        java_files = list(java_root.rglob("*.java"))[:100]  # Limit search
        
        for java_file in java_files:
            try:
                content = java_file.read_text(encoding='utf-8', errors='ignore')
                if "@SpringBootApplication" in content:
                    lines = content.splitlines()
                    for i, line in enumerate(lines):
                        if "@SpringBootApplication" in line:
                            return {
                                "path": self._relative_path(java_file),
                                "line": i + 1,
                            }
            except Exception:
                continue
        return None
    
    def _detect_from_docker_compose(self, detected: Dict[str, RawContainer]):
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
                    # Find service name
                    service_match = re.search(
                        rf'^\s+(\w+):\s*\n[^:]*image:\s*["\']?[^"\']*{db_key}',
                        content, re.MULTILINE | re.IGNORECASE
                    )
                    service_name = service_match.group(1) if service_match else db_key
                    
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
                        reason=f"Docker Compose service: {service_name} ({technology})"
                    )
                    
                    detected[service_name] = container
                    logger.info(f"[ContainerCollector] Found {category}: {service_name} ({technology})")
