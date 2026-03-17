"""Python Dependency Specialist — Extracts Python dependency facts.

Detects:
- Python packages (requirements.txt, requirements*.txt)
- Python packages (pyproject.toml — [project] and [tool.poetry.dependencies])

Output: Dependency facts for dependencies dimension
"""

import re
from pathlib import Path

from .....shared.utils.logger import logger
from ..base import CollectorOutput, DimensionCollector
from ..dependency_collector import RawDependency


class PythonDependencyCollector(DimensionCollector):
    """Extracts Python dependency facts from requirements and pyproject files."""

    DIMENSION = "dependencies"

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect dependency facts from Python build files."""
        self._log_start()

        for req_file in self._find_files("requirements*.txt"):
            self._extract_python_deps(req_file)

        for pyproject in self._find_files("pyproject.toml"):
            self._extract_pyproject_deps(pyproject)

        self._log_end()
        return self.output

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
                        version=version or "",
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
                        version = match.group(2) or ""

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
