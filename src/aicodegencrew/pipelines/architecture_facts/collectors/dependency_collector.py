"""
Dependency Collector - Extracts project dependencies.

Detects:
- Maven dependencies (pom.xml)
- NPM packages (package.json)
- Python packages (requirements.txt, pyproject.toml)
- Gradle dependencies (build.gradle)

Output: Dependency facts for dependencies dimension
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from ....shared.utils.logger import logger
from .base import CollectorOutput, DimensionCollector, RawFact


@dataclass
class RawDependency(RawFact):
    """A dependency fact (external library/package)."""

    type: str = ""  # maven, npm, python, gradle
    version: str = ""
    scope: str = "compile"  # compile, runtime, test, dev
    group: str = ""  # groupId for Maven


class DependencyCollector(DimensionCollector):
    """
    Extracts project dependency facts.

    Scans build files:
    - pom.xml (Maven)
    - package.json (NPM)
    - requirements.txt, pyproject.toml (Python)
    - build.gradle (Gradle)
    """

    DIMENSION = "dependencies"

    def collect(self) -> CollectorOutput:
        """Collect dependency facts from build files."""
        self._log_start()

        # Maven
        for pom_file in self._find_files("pom.xml"):
            self._extract_maven_deps(pom_file)

        # NPM
        for pkg_file in self._find_files("package.json"):
            self._extract_npm_deps(pkg_file)

        # Python
        for req_file in self._find_files("requirements*.txt"):
            self._extract_python_deps(req_file)

        for pyproject in self._find_files("pyproject.toml"):
            self._extract_pyproject_deps(pyproject)

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

    def _extract_npm_deps(self, pkg_path: Path) -> None:
        """Extract dependencies from package.json."""
        try:
            content = pkg_path.read_text(encoding="utf-8")
            pkg_json = json.loads(content)
            rel_path = self._relative_path(pkg_path)

            # Regular dependencies
            deps = pkg_json.get("dependencies", {})
            for name, version in deps.items():
                fact = RawDependency(
                    name=name,
                    type="npm",
                    version=str(version),
                    scope="runtime",
                )
                fact.add_evidence(rel_path, 1, 50, f"NPM dependency: {name}")
                self.output.add_fact(fact)

            # Dev dependencies
            dev_deps = pkg_json.get("devDependencies", {})
            for name, version in dev_deps.items():
                fact = RawDependency(
                    name=name,
                    type="npm",
                    version=str(version),
                    scope="dev",
                )
                fact.add_evidence(rel_path, 1, 50, f"NPM devDependency: {name}")
                self.output.add_fact(fact)

        except Exception as e:
            logger.debug(f"Failed to parse {pkg_path}: {e}")

    def _extract_python_deps(self, req_path: Path) -> None:
        """Extract dependencies from requirements.txt."""
        try:
            content = req_path.read_text(encoding="utf-8")
            rel_path = self._relative_path(req_path)

            for line_num, line in enumerate(content.split("\n"), 1):
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue

                # Strip environment markers (e.g. "; python_version >= '3.8'")
                line = line.split(";")[0].strip()
                if not line:
                    continue

                # Parse: package[extras]>=version, package>=version, package
                match = re.match(r"^([a-zA-Z0-9_.-]+)(?:\[.*?\])?\s*([<>=!~]+)?(.+)?$", line)
                if match:
                    name = match.group(1)
                    version = (match.group(2) or "") + (match.group(3) or "")

                    fact = RawDependency(
                        name=name,
                        type="python",
                        version=version or "any",
                        scope="runtime",
                    )
                    fact.add_evidence(rel_path, line_num, line_num, f"Python dependency: {name}")
                    self.output.add_fact(fact)

        except Exception as e:
            logger.debug(f"Failed to parse {req_path}: {e}")

    def _extract_pyproject_deps(self, pyproject_path: Path) -> None:
        """Extract dependencies from pyproject.toml."""
        try:
            content = pyproject_path.read_text(encoding="utf-8")
            rel_path = self._relative_path(pyproject_path)

            # Parse [project] dependencies — find the first dependencies block after [project] section
            # Anchor to [project] section to avoid matching [tool.X.dependencies]
            project_match = re.search(r"^\[project\]", content, re.MULTILINE)
            project_content = content[project_match.start():] if project_match else content
            deps_match = re.search(r"dependencies\s*=\s*\[(.*?)\]", project_content, re.DOTALL)
            if deps_match:
                deps_str = deps_match.group(1)
                for dep in re.findall(r'["\']([^"\']+)["\']', deps_str):
                    # Parse "package>=version"
                    match = re.match(r"^([a-zA-Z0-9_-]+)(.*)$", dep)
                    if match:
                        name = match.group(1)
                        version = match.group(2) or "any"

                        fact = RawDependency(
                            name=name,
                            type="python",
                            version=version,
                            scope="runtime",
                        )
                        fact.add_evidence(rel_path, 1, 50, f"Python dependency: {name}")
                        self.output.add_fact(fact)

            # Parse [tool.poetry.dependencies]
            poetry_match = re.search(r"\[tool\.poetry\.dependencies\](.*?)(?:\[|$)", content, re.DOTALL)
            if poetry_match:
                for line in poetry_match.group(1).split("\n"):
                    if "=" in line and not line.strip().startswith("#"):
                        parts = line.split("=", 1)
                        name = parts[0].strip()
                        if name and name not in ("python",):
                            version = parts[1].strip().strip("\"'") if len(parts) > 1 else "any"

                            fact = RawDependency(
                                name=name,
                                type="python",
                                version=str(version),
                                scope="runtime",
                            )
                            fact.add_evidence(rel_path, 1, 50, f"Poetry dependency: {name}")
                            self.output.add_fact(fact)

        except Exception as e:
            logger.debug(f"Failed to parse {pyproject_path}: {e}")

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
