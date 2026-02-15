"""Repo Manifest Builder — Step 1b of the enhanced Discover phase.

Scans discovered file paths to produce a repo_manifest.json with:
- Framework detection (via marker files)
- File stats by extension and module
- Git commit hash
- Noise folder identification
"""

from __future__ import annotations

import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from ...shared.utils.logger import setup_logger
from .models import ModuleStats, RepoManifest

logger = setup_logger(__name__)

# Marker files → framework name
FRAMEWORK_MARKERS: dict[str, str] = {
    "pom.xml": "Spring/Maven",
    "build.gradle": "Spring/Gradle",
    "build.gradle.kts": "Spring/Gradle-KTS",
    "angular.json": "Angular",
    "package.json": "Node.js",
    "requirements.txt": "Python",
    "pyproject.toml": "Python",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "Gemfile": "Ruby",
    "composer.json": "PHP",
    "Dockerfile": "Docker",
    "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml": "Docker Compose",
    ".gitlab-ci.yml": "GitLab CI",
    ".github/workflows": "GitHub Actions",
    "Jenkinsfile": "Jenkins",
}

# Directories that are typically noise for analysis
NOISE_PATTERNS: set[str] = {
    "node_modules",
    ".git",
    "__pycache__",
    ".gradle",
    ".mvn",
    "target",
    "build",
    "dist",
    ".angular",
    ".cache",
    ".idea",
    ".vscode",
    "vendor",
    "venv",
    ".venv",
}


class ManifestBuilder:
    """Builds a RepoManifest from discovered file paths."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path

    def build(self, all_file_paths: list[str]) -> RepoManifest:
        """Build manifest from file paths.

        Args:
            all_file_paths: Absolute file paths from discovery step.

        Returns:
            Populated RepoManifest.
        """
        commit = self._get_commit_hash()
        frameworks = self._detect_frameworks()
        noise_folders = self._detect_noise_folders()
        stats, modules = self._compute_stats(all_file_paths)

        manifest = RepoManifest(
            repo_root=str(self.repo_path),
            commit=commit,
            stats=stats,
            modules=[m.__dict__ for m in modules],
            frameworks=frameworks,
            noise_folders=noise_folders,
        )

        logger.info(
            f"[Manifest] {stats.get('total_files', 0)} files, {len(frameworks)} frameworks, {len(modules)} modules"
        )
        return manifest

    def write(self, manifest: RepoManifest, output_path: Path) -> None:
        """Write manifest to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info(f"[Manifest] Written to {output_path}")

    def _get_commit_hash(self) -> str:
        """Get current HEAD commit hash via git."""
        try:
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.debug(f"[Manifest] git rev-parse failed: {e}")
        return ""

    def _detect_frameworks(self) -> list[str]:
        """Detect frameworks via marker files in repo root and first-level dirs."""
        found: set[str] = set()

        for marker, framework in FRAMEWORK_MARKERS.items():
            marker_path = self.repo_path / marker
            if marker_path.exists():
                found.add(framework)

        # Also scan first-level subdirectories for multi-module repos
        try:
            for child in self.repo_path.iterdir():
                if child.is_dir() and child.name not in NOISE_PATTERNS:
                    for marker, framework in FRAMEWORK_MARKERS.items():
                        if (child / marker).exists():
                            found.add(framework)
        except OSError:
            pass

        return sorted(found)

    def _detect_noise_folders(self) -> list[str]:
        """Return noise folders that actually exist in the repo."""
        existing = []
        try:
            for child in self.repo_path.iterdir():
                if child.is_dir() and child.name in NOISE_PATTERNS:
                    existing.append(child.name)
        except OSError:
            pass
        return sorted(existing)

    def _compute_stats(self, all_file_paths: list[str]) -> tuple[dict[str, int], list[ModuleStats]]:
        """Compute file stats by extension and by top-level module."""
        ext_counter: Counter[str] = Counter()
        module_files: dict[str, list[str]] = defaultdict(list)

        for fp in all_file_paths:
            try:
                rel = Path(fp).relative_to(self.repo_path).as_posix()
            except ValueError:
                rel = fp

            ext = Path(fp).suffix.lower() or "(no ext)"
            ext_counter[ext] += 1

            parts = rel.split("/")
            module_name = parts[0] if len(parts) > 1 else "(root)"
            module_files[module_name].append(fp)

        # Build module stats
        modules = []
        for name, files in sorted(module_files.items()):
            mod_ext: Counter[str] = Counter()
            for f in files:
                mod_ext[Path(f).suffix.lower() or "(no ext)"] += 1
            modules.append(
                ModuleStats(
                    name=name,
                    file_count=len(files),
                    extensions=dict(mod_ext.most_common()),
                )
            )

        stats = {
            "total_files": len(all_file_paths),
            "total_extensions": len(ext_counter),
            **{f"ext_{k}": v for k, v in ext_counter.most_common(20)},
        }

        return stats, modules
