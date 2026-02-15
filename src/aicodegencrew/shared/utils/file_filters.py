"""File filtering and pattern matching utilities - FAST VERSION.

Uses os.walk() instead of pathlib for speed.
Blocklist-based: indexes all text files, excludes known binary/generated extensions.
Dynamically reads .gitignore rules for exclusion.
"""

import fnmatch
import os
import re
from pathlib import Path, PurePosixPath

# Binary/generated extensions to EXCLUDE (blocklist approach).
# Everything else is treated as text and indexed.
BINARY_EXTENSIONS = {
    # Compiled / bytecode
    ".class", ".jar", ".war", ".ear", ".pyc", ".pyo",
    ".o", ".obj", ".a", ".lib", ".so", ".dll", ".dylib", ".exe",
    # Archives
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar", ".xz",
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp", ".tiff",
    # Media
    ".mp3", ".mp4", ".avi", ".mov", ".wav", ".flac", ".ogg", ".webm",
    # Fonts
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    # Documents (binary)
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    # Data (binary/large)
    ".db", ".sqlite", ".sqlite3", ".mdb",
    # Lock files (auto-generated, often huge)
    ".lock",
    # Source maps (generated)
    ".map",
    # Minified bundles (generated, not useful for RAG)
    ".min.js", ".min.css",
}

CONFIG_EXTENSIONS = {
    ".yml",
    ".yaml",
    ".json",
    ".xml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".properties",
    ".gradle",
}

# Directories to skip (faster than pattern matching)
# Only skip build outputs, dependencies, cache - NOT source code!
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "target",
    ".idea",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".gradle",
    ".maven",
    "coverage",
    "test-results",
    "reports",
    ".next",
    ".nuxt",
    ".vscode",
    ".continue",
    ".cache",
    ".chroma",
    ".chroma_db",
    "vendor",
    "packages",
    "site-packages",
    ".eggs",
    "eggs",
    ".renv",
    ".env",
    "cypress",
    ".angular",
    "out",
    ".tox",
    "htmlcov",
    ".m2",
    "bin",
    "generated",
    "_generated",
    "deployment",
    "html",
}

# Special files to always include
SPECIAL_FILES = {
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "chart.yaml",
    "pom.xml",
    "angular.json",
    "tsconfig.json",
    "package.json",
    "setup.py",
    "requirements.txt",
    ".gitignore",
    "makefile",
    "gradle.properties",
}

DEFAULT_SKIP_FILE_PATTERNS = [
    "**/*.min.js",
    "**/*.map",
    "**/*.class",
    "**/*.jar",
    "**/*.war",
    "**/*.zip",
    "**/*.exe",
    "**/*.dll",
    "**/*.so",
    "**/*.png",
    "**/*.jpg",
    "**/*.jpeg",
    "**/*.gif",
    "**/*.pdf",
]

DEFAULT_KEEP_GLOBS = [
    "README*",
    "docs/**",
    "adr/**",
    "architecture/**",
    "**/src/**",
    "package.json",
    "pom.xml",
    "build.gradle*",
    "Dockerfile*",
    "docker-compose*.yml",
    "docker-compose*.yaml",
    "helm/**",
    "k8s/**",
    "**/*.yml",
    "**/*.yaml",
]

# Defaults used by tests and callers that rely on glob patterns.
# Blocklist: include everything, exclude skip-dirs + binary extensions.
DEFAULT_INCLUDE_PATTERNS = ["**/*"]
DEFAULT_EXCLUDE_PATTERNS = (
    [f"**/{d}/**" for d in sorted(SKIP_DIRS)]
    + [f"*{ext}" for ext in sorted(BINARY_EXTENSIONS)]
)


