"""Ecosystem Strategy Pattern — Base classes.

Each ecosystem (Java/JVM, JavaScript/TypeScript, Python, C/C++) implements
EcosystemDefinition to provide its own symbol extraction, container detection,
version collection, and component routing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass
class MarkerFile:
    """A file whose presence indicates an ecosystem or framework."""

    filename: str
    framework_label: str


class CollectorContext:
    """Provides repository context and utility functions to ecosystem modules.

    Created by the calling collector and passed to ecosystem detection methods
    so they can perform file I/O and path resolution without importing
    collector internals.
    """

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        # Callbacks — set by the calling collector before invoking ecosystem methods
        self.is_test_directory: Callable[[str], bool] = lambda _: False
        self.add_version: Callable[[str, str, str, str], None] = lambda *a: None
        self.find_files: Callable[..., list[Path]] = lambda *a, **kw: []
        self.find_files_glob: Callable[[str], list[Path]] = lambda _: []

    def relative_path(self, path: Path) -> str:
        """Get path relative to repo root."""
        try:
            return str(path.relative_to(self.repo_path))
        except ValueError:
            return str(path)

    @staticmethod
    def read_file_content(path: Path) -> str:
        """Read file content as string."""
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

    @staticmethod
    def read_file_lines(path: Path) -> list[str]:
        """Read file as list of lines (with line endings)."""
        try:
            return path.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)
        except Exception:
            return []

    @staticmethod
    def find_line_number(lines: list[str], search: str) -> int:
        """Find 1-based line number containing search string."""
        for i, line in enumerate(lines, 1):
            if search in line:
                return i
        return 1


class EcosystemDefinition(ABC):
    """Abstract base class defining an ecosystem (language + build tools + frameworks).

    Each ecosystem implementation provides:
    - Identity: id, name
    - File classification: source/exclude/config extensions, skip directories
    - Detection: marker files that indicate this ecosystem is present
    - Symbol extraction: regex-based symbol extraction for its languages
    - Container detection: identifying deployable units from build files
    - Version collection: extracting technology versions from config files
    - Component collection: running specialist collectors
    """

    # --- Identity ---
    @property
    @abstractmethod
    def id(self) -> str:
        """Unique ecosystem identifier (e.g., 'java_jvm')."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name (e.g., 'Java/JVM')."""

    @property
    def priority(self) -> int:
        """Detection priority — lower number = checked first for containers."""
        return 100

    # --- File Extensions ---
    @property
    @abstractmethod
    def source_extensions(self) -> set[str]:
        """File extensions that belong to this ecosystem (e.g., {'.java', '.kt'})."""

    @property
    @abstractmethod
    def exclude_extensions(self) -> set[str]:
        """Binary/generated extensions to skip (e.g., {'.class', '.jar'})."""

    @property
    def config_extensions(self) -> set[str]:
        """Config file extensions relevant to this ecosystem."""
        return set()

    @property
    @abstractmethod
    def skip_directories(self) -> set[str]:
        """Directories that are noise for this ecosystem."""

    # --- Detection ---
    @property
    @abstractmethod
    def marker_files(self) -> list[MarkerFile]:
        """Files whose presence indicates this ecosystem."""

    def detect(self, repo_path: Path) -> bool:
        """Check if this ecosystem is present in the repository.

        Default: checks for marker files in root and one level deep.
        """
        for marker in self.marker_files:
            if (repo_path / marker.filename).exists():
                return True
        try:
            for child in repo_path.iterdir():
                if child.is_dir() and not child.name.startswith("."):
                    for marker in self.marker_files:
                        if (child / marker.filename).exists():
                            return True
        except OSError:
            pass
        return False

    # --- Symbol Extraction ---
    @property
    @abstractmethod
    def ext_to_lang(self) -> dict[str, str]:
        """Mapping of file extension to language name for symbol extraction."""

    @abstractmethod
    def extract_symbols(
        self, path: str, content: str, lines: list[str], lang: str, module: str
    ) -> list[dict]:
        """Extract symbols from a source file.

        Args:
            path: Relative file path.
            content: Full file content.
            lines: Content split into lines.
            lang: Language identifier from ext_to_lang.
            module: Top-level module name.

        Returns:
            List of dicts with SymbolRecord-compatible keys:
            {symbol, kind, path, line, end_line, language, module}
        """

    # --- Container Detection ---
    def detect_container(
        self, dir_path: Path, name: str, ctx: CollectorContext
    ) -> dict | None:
        """Detect a container (deployable unit) in the given directory.

        Args:
            dir_path: Directory to check.
            name: Directory name (used as container name).
            ctx: Collector context with utility functions.

        Returns:
            Dict with RawContainer-compatible keys, or None.
            Keys: name, type, technology, root_path, category, metadata, evidence
        """
        return None

    # --- Version Detection ---
    def collect_versions(self, ctx: CollectorContext) -> None:
        """Collect technology versions from build/config files.

        Use ctx.add_version(technology, version, source_file, category) to report.
        Use ctx.find_files(pattern) to locate files.
        """

    # --- Component Collection ---
    def get_component_technologies(self) -> set[str]:
        """Technology strings that route containers to this ecosystem's component collectors."""
        return set()

    def collect_components(
        self, container: dict, repo_path: Path
    ) -> tuple[list, list]:
        """Collect components for a container belonging to this ecosystem.

        Args:
            container: Container dict with 'name', 'root_path', 'technology'.
            repo_path: Repository root path.

        Returns:
            Tuple of (facts, relations).
        """
        return [], []

    # --- Dimension Delegation ---
    def collect_dimension(
        self, dimension: str, repo_path: Path, container_id: str = ""
    ) -> tuple[list, list]:
        """Collect facts for a specific dimension.

        Ecosystems override this to dispatch to specialist collectors.
        Returns (facts, relations). Default: no facts for any dimension.
        """
        return [], []
