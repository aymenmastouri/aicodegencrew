"""Python Build System Specialist — Extracts Python build facts.

Detects:
- pyproject.toml build backends and scripts
- setup.py entry points
- tox.ini test environments
"""

import re
from pathlib import Path

from .....shared.utils.logger import logger
from ..base import CollectorOutput, DimensionCollector
from ..build_system_collector import RawBuildFact


class PythonBuildSystemCollector(DimensionCollector):
    """Extracts Python build system facts."""

    DIMENSION = "build_system"

    def __init__(self, repo_path: Path):
        super().__init__(repo_path)

    def collect(self) -> CollectorOutput:
        """Collect Python build system facts."""
        self._log_start()

        self._collect_python_build_system()

        self._log_end()
        return self.output

    # =========================================================================
    # Python Build System
    # =========================================================================

    def _collect_python_build_system(self) -> None:
        """Extract Python build system facts from pyproject.toml, setup.py, tox.ini."""
        # pyproject.toml
        for pyproject in self._find_files("pyproject.toml"):
            self._extract_pyproject_build(pyproject)

        # setup.py
        for setup_py in self._find_files("setup.py"):
            self._extract_setup_py(setup_py)

        # tox.ini
        for tox_ini in self._find_files("tox.ini"):
            self._extract_tox(tox_ini)

    def _extract_pyproject_build(self, pyproject_path: Path) -> None:
        """Extract build system facts from pyproject.toml."""
        content = self._read_file_content(pyproject_path)
        lines = self._read_file(pyproject_path)
        rel_path = self._relative_path(pyproject_path)
        module_path = self._relative_path(pyproject_path.parent)

        # Project name
        name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
        module_name = name_match.group(1) if name_match else pyproject_path.parent.name

        # Build backend
        plugins = []
        backend_match = re.search(r'build-backend\s*=\s*["\']([^"\']+)["\']', content)
        if backend_match:
            plugins.append(backend_match.group(1))

        # Scripts/entry points
        tasks = []
        for match in re.finditer(r'\[(?:project\.scripts|tool\.poetry\.scripts)\].*?(?=\[|\Z)', content, re.DOTALL):
            block = match.group(0)
            for line in block.split("\n"):
                if "=" in line and not line.strip().startswith("["):
                    script_name = line.split("=")[0].strip()
                    if script_name and not script_name.startswith("#"):
                        tasks.append(script_name)

        # Source directories
        source_dirs = []
        for candidate in ["src", "lib", "app"]:
            if (pyproject_path.parent / candidate).is_dir():
                source_dirs.append(candidate)

        # Properties
        properties: dict[str, str] = {}
        version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
        if version_match:
            properties["version"] = version_match.group(1)
        python_match = re.search(r'requires-python\s*=\s*["\']([^"\']+)["\']', content)
        if python_match:
            properties["requires_python"] = python_match.group(1)

        fact = RawBuildFact(
            name=f"pyproject:{module_name}",
            build_tool="python",
            module=module_name,
            module_path=module_path,
            tasks=tasks,
            source_dirs=source_dirs,
            plugins=plugins,
            wrapper_path=None,
            build_file=rel_path,
            properties=properties,
        )
        fact.add_evidence(
            path=rel_path,
            line_start=1,
            line_end=min(len(lines), 20),
            reason=f"Python project '{module_name}' (pyproject.toml)",
        )
        self.output.add_fact(fact)

    def _extract_setup_py(self, setup_path: Path) -> None:
        """Extract build system facts from setup.py."""
        content = self._read_file_content(setup_path)
        lines = self._read_file(setup_path)
        rel_path = self._relative_path(setup_path)
        module_path = self._relative_path(setup_path.parent)

        # Project name
        name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
        module_name = name_match.group(1) if name_match else setup_path.parent.name

        tasks = []
        # Entry points / console_scripts
        for match in re.finditer(r'console_scripts.*?\[([^\]]+)\]', content, re.DOTALL):
            for entry in re.findall(r'["\'](\w+)\s*=', match.group(1)):
                tasks.append(entry)

        fact = RawBuildFact(
            name=f"setup.py:{module_name}",
            build_tool="python",
            module=module_name,
            module_path=module_path,
            tasks=tasks,
            source_dirs=[],
            plugins=[],
            wrapper_path=None,
            build_file=rel_path,
            properties={},
        )
        fact.add_evidence(
            path=rel_path,
            line_start=1,
            line_end=min(len(lines), 20),
            reason=f"Python project '{module_name}' (setup.py)",
        )
        self.output.add_fact(fact)

    def _extract_tox(self, tox_path: Path) -> None:
        """Extract tox environment definitions as build tasks."""
        content = self._read_file_content(tox_path)
        lines = self._read_file(tox_path)
        rel_path = self._relative_path(tox_path)
        module_path = self._relative_path(tox_path.parent)

        # Extract [testenv:name] sections
        environments = re.findall(r"\[testenv:(\w+)\]", content)
        # Also get the default envlist
        envlist_match = re.search(r"envlist\s*=\s*(.+)", content)
        if envlist_match:
            for env in re.findall(r"(\w+)", envlist_match.group(1)):
                if env not in environments:
                    environments.append(env)

        if environments:
            fact = RawBuildFact(
                name=f"tox:{tox_path.parent.name}",
                build_tool="tox",
                module=tox_path.parent.name,
                module_path=module_path,
                tasks=environments,
                source_dirs=[],
                plugins=[],
                wrapper_path=None,
                build_file=rel_path,
                properties={},
            )
            fact.add_evidence(
                path=rel_path,
                line_start=1,
                line_end=min(len(lines), 20),
                reason=f"tox environments: {', '.join(environments[:5])}",
            )
            self.output.add_fact(fact)
