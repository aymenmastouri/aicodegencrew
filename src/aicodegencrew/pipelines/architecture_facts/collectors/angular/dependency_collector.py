"""Angular/NPM Dependency Specialist — Extracts NPM dependency facts.

Detects:
- NPM packages (package.json)
- Both dependencies and devDependencies

Output: Dependency facts for dependencies dimension
"""

import json
from pathlib import Path

from .....shared.utils.logger import logger
from ..base import CollectorOutput, DimensionCollector
from ..dependency_collector import RawDependency


class AngularDependencyCollector(DimensionCollector):
    """Extracts NPM dependency facts from package.json files."""

    DIMENSION = "dependencies"

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect dependency facts from package.json files."""
        self._log_start()

        for pkg_file in self._find_files("package.json"):
            self._extract_npm_deps(pkg_file)

        self._log_end()
        return self.output

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
