"""C/C++ Dependency Specialist — Extracts CMake, Conan, and vcpkg dependency facts.

Detects:
- CMake dependencies (CMakeLists.txt): find_package, FetchContent, ExternalProject
- Conan dependencies (conanfile.txt)
- vcpkg dependencies (vcpkg.json)

Output: Dependency facts for dependencies dimension
"""

import json
import re
from pathlib import Path

from .....shared.utils.logger import logger
from ..base import CollectorOutput, DimensionCollector
from ..dependency_collector import RawDependency


class CppDependencyCollector(DimensionCollector):
    """Extracts C/C++ dependency facts from CMake, Conan, and vcpkg files."""

    DIMENSION = "dependencies"

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect dependency facts from C/C++ build files."""
        self._log_start()

        # CMake
        for cmake_file in self._find_files("CMakeLists.txt"):
            self._extract_cmake_deps(cmake_file)

        # Conan
        for conan_file in self._find_files("conanfile.txt"):
            self._extract_conan_deps(conan_file)

        # vcpkg
        for vcpkg_file in self._find_files("vcpkg.json"):
            self._extract_vcpkg_deps(vcpkg_file)

        self._log_end()
        return self.output

    def _extract_cmake_deps(self, cmake_path: Path) -> None:
        """Extract dependencies from CMakeLists.txt: find_package, FetchContent, ExternalProject."""
        try:
            content = cmake_path.read_text(encoding="utf-8", errors="ignore")
            rel_path = self._relative_path(cmake_path)

            # find_package(Name ...)
            for match in re.finditer(r"find_package\s*\(\s*(\w+)(?:\s+([0-9.]+))?", content):
                name = match.group(1)
                version = match.group(2) or ""
                line_num = content[: match.start()].count("\n") + 1

                fact = RawDependency(
                    name=name,
                    type="cmake",
                    version=version,
                    scope="compile",
                )
                fact.add_evidence(rel_path, line_num, line_num, f"CMake find_package: {name}")
                self.output.add_fact(fact)

            # FetchContent_Declare(name ...)
            for match in re.finditer(r"FetchContent_Declare\s*\(\s*(\w+)", content):
                name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                # Try to extract GIT_TAG for version
                fetch_block = content[match.start():match.start() + 500]
                tag_match = re.search(r"GIT_TAG\s+(\S+)", fetch_block)
                version = tag_match.group(1) if tag_match else ""

                fact = RawDependency(
                    name=name,
                    type="cmake",
                    version=version,
                    scope="compile",
                )
                fact.metadata["cmake_mechanism"] = "fetchcontent"
                fact.add_evidence(rel_path, line_num, line_num + 5, f"CMake FetchContent: {name}")
                self.output.add_fact(fact)

            # ExternalProject_Add(name ...)
            for match in re.finditer(r"ExternalProject_Add\s*\(\s*(\w+)", content):
                name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                fact = RawDependency(
                    name=name,
                    type="cmake",
                    version="",
                    scope="compile",
                )
                fact.metadata["cmake_mechanism"] = "external_project"
                fact.add_evidence(rel_path, line_num, line_num + 5, f"CMake ExternalProject: {name}")
                self.output.add_fact(fact)

        except Exception as e:
            logger.debug(f"Failed to parse CMake {cmake_path}: {e}")

    def _extract_conan_deps(self, conan_path: Path) -> None:
        """Extract dependencies from conanfile.txt [requires] section."""
        try:
            content = conan_path.read_text(encoding="utf-8", errors="ignore")
            rel_path = self._relative_path(conan_path)

            in_requires = False
            for line_num, line in enumerate(content.split("\n"), 1):
                line = line.strip()
                if line == "[requires]":
                    in_requires = True
                    continue
                if line.startswith("[") and line.endswith("]"):
                    in_requires = False
                    continue
                if in_requires and "/" in line and not line.startswith("#"):
                    parts = line.split("/", 1)
                    name = parts[0].strip()
                    version = parts[1].strip().split("@")[0].strip() if len(parts) > 1 else ""

                    fact = RawDependency(
                        name=name,
                        type="conan",
                        version=version or "",
                        scope="compile",
                    )
                    fact.add_evidence(rel_path, line_num, line_num, f"Conan dependency: {name}")
                    self.output.add_fact(fact)

        except Exception as e:
            logger.debug(f"Failed to parse {conan_path}: {e}")

    def _extract_vcpkg_deps(self, vcpkg_path: Path) -> None:
        """Extract dependencies from vcpkg.json."""
        try:
            content = vcpkg_path.read_text(encoding="utf-8")
            pkg = json.loads(content)
            rel_path = self._relative_path(vcpkg_path)

            for dep in pkg.get("dependencies", []):
                if isinstance(dep, str):
                    name = dep
                    version = ""
                elif isinstance(dep, dict):
                    name = dep.get("name", "")
                    version = dep.get("version>=", dep.get("version", ""))
                else:
                    continue

                if name:
                    fact = RawDependency(
                        name=name,
                        type="vcpkg",
                        version=str(version) if version else "",
                        scope="compile",
                    )
                    fact.add_evidence(rel_path, 1, 20, f"vcpkg dependency: {name}")
                    self.output.add_fact(fact)

        except Exception as e:
            logger.debug(f"Failed to parse {vcpkg_path}: {e}")
