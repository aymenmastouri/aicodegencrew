"""C/C++ Build System Specialist — Extracts CMake and Meson build facts.

Detects:
- CMake projects, targets (executables, libraries), subdirectories
- Meson projects, targets, subdirectories
"""

import re
from pathlib import Path

from .....shared.utils.logger import logger
from ..base import CollectorOutput, DimensionCollector
from ..build_system_collector import RawBuildFact


class CppBuildSystemCollector(DimensionCollector):
    """Extracts CMake and Meson build system facts."""

    DIMENSION = "build_system"

    def __init__(self, repo_path: Path):
        super().__init__(repo_path)

    def collect(self) -> CollectorOutput:
        """Collect CMake and Meson build system facts."""
        self._log_start()

        self._collect_cmake()
        self._collect_meson()

        self._log_end()
        return self.output

    # =========================================================================
    # CMake
    # =========================================================================

    def _collect_cmake(self) -> None:
        """Extract CMake build system facts."""
        cmake_files = self._find_files("CMakeLists.txt")
        if not cmake_files:
            return

        logger.info(f"  [CMake] Found {len(cmake_files)} CMakeLists.txt file(s)...")

        for cmake_file in cmake_files:
            self._extract_cmake_module(cmake_file)

    def _extract_cmake_module(self, cmake_file: Path) -> None:
        """Extract facts from a single CMakeLists.txt."""
        content = self._read_file_content(cmake_file)
        lines = self._read_file(cmake_file)
        rel_path = self._relative_path(cmake_file)
        module_path = self._relative_path(cmake_file.parent)

        # Project name
        project_match = re.search(r"project\s*\(\s*(\w+)", content, re.IGNORECASE)
        module_name = project_match.group(1) if project_match else cmake_file.parent.name

        # Targets: executables and libraries
        tasks = []
        executables = []
        libraries = []
        for match in re.finditer(r"add_executable\s*\(\s*(\w+)", content):
            tasks.append(match.group(1))
            executables.append(match.group(1))
        for match in re.finditer(r"add_library\s*\(\s*(\w+)", content):
            tasks.append(match.group(1))
            libraries.append(match.group(1))
        for match in re.finditer(r"add_custom_target\s*\(\s*(\w+)", content):
            tasks.append(match.group(1))

        # Subdirectories
        subdirs = []
        for match in re.finditer(r"add_subdirectory\s*\(\s*(\w+)", content):
            subdirs.append(match.group(1))

        # Source dirs heuristic
        source_dirs = self._detect_source_dirs(cmake_file.parent)
        if not source_dirs:
            for candidate in ["src", "source", "lib", "include"]:
                if (cmake_file.parent / candidate).is_dir():
                    source_dirs.append(candidate)

        # Properties
        properties: dict[str, str] = {}
        cmake_ver = re.search(r"cmake_minimum_required\s*\(\s*VERSION\s+([0-9.]+)", content, re.IGNORECASE)
        if cmake_ver:
            properties["cmake_version"] = cmake_ver.group(1)
        cxx_std = re.search(r"CMAKE_CXX_STANDARD\s+(\d+)", content)
        if cxx_std:
            properties["cxx_standard"] = cxx_std.group(1)
        c_std = re.search(r"CMAKE_C_STANDARD\s+(\d+)", content)
        if c_std:
            properties["c_standard"] = c_std.group(1)

        fact = RawBuildFact(
            name=f"cmake:{module_name}",
            build_tool="cmake",
            module=module_name,
            module_path=module_path,
            tasks=tasks,
            source_dirs=source_dirs,
            plugins=[],
            wrapper_path=None,
            parent_module=None,
            build_file=rel_path,
            properties=properties,
            metadata={
                **({"subdirectories": subdirs} if subdirs else {}),
                **({"executables": executables} if executables else {}),
                **({"libraries": libraries} if libraries else {}),
            },
        )
        fact.add_evidence(
            path=rel_path,
            line_start=1,
            line_end=min(len(lines), 20),
            reason=f"CMake project '{module_name}'",
        )
        self.output.add_fact(fact)

    # =========================================================================
    # Meson
    # =========================================================================

    def _collect_meson(self) -> None:
        """Extract Meson build system facts."""
        meson_files = self._find_files("meson.build")
        if not meson_files:
            return

        logger.info(f"  [Meson] Found {len(meson_files)} meson.build file(s)...")

        for meson_file in meson_files:
            self._extract_meson_module(meson_file)

    def _extract_meson_module(self, meson_file: Path) -> None:
        """Extract facts from a single meson.build."""
        content = self._read_file_content(meson_file)
        lines = self._read_file(meson_file)
        rel_path = self._relative_path(meson_file)
        module_path = self._relative_path(meson_file.parent)

        # Project name
        project_match = re.search(r"project\s*\(\s*'(\w+)'", content)
        module_name = project_match.group(1) if project_match else meson_file.parent.name

        # Targets
        tasks = []
        for match in re.finditer(r"executable\s*\(\s*'(\w+)'", content):
            tasks.append(match.group(1))
        for match in re.finditer(r"(?:shared_library|static_library|library)\s*\(\s*'(\w+)'", content):
            tasks.append(match.group(1))

        # Subdirectories
        subdirs = []
        for match in re.finditer(r"subdir\s*\(\s*'(\w+)'", content):
            subdirs.append(match.group(1))

        source_dirs = self._detect_source_dirs(meson_file.parent)

        fact = RawBuildFact(
            name=f"meson:{module_name}",
            build_tool="meson",
            module=module_name,
            module_path=module_path,
            tasks=tasks,
            source_dirs=source_dirs,
            plugins=[],
            wrapper_path=None,
            parent_module=None,
            build_file=rel_path,
            properties={},
            metadata={"subdirectories": subdirs} if subdirs else {},
        )
        fact.add_evidence(
            path=rel_path,
            line_start=1,
            line_end=min(len(lines), 20),
            reason=f"Meson project '{module_name}'",
        )
        self.output.add_fact(fact)