def _env_csv_set(name: str) -> set[str]:
    """Read a comma-separated env var into a normalized lowercase set."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return set()
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _env_csv_list(name: str) -> list[str]:
    """Read a comma-separated env var preserving order and case."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _match_path(path_posix: str, pattern: str) -> bool:
    """Match with glob semantics supporting ** for directories."""
    try:
        if PurePosixPath(path_posix).match(pattern):
            return True
    except Exception:
        pass

    # Fallbacks for common ** patterns and simple substring contains
    if fnmatch.fnmatch(path_posix, pattern) or fnmatch.fnmatch(os.path.basename(path_posix), pattern):
        return True

    if "**" in pattern:
        core = pattern.replace("**/", "").replace("/**", "").strip("/")
        if core and f"/{core}/" in f"/{path_posix}/":
            return True

    return False


def _get_skip_dirs() -> set[str]:
    """Return skip dirs, optionally extended via env.

    Env:
      - INDEX_EXTRA_SKIP_DIRS: comma-separated list (e.g. "docs,dist,out")
      - SKIP_DIRS: comma-separated list (supports names or globs)
    """
    extra = _env_csv_set("INDEX_EXTRA_SKIP_DIRS")
    skip_dirs_env = _env_csv_list("SKIP_DIRS")

    normalized_env: set[str] = set()
    for token in skip_dirs_env:
        t = token.strip().lower().replace("\\", "/")
        t = t.removeprefix("**/").removesuffix("/**").strip("/")
        if not t or any(ch in t for ch in "*?[]"):
            continue
        if "/" in t:
            t = t.split("/")[-1]
        normalized_env.add(t)

    return {d.lower() for d in SKIP_DIRS} | extra | normalized_env


def _get_skip_file_patterns() -> list[str]:
    """Return skip-file glob patterns from env or defaults.

    Env:
      - SKIP_FILES: comma-separated glob list
    """
    from_env = _env_csv_list("SKIP_FILES")
    return from_env if from_env else DEFAULT_SKIP_FILE_PATTERNS


def _get_keep_globs() -> list[str]:
    """Return keep-globs allowlist.

    Env:
      - KEEP_GLOBS: comma-separated glob list
    """
    keep_env = _env_csv_list("KEEP_GLOBS")
    return keep_env if keep_env else DEFAULT_KEEP_GLOBS


def _is_config_file(file_path: Path) -> bool:
    if file_path.name.lower() in SPECIAL_FILES:
        return True
    return file_path.suffix.lower() in CONFIG_EXTENSIONS


def _looks_like_test_path(file_path: Path) -> bool:
    parts_lower = [part.lower() for part in file_path.parts]
    if {"test", "tests", "__tests__", "test-results"} & set(parts_lower):
        return True

    path_posix = file_path.as_posix().lower()
    if "/src/test/" in path_posix or "/src/tests/" in path_posix:
        return True

    return bool(re.search(r"(^|[._-])(test|tests|spec)([._-]|$)", file_path.stem.lower()))


