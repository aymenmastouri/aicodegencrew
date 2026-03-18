"""C++ Configuration Specialist — CMake options, config headers, tool configs."""

from __future__ import annotations

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawConfigFact


class CppConfigurationCollector(DimensionCollector):
    DIMENSION = "configuration"

    CMAKE_OPTION_PATTERN = re.compile(r"option\s*\(\s*(\w+)", re.IGNORECASE)
    CMAKE_SET_CACHE_PATTERN = re.compile(r'set\s*\(\s*(\w+)\s+[^)]*CACHE', re.IGNORECASE)

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        self._log_start()
        self._collect_cmake_options()
        self._collect_config_headers()
        self._collect_tool_configs()
        self._log_end()
        return self.output

    def _collect_cmake_options(self):
        for path in self._find_files("CMakeLists.txt"):
            content = self._read_file_content(path)
            options = self.CMAKE_OPTION_PATTERN.findall(content)
            cache_vars = self.CMAKE_SET_CACHE_PATTERN.findall(content)
            all_vars = options + cache_vars
            if all_vars:
                rel = self._relative_path(path)
                lines = content.splitlines()
                fact = RawConfigFact(
                    name=f"cmake-options:{rel}",
                    config_type="config_file",
                    format="cmake",
                    file_path=rel,
                    key_count=len(all_vars),
                    container_hint=self.container_id,
                )
                fact.metadata["options"] = options
                fact.metadata["cache_variables"] = cache_vars
                fact.add_evidence(rel, 1, min(len(lines), 20), f"CMake: {len(options)} options, {len(cache_vars)} cache vars")
                self.output.add_fact(fact)

    def _collect_config_headers(self):
        for path in self._find_files("*.h.in"):
            content = self._read_file_content(path)
            defines = re.findall(r"#cmakedefine\s+(\w+)", content)
            rel = self._relative_path(path)
            lines = content.splitlines()
            fact = RawConfigFact(
                name=f"config-header:{path.name}",
                config_type="config_file",
                format="cmake",
                file_path=rel,
                key_count=len(defines),
                container_hint=self.container_id,
            )
            fact.add_evidence(rel, 1, min(len(lines), 15), f"Config header template: {len(defines)} defines")
            self.output.add_fact(fact)

    def _collect_tool_configs(self):
        for pattern in (".clang-format", ".clang-tidy", "conanfile.txt", "conanfile.py", "vcpkg.json"):
            for path in self._find_files(pattern):
                content = self._read_file_content(path)
                lines = content.splitlines()
                rel = self._relative_path(path)
                fact = RawConfigFact(
                    name=f"tool-config:{path.name}",
                    config_type="config_file",
                    format="yaml" if path.suffix in (".yml", ".yaml") else "text",
                    file_path=rel,
                    key_count=len(lines),
                    container_hint=self.container_id,
                )
                fact.add_evidence(rel, 1, min(len(lines), 10), f"C++ tool config: {path.name}")
                self.output.add_fact(fact)
