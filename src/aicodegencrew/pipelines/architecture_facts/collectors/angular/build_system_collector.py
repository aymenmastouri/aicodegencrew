"""Angular Build System Specialist — Extracts npm and Angular build facts.

Detects:
- npm scripts and workspaces from package.json
- Angular project architect targets from angular.json
- TypeScript path mappings from tsconfig.json
"""

import json
import re
from pathlib import Path

from .....shared.utils.logger import logger
from ..base import CollectorOutput, DimensionCollector
from ..build_system_collector import RawBuildFact


class AngularBuildSystemCollector(DimensionCollector):
    """Extracts npm and Angular build system facts."""

    DIMENSION = "build_system"

    def __init__(self, repo_path: Path):
        super().__init__(repo_path)

    def collect(self) -> CollectorOutput:
        """Collect npm and Angular build system facts."""
        self._log_start()

        self._collect_npm()
        self._collect_angular()

        self._log_end()
        return self.output

    # =========================================================================
    # npm
    # =========================================================================

    def _collect_npm(self) -> None:
        """Extract npm build system facts from package.json files."""
        pkg_files = self._find_files("package.json")
        if not pkg_files:
            return

        logger.info(f"  [npm] Found {len(pkg_files)} package.json file(s)...")

        for pkg_file in pkg_files:
            self._extract_npm_module(pkg_file)

    def _extract_npm_module(self, pkg_file: Path) -> None:
        """Extract facts from a single package.json."""
        try:
            with open(pkg_file, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        name = data.get("name", pkg_file.parent.name)
        scripts = data.get("scripts", {})
        rel_pkg = self._relative_path(pkg_file)
        module_path = self._relative_path(pkg_file.parent)
        lines = self._read_file(pkg_file)

        # Classify scripts
        tasks = list(scripts.keys())

        # Detect source dirs
        source_dirs = self._detect_source_dirs(pkg_file.parent)

        # Key properties
        properties: dict[str, str] = {}
        if data.get("version"):
            properties["version"] = data["version"]
        if data.get("engines"):
            for eng_key, eng_val in data["engines"].items():
                properties[f"engine.{eng_key}"] = eng_val

        fact = RawBuildFact(
            name=f"npm:{name}",
            build_tool="npm",
            module=name,
            module_path=module_path,
            tasks=tasks,
            source_dirs=source_dirs,
            plugins=[],
            wrapper_path=None,
            build_file=rel_pkg,
            properties=properties,
            metadata={"scripts": scripts},
        )
        fact.add_evidence(
            path=rel_pkg,
            line_start=1,
            line_end=min(len(lines), 20),
            reason=f"npm package.json for '{name}'",
        )
        self.output.add_fact(fact)

    # =========================================================================
    # Angular
    # =========================================================================

    def _collect_angular(self) -> None:
        """Extract Angular build system facts from angular.json."""
        angular_files = self._find_files("angular.json")
        if not angular_files:
            return

        logger.info(f"  [Angular] Found {len(angular_files)} angular.json file(s)...")

        for angular_file in angular_files:
            self._extract_angular_projects(angular_file)

        # Also scan tsconfig for build-relevant path mappings
        tsconfig_files = self._find_files("tsconfig.json")
        tsconfig_files.extend(self._find_files("tsconfig.app.json"))
        for tsconfig_file in tsconfig_files:
            self._extract_tsconfig_paths(tsconfig_file)

    def _extract_angular_projects(self, angular_file: Path) -> None:
        """Extract architect targets per Angular project."""
        try:
            with open(angular_file, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        projects = data.get("projects", {})
        rel_file = self._relative_path(angular_file)
        lines = self._read_file(angular_file)

        for proj_name, proj_config in projects.items():
            architect = proj_config.get("architect", {})
            targets = list(architect.keys())
            root = proj_config.get("root", "")
            source_root = proj_config.get("sourceRoot", "")

            source_dirs = [source_root] if source_root else []

            fact = RawBuildFact(
                name=f"angular:{proj_name}",
                build_tool="angular",
                module=proj_name,
                module_path=root,
                tasks=targets,
                source_dirs=source_dirs,
                plugins=[],
                wrapper_path=None,
                build_file=rel_file,
                properties={},
            )
            fact.add_evidence(
                path=rel_file,
                line_start=1,
                line_end=min(len(lines), 10),
                reason=f"Angular project '{proj_name}' with targets: {', '.join(targets)}",
            )
            self.output.add_fact(fact)

    def _extract_tsconfig_paths(self, tsconfig_file: Path) -> None:
        """Extract build-relevant path mappings from tsconfig."""
        try:
            content = self._read_file_content(tsconfig_file)
            # Strip comments (tsconfig allows them)
            content = re.sub(r"//.*?\n", "\n", content)
            content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
            data = json.loads(content)
        except (json.JSONDecodeError, OSError):
            return

        compiler_opts = data.get("compilerOptions", {})
        paths = compiler_opts.get("paths", {})
        if not paths:
            return

        rel_file = self._relative_path(tsconfig_file)
        lines = self._read_file(tsconfig_file)

        fact = RawBuildFact(
            name=f"tsconfig:{tsconfig_file.stem}",
            build_tool="angular",
            module=tsconfig_file.stem,
            module_path=self._relative_path(tsconfig_file.parent),
            tasks=[],
            source_dirs=[],
            plugins=[],
            wrapper_path=None,
            build_file=rel_file,
            properties={},
            metadata={"path_mappings": paths},
        )
        fact.add_evidence(
            path=rel_file,
            line_start=1,
            line_end=min(len(lines), 10),
            reason=f"TypeScript path mappings: {len(paths)} entries",
        )
        self.output.add_fact(fact)
