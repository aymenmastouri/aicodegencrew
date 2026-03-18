"""Python Ecosystem — pip, poetry, setuptools, Django, Flask, FastAPI."""

from __future__ import annotations

import re
from pathlib import Path

from ._utils import count_line, find_python_block_end
from .base import CollectorContext, EcosystemDefinition, MarkerFile

# ── Regex patterns ──────────────────────────────────────────────────────────

_PY_CLASS = re.compile(r"^class\s+(\w+)\s*[:\(]", re.MULTILINE)
_PY_METHOD = re.compile(r"^    def\s+(\w+)\s*\(", re.MULTILINE)
_PY_DECORATOR = re.compile(r"^(?:    )?@(\w+)", re.MULTILINE)


class PythonEcosystem(EcosystemDefinition):
    """Python ecosystem: pip, poetry, setuptools."""

    @property
    def id(self) -> str:
        return "python"

    @property
    def name(self) -> str:
        return "Python"

    @property
    def priority(self) -> int:
        return 40

    @property
    def source_extensions(self) -> set[str]:
        return {".py", ".pyx", ".pxd"}

    @property
    def exclude_extensions(self) -> set[str]:
        return {".pyc", ".pyo"}

    @property
    def config_extensions(self) -> set[str]:
        return {".cfg", ".ini", ".toml"}

    @property
    def skip_directories(self) -> set[str]:
        return {"__pycache__", ".venv", "venv", ".tox", ".eggs", ".mypy_cache", ".pytest_cache"}

    @property
    def marker_files(self) -> list[MarkerFile]:
        return [
            MarkerFile("requirements.txt", "Python"),
            MarkerFile("pyproject.toml", "Python"),
            MarkerFile("setup.py", "Python"),
            MarkerFile("setup.cfg", "Python"),
        ]

    @property
    def ext_to_lang(self) -> dict[str, str]:
        return {".py": "python"}

    # ── Symbol Extraction ───────────────────────────────────────────────────

    def extract_symbols(self, path, content, lines, lang, module):
        records = []

        # Classes
        for m in _PY_CLASS.finditer(content):
            line_no = count_line(content, m.start())
            end_line = find_python_block_end(lines, line_no - 1)
            records.append(dict(
                symbol=m.group(1), kind="class", path=path,
                line=line_no, end_line=end_line, language="python", module=module,
            ))

        # Top-level functions (no indent)
        for m in re.finditer(r"^def\s+(\w+)\s*\(", content, re.MULTILINE):
            name = m.group(1)
            line_no = count_line(content, m.start())
            end_line = find_python_block_end(lines, line_no - 1)
            records.append(dict(
                symbol=name, kind="function", path=path,
                line=line_no, end_line=end_line, language="python", module=module,
            ))

        # Methods (indented def)
        for m in _PY_METHOD.finditer(content):
            name = m.group(1)
            line_no = count_line(content, m.start())
            # Skip if already captured as top-level function
            if any(r["symbol"] == name and r["line"] == line_no for r in records):
                continue
            end_line = find_python_block_end(lines, line_no - 1)
            records.append(dict(
                symbol=name, kind="method", path=path,
                line=line_no, end_line=end_line, language="python", module=module,
            ))

        # Decorators
        for m in _PY_DECORATOR.finditer(content):
            name = m.group(1)
            if name in ("property", "staticmethod", "classmethod", "abstractmethod"):
                continue
            line_no = count_line(content, m.start())
            records.append(dict(
                symbol=f"@{name}", kind="decorator", path=path,
                line=line_no, end_line=0, language="python", module=module,
            ))

        return records

    # ── Container Detection ─────────────────────────────────────────────────

    def detect_container(self, dir_path, name, ctx):
        pyproject = dir_path / "pyproject.toml"
        setup_py = dir_path / "setup.py"

        if not pyproject.exists() and not setup_py.exists():
            return None

        marker_file = pyproject if pyproject.exists() else setup_py
        content = ctx.read_file_content(marker_file)

        container_type = "backend"
        if ctx.is_test_directory(name):
            container_type = "test"

        technology = "Python"
        if "django" in content.lower():
            technology = "Django"
        elif "flask" in content.lower():
            technology = "Flask"
        elif "fastapi" in content.lower():
            technology = "FastAPI"

        return {
            "name": name,
            "type": container_type,
            "technology": technology,
            "root_path": ctx.relative_path(dir_path),
            "category": "application",
            "metadata": {"build_system": "python"},
            "evidence": [{
                "path": ctx.relative_path(marker_file),
                "line_start": 1,
                "line_end": 10,
                "reason": f"{technology} project: {name}",
            }],
        }

    # ── Version Collection ──────────────────────────────────────────────────

    def collect_versions(self, ctx):
        # .python-version files
        for version_file in ctx.find_files(".python-version"):
            try:
                version = version_file.read_text(encoding="utf-8").strip()
                if version:
                    ctx.add_version("Python", version, ctx.relative_path(version_file), "language")
            except Exception:
                pass

        # pyproject.toml: requires-python
        for pyproject in ctx.find_files("pyproject.toml"):
            try:
                content = pyproject.read_text(encoding="utf-8", errors="ignore")
                match = re.search(r'requires-python\s*=\s*["\']([^"\']+)', content)
                if match:
                    version = re.search(r"(\d+\.\d+(?:\.\d+)?)", match.group(1))
                    if version:
                        ctx.add_version("Python", version.group(1), ctx.relative_path(pyproject), "language")
            except Exception:
                pass

    # ── Dimension Delegation ──────────────────────────────────────────────

    def collect_dimension(self, dimension, repo_path, container_id=""):
        dispatch = {
            "build_system": self._collect_build_system,
            "runtime": self._collect_runtime,
            "dependencies": self._collect_dependencies,
            "security_details": self._collect_security_details,
            "validation": self._collect_validation,
            "error_handling": self._collect_error_handling,
            "tests": self._collect_tests,
            "data_model": self._collect_data_model,
            "workflows": self._collect_workflows,
            "configuration": self._collect_configuration,
            "logging_observability": self._collect_logging,
            "communication_patterns": self._collect_communication,
        }
        handler = dispatch.get(dimension)
        return handler(repo_path, container_id) if handler else ([], [])

    def _collect_build_system(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.python_eco.build_system_collector import PythonBuildSystemCollector
        output = PythonBuildSystemCollector(repo_path).collect()
        return output.facts, output.relations

    def _collect_runtime(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.python_eco.runtime_collector import PythonRuntimeCollector
        output = PythonRuntimeCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_dependencies(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.python_eco.dependency_collector import PythonDependencyCollector
        output = PythonDependencyCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_security_details(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.python_eco.security_collector import PythonSecurityCollector
        output = PythonSecurityCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_validation(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.python_eco.validation_collector import PythonValidationCollector
        output = PythonValidationCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_error_handling(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.python_eco.error_collector import PythonErrorCollector
        output = PythonErrorCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_tests(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.python_eco.test_collector import PythonTestCollector
        output = PythonTestCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_data_model(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.python_eco.data_model_collector import PythonDataModelCollector
        output = PythonDataModelCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_workflows(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.python_eco.workflow_collector import PythonWorkflowCollector
        output = PythonWorkflowCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_configuration(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.python_eco.configuration_collector import PythonConfigurationCollector
        output = PythonConfigurationCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_logging(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.python_eco.logging_collector import PythonLoggingCollector
        output = PythonLoggingCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    def _collect_communication(self, repo_path, container_id):
        from ...pipelines.architecture_facts.collectors.python_eco.communication_collector import PythonCommunicationCollector
        output = PythonCommunicationCollector(repo_path, container_id=container_id).collect()
        return output.facts, output.relations

    # ── Component Technologies ──────────────────────────────────────────────

    def get_component_technologies(self) -> set[str]:
        return {"Python", "Django", "Flask", "FastAPI"}

    # ── Component Collection ───────────────────────────────────────────────

    def collect_components(self, container, repo_path):
        # Lazy import to avoid circular dependency
        from ...pipelines.architecture_facts.collectors.python_eco import (
            PythonComponentCollector,
            PythonInterfaceCollector,
        )

        root_path = container.get("root_path", "")
        container_root = repo_path / root_path if root_path and root_path != "." else repo_path
        container_name = container.get("name", "backend")

        facts = []
        relations = []
        for CollectorClass in [PythonComponentCollector, PythonInterfaceCollector]:
            collector = CollectorClass(container_root, container_id=container_name)
            output = collector.collect()
            facts.extend(output.facts)
            relations.extend(output.relations)
        return facts, relations
