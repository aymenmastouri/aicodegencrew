"""Spring Dependency Specialist — Extracts Maven and Gradle dependency facts.

Detects:
- Maven dependencies (pom.xml)
- Gradle dependencies (build.gradle, build.gradle.kts)

Output: Dependency facts for dependencies dimension
"""

import re
from pathlib import Path
from xml.etree import ElementTree as ET

from .....shared.utils.logger import logger
from ..base import CollectorOutput, DimensionCollector
from ..dependency_collector import RawDependency


class SpringDependencyCollector(DimensionCollector):
    """Extracts Maven and Gradle dependency facts."""

    DIMENSION = "dependencies"

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect dependency facts from Maven and Gradle build files."""
        self._log_start()

        # Maven
        for pom_file in self._find_files("pom.xml"):
            self._extract_maven_deps(pom_file)

        # Gradle
        for gradle_file in self._find_files("build.gradle"):
            self._extract_gradle_deps(gradle_file)

        for gradle_file in self._find_files("build.gradle.kts"):
            self._extract_gradle_deps(gradle_file)

        self._log_end()
        return self.output

    def _extract_maven_deps(self, pom_path: Path) -> None:
        """Extract dependencies from pom.xml."""
        try:
            tree = ET.parse(pom_path)
            root = tree.getroot()

            # Handle namespace
            ns = {"m": "http://maven.apache.org/POM/4.0.0"}

            # Find dependencies
            deps = root.findall(".//m:dependency", ns) or root.findall(".//dependency")
            rel_path = self._relative_path(pom_path)

            for dep in deps:
                group_id = dep.find("m:groupId", ns)
                artifact_id = dep.find("m:artifactId", ns)
                version = dep.find("m:version", ns)
                scope = dep.find("m:scope", ns)

                # Fallback without namespace
                if group_id is None:
                    group_id = dep.find("groupId")
                    artifact_id = dep.find("artifactId")
                    version = dep.find("version")
                    scope = dep.find("scope")

                if artifact_id is not None:
                    group = group_id.text if group_id is not None else ""
                    artifact = artifact_id.text
                    dep_name = f"{group}:{artifact}" if group else artifact

                    fact = RawDependency(
                        name=dep_name,
                        type="maven",
                        version=version.text if version is not None else "managed",
                        scope=scope.text if scope is not None else "compile",
                        group=group,
                    )
                    fact.add_evidence(rel_path, 1, 50, f"Maven dependency: {dep_name}")
                    self.output.add_fact(fact)

        except Exception as e:
            logger.debug(f"Failed to parse {pom_path}: {e}")

    def _extract_gradle_deps(self, gradle_path: Path) -> None:
        """Extract dependencies from build.gradle."""
        try:
            content = gradle_path.read_text(encoding="utf-8")
            rel_path = self._relative_path(gradle_path)

            # Find dependency declarations
            dep_pattern = re.compile(
                r"(implementation|api|compileOnly|runtimeOnly|testImplementation)\s*"
                r"['\(\"]+([^'\")\n]+)['\")]+",
                re.IGNORECASE,
            )

            for match in dep_pattern.finditer(content):
                scope = match.group(1).lower()
                dep = match.group(2).strip()
                line_num = content[: match.start()].count("\n") + 1

                # Map Gradle scopes to standard scopes
                scope_map = {
                    "implementation": "compile",
                    "api": "compile",
                    "compileonly": "provided",
                    "runtimeonly": "runtime",
                    "testimplementation": "test",
                }

                # Parse group:artifact:version format
                dep_parts = dep.split(":")
                dep_version = dep_parts[2] if len(dep_parts) >= 3 else ""

                fact = RawDependency(
                    name=dep,
                    type="gradle",
                    version=dep_version,
                    scope=scope_map.get(scope, "compile"),
                    group=dep_parts[0] if len(dep_parts) >= 2 else "",
                )
                fact.add_evidence(rel_path, line_num, line_num, f"Gradle dependency: {dep}")
                self.output.add_fact(fact)

        except Exception as e:
            logger.debug(f"Failed to parse {gradle_path}: {e}")
