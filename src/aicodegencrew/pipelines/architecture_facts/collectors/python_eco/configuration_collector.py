"""Python Configuration Specialist — settings.py, pyproject.toml, config patterns."""

from __future__ import annotations

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawConfigFact


class PythonConfigurationCollector(DimensionCollector):
    DIMENSION = "configuration"

    DJANGO_SETTING_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]+\s*=", re.MULTILINE)

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        self._log_start()
        self._collect_settings_files()
        self._collect_pyproject_toml()
        self._collect_tool_configs()
        self._log_end()
        return self.output

    def _collect_settings_files(self):
        for path in self._find_files("settings.py"):
            content = self._read_file_content(path)
            keys = self.DJANGO_SETTING_PATTERN.findall(content)
            rel = self._relative_path(path)
            lines = content.splitlines()

            fact = RawConfigFact(
                name=f"django-settings:{self._relative_path(path)}",
                config_type="config_file",
                format="python",
                file_path=rel,
                key_count=len(keys),
                container_hint=self.container_id,
            )
            fact.add_evidence(rel, 1, min(len(lines), 30), f"Django settings: {len(keys)} config values")
            self.output.add_fact(fact)

        for path in self._find_files("config.py"):
            content = self._read_file_content(path)
            keys = self.DJANGO_SETTING_PATTERN.findall(content)
            if keys:
                rel = self._relative_path(path)
                fact = RawConfigFact(
                    name=f"python-config:{self._relative_path(path)}",
                    config_type="config_file",
                    format="python",
                    file_path=rel,
                    key_count=len(keys),
                    container_hint=self.container_id,
                )
                fact.add_evidence(rel, 1, 20, f"Python config: {len(keys)} config values")
                self.output.add_fact(fact)

    def _collect_pyproject_toml(self):
        for path in self._find_files("pyproject.toml"):
            content = self._read_file_content(path)
            lines = content.splitlines()
            rel = self._relative_path(path)

            # Count [tool.*] sections
            tool_sections = [l for l in lines if l.strip().startswith("[tool.")]
            fact = RawConfigFact(
                name=f"pyproject:{self._relative_path(path)}",
                config_type="config_file",
                format="toml",
                file_path=rel,
                key_count=len(lines),
                container_hint=self.container_id,
            )
            fact.metadata["tool_sections"] = len(tool_sections)
            fact.add_evidence(rel, 1, min(len(lines), 20), f"pyproject.toml: {len(tool_sections)} tool sections")
            self.output.add_fact(fact)

    def _collect_tool_configs(self):
        for pattern in ("setup.cfg", "tox.ini", ".flake8", "mypy.ini", ".pylintrc", "ruff.toml"):
            for path in self._find_files(pattern):
                content = self._read_file_content(path)
                lines = content.splitlines()
                rel = self._relative_path(path)

                fact = RawConfigFact(
                    name=f"tool-config:{path.name}",
                    config_type="config_file",
                    format="ini" if path.suffix in (".ini", ".cfg", "") else "toml",
                    file_path=rel,
                    key_count=len(lines),
                    container_hint=self.container_id,
                )
                fact.add_evidence(rel, 1, min(len(lines), 10), f"Tool config: {path.name}")
                self.output.add_fact(fact)
