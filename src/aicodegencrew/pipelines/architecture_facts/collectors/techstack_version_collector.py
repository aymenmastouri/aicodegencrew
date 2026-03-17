"""
TechStackVersionCollector - Extracts technology versions for upgrade planning.

Detects versions from ecosystem-specific build files and config files,
plus cross-cutting Docker/infrastructure versions.

Output -> tech_versions in system.json
"""

import re
from dataclasses import dataclass
from pathlib import Path

from ....shared.ecosystems import CollectorContext, EcosystemRegistry
from ....shared.utils.logger import logger
from .base import CollectorOutput, DimensionCollector, RawFact


@dataclass
class TechVersion(RawFact):
    """A technology version fact."""

    technology: str = ""
    version: str = ""
    source_file: str = ""
    category: str = ""  # language, framework, build_tool, library, runtime


class TechStackVersionCollector(DimensionCollector):
    """
    Collects technology versions from build files and config files.

    Essential for upgrade planning (e.g., Angular upgrade, Java upgrade).
    Delegates ecosystem-specific collection to ecosystem modules.
    """

    DIMENSION = "tech_versions"

    # Skip directories
    SKIP_DIRS = {"node_modules", "dist", "build", "target", ".git", "bin", "generated"}

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id
        self.versions: dict[str, TechVersion] = {}
        self._ecosystem_registry = EcosystemRegistry()

    def collect(self) -> CollectorOutput:
        """Collect all technology version facts."""
        self._log_start()

        # Build context for ecosystem modules
        ctx = self._build_context()

        # Delegate to each active ecosystem
        active_ecosystems = self._ecosystem_registry.detect(self.repo_path)
        for ecosystem in active_ecosystems:
            ecosystem.collect_versions(ctx)

        # Cross-cutting: Docker/Container versions (not ecosystem-specific)
        self._collect_dockerfile_versions()

        # Add all to output
        for version in self.versions.values():
            self.output.add_fact(version)

        logger.info(f"[TechStackVersionCollector] Found {len(self.versions)} technology versions")
        self._log_end()
        return self.output

    def _build_context(self) -> CollectorContext:
        """Create a CollectorContext for ecosystem version collection."""
        ctx = CollectorContext(self.repo_path)
        ctx.add_version = self._add_version
        ctx.find_files = self._find_files
        ctx.find_files_glob = self._find_files_glob
        return ctx

    def _add_version(self, technology: str, version: str, source_file: str, category: str):
        """Add a version fact if not already present or if version is more specific."""
        key = f"{technology}:{category}"

        # Clean version string
        version = version.strip().strip('"').strip("'")
        if not version:
            return

        # Skip if already have this tech — keep the more specific (longer) version
        # but use segment count, not string length, for comparison
        if key in self.versions:
            existing = self.versions[key]
            existing_segments = existing.version.count(".") + 1
            new_segments = version.count(".") + 1
            if existing_segments >= new_segments:
                return

        fact = TechVersion(
            name=f"{technology} {version}",
            technology=technology,
            version=version,
            source_file=source_file,
            category=category,
        )
        fact.add_evidence(path=source_file, line_start=1, line_end=10, reason=f"{technology} version: {version}")
        self.versions[key] = fact
        logger.debug(f"[TechStackVersionCollector] {technology}: {version} ({source_file})")

    # =========================================================================
    # Docker (cross-cutting — not ecosystem-specific)
    # =========================================================================

    def _collect_dockerfile_versions(self):
        """Collect base image versions from Dockerfiles."""
        for dockerfile in self._find_files_glob("Dockerfile*"):
            self._parse_dockerfile(dockerfile)

    def _parse_dockerfile(self, file_path: Path):
        """Parse Dockerfile for base image versions."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            rel_path = self._relative_path(file_path)

            for match in re.finditer(r"^FROM\s+([^:\s]+):([^\s]+)", content, re.MULTILINE):
                image = match.group(1)
                version = match.group(2)

                if "openjdk" in image.lower() or "eclipse-temurin" in image.lower():
                    self._add_version("Java (Docker)", version, rel_path, "runtime")
                elif "node" in image.lower():
                    self._add_version("Node.js (Docker)", version, rel_path, "runtime")
                elif "nginx" in image.lower():
                    self._add_version("Nginx (Docker)", version, rel_path, "runtime")
                elif "postgres" in image.lower():
                    self._add_version("PostgreSQL (Docker)", version, rel_path, "database")
                elif "oracle" in image.lower():
                    self._add_version("Oracle (Docker)", version, rel_path, "database")
                elif "gcc" in image.lower():
                    self._add_version("GCC (Docker)", version, rel_path, "runtime")
                elif "clang" in image.lower() or "llvm" in image.lower():
                    self._add_version("Clang/LLVM (Docker)", version, rel_path, "runtime")
        except Exception as e:
            logger.debug(f"[TechStackVersionCollector] Failed to parse {file_path}: {e}")

    # =========================================================================
    # Helpers
    # =========================================================================

    def _find_files(self, filename: str, root: Path | None = None) -> list[Path]:
        """Walk repo, pruning SKIP_DIRS at directory level.

        Using os.walk with in-place dir list modification avoids descending into
        node_modules, dist, target etc.
        """
        import os

        search_root = root or self.repo_path
        results = []
        for dirpath, dirnames, filenames in os.walk(search_root):
            dirnames[:] = [d for d in dirnames if d.lower() not in self.SKIP_DIRS]
            if filename in filenames:
                results.append(Path(dirpath) / filename)
        return results

    def _find_files_glob(self, pattern: str) -> list[Path]:
        """Like _find_files but matches a glob pattern (e.g. 'Dockerfile*')."""
        import fnmatch
        import os

        results = []
        for dirpath, dirnames, filenames in os.walk(self.repo_path):
            dirnames[:] = [d for d in dirnames if d.lower() not in self.SKIP_DIRS]
            for fname in filenames:
                if fnmatch.fnmatch(fname, pattern):
                    results.append(Path(dirpath) / fname)
        return results

    def _relative_path(self, file_path: Path) -> str:
        """Get relative path from repo root."""
        try:
            return str(file_path.relative_to(self.repo_path))
        except ValueError:
            return str(file_path)