def should_include_file(
    file_path: Path,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> bool:
    """Return True if a file should be indexed.

    Blocklist approach:
    - Exclude any file under known skip directories (e.g. node_modules, .git)
    - If include/exclude patterns are provided, apply them using fnmatch
    - Otherwise, exclude files with BINARY_EXTENSIONS; include everything else
    """
    # 1) Directory-based skip (case-insensitive on Windows)
    skip_dirs = _get_skip_dirs()
    parts_lower = [p.lower() for p in file_path.parts]
    if any(part in skip_dirs for part in parts_lower):
        return False

    # Optional mode switches
    if not _env_flag("ENABLE_TEST_INDEX", True) and _looks_like_test_path(file_path):
        return False
    if not _env_flag("ENABLE_CONFIG_PARSER", True) and _is_config_file(file_path):
        return False

    # Normalize path for glob matching
    path_posix = file_path.as_posix()

    # 2) Skip-file patterns + optional excludes
    effective_excludes = list(DEFAULT_EXCLUDE_PATTERNS)
    effective_excludes.extend(_get_skip_file_patterns())
    if exclude_patterns:
        effective_excludes.extend(exclude_patterns)
    for pat in effective_excludes:
        if _match_path(path_posix, pat) or _match_path(file_path.name, pat):
            return False

    # 3) Allowlist
    if include_patterns is not None:
        include_match = any(_match_path(path_posix, pat) or _match_path(file_path.name, pat) for pat in include_patterns)
        return include_match
    else:
        keep_patterns = _get_keep_globs()
        if keep_patterns:
            if not any(_match_path(path_posix, pat) or _match_path(file_path.name, pat) for pat in keep_patterns):
                return False

    # 4) Extension/special-file rules (blocklist: exclude known binary)
    file_name = file_path.name.lower()
    if file_name in SPECIAL_FILES:
        return True

    return file_path.suffix.lower() not in BINARY_EXTENSIONS


def _load_gitignore_patterns(root_path: Path) -> set[str]:
    """Load patterns from .gitignore file if exists.

    Returns set of patterns to exclude (directories and files).
    """
    gitignore_path = root_path / ".gitignore"
    patterns = set()

    if not gitignore_path.exists():
        return patterns

    try:
        with open(gitignore_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue
                # Remove leading slash
                if line.startswith("/"):
                    line = line[1:]
                # Remove trailing slash for directories
                if line.endswith("/"):
                    line = line[:-1]
                patterns.add(line)
    except Exception:
        pass  # Silently ignore gitignore read errors

    return patterns


def _should_skip_by_gitignore(path_str: str, gitignore_patterns: set[str]) -> bool:
    """Check if path matches any gitignore pattern."""
    if not gitignore_patterns:
        return False

    # Get just the directory/file name
    name = os.path.basename(path_str)

    # Check exact matches and wildcard patterns
    for pattern in gitignore_patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
        # Also check full relative path for patterns with /
        if "/" in pattern and fnmatch.fnmatch(path_str, pattern):
            return True

    return False


def collect_files(
    root_path: Path,
    include_patterns: list[str] = None,
    exclude_patterns: list[str] = None,
    max_depth: int = None,
) -> list[Path]:
    """Fast file collection using os.walk() instead of pathlib recursion.

    Blocklist-based: indexes all text files, excludes BINARY_EXTENSIONS blocklist.
    Skips binary/cache directories. Reads .gitignore and applies exclusion rules.

    Args:
        root_path: Root directory to scan
        include_patterns: Optional include globs (overrides default allowlist)
        exclude_patterns: Optional extra exclude globs
        max_depth: Maximum directory depth (None for unlimited)

    Returns:
        List of matching file paths
    """
    if not root_path.exists():
        return []

    # Load .gitignore patterns dynamically
    gitignore_patterns = _load_gitignore_patterns(root_path)
    skip_dirs = _get_skip_dirs()

    collected: list[Path] = []
    root_str = str(root_path)

    # Use os.walk for speed (avoids pathlib.relative_to() overhead)
    for dirpath, dirnames, filenames in os.walk(root_str, topdown=True, onerror=None):
        # Track depth
        depth = dirpath[len(root_str) :].count(os.sep)
        if max_depth is not None and depth > max_depth:
            dirnames.clear()  # Don't descend further
            continue

        # Get relative path for gitignore matching
        rel_path = dirpath[len(root_str) :].lstrip(os.sep)

        # Prune directories in-place (modifying dirnames stops walk from descending)
        # Check both SKIP_DIRS and gitignore patterns
        filtered_dirs = []
        for d in dirnames:
            if d.lower() in skip_dirs:
                continue
            # Check gitignore patterns
            dir_rel = os.path.join(rel_path, d) if rel_path else d
            if _should_skip_by_gitignore(dir_rel, gitignore_patterns):
                continue
            filtered_dirs.append(d)
        dirnames[:] = filtered_dirs

        # Check files
        for filename in filenames:
            filepath = Path(dirpath) / filename

            # Check extension/special files first
            if not should_include_file(filepath):
                continue

            # Check gitignore patterns
            file_rel = os.path.join(rel_path, filename) if rel_path else filename
            if _should_skip_by_gitignore(file_rel, gitignore_patterns):
                continue

            collected.append(filepath)

    return sorted(collected)
