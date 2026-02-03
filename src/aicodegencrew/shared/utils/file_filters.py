"""File filtering and pattern matching utilities - FAST VERSION.

Uses os.walk() instead of pathlib for speed.
Only indexes code/documentation files based on RAG config.
Dynamically reads .gitignore rules for exclusion.
"""

import os
from pathlib import Path
from typing import List, Set, Optional
import fnmatch


# Global code & doc extensions (like Continue plugin RAG config)
# ALL production code - batch embeddings make this fast!
# SQL excluded - too large
INDEXABLE_EXTENSIONS = {
    ".py", ".java", ".kt", ".xml", ".properties", ".yml", ".yaml",
    ".md", ".ts", ".tsx", ".html", ".scss", ".css", ".json",
    ".gradle", ".toml", ".js", ".jsx", ".go", ".rs", ".cs",
    ".cpp", ".c", ".h", ".hpp", ".sh", ".bash"
}

# Directories to skip (faster than pattern matching)
# Only skip build outputs, dependencies, cache - NOT source code!
SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "dist", "build", "target",
    ".idea", "__pycache__", ".pytest_cache", ".mypy_cache", ".gradle",
    ".maven", "coverage", "test-results", "reports", ".next", ".nuxt",
    ".vscode", ".continue", ".cache", ".chroma", ".chroma_db", "vendor",
    "packages", "site-packages", ".eggs", "eggs", ".renv", ".env",
    "cypress", ".angular", "out", ".tox", "htmlcov", ".m2"
}

# Special files to always include
SPECIAL_FILES = {
    "dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "chart.yaml", "pom.xml", "angular.json", "tsconfig.json",
    "package.json", "setup.py", "requirements.txt", ".gitignore",
    "makefile", "gradle.properties"
}

# Backwards-compatible defaults used by tests and callers that rely on glob patterns.
# Note: the current implementation is extension-driven for speed, but we still expose
# these pattern lists and accept overrides in `should_include_file`.
DEFAULT_INCLUDE_PATTERNS = [f"**/*{ext}" for ext in sorted(INDEXABLE_EXTENSIONS)]
DEFAULT_EXCLUDE_PATTERNS = (
    [f"**/{d}/**" for d in sorted(SKIP_DIRS)]
    + ["**/*.class", "**/*.jar", "**/*.war", "**/*.zip", "**/*.exe", "**/*.dll", "**/*.so"]
)


def _env_csv_set(name: str) -> Set[str]:
    """Read a comma-separated env var into a normalized lowercase set."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return set()
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _get_indexable_extensions() -> Set[str]:
    """Return indexable extensions, optionally overridden via env.

    Env:
      - INDEX_EXTENSIONS: comma-separated list (e.g. ".py,.java,.md")
    """
    override = _env_csv_set("INDEX_EXTENSIONS")
    if override:
        # Normalize: ensure leading dot for extensions
        normalized = set()
        for ext in override:
            normalized.add(ext if ext.startswith(".") else f".{ext}")
        return normalized
    return INDEXABLE_EXTENSIONS


def _get_skip_dirs() -> Set[str]:
    """Return skip dirs, optionally extended via env.

    Env:
      - INDEX_EXTRA_SKIP_DIRS: comma-separated list (e.g. "docs,dist,out")
    """
    extra = _env_csv_set("INDEX_EXTRA_SKIP_DIRS")
    return {d.lower() for d in SKIP_DIRS} | extra


def should_include_file(
    file_path: Path,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
) -> bool:
    """Return True if a file should be indexed.

    Fast path:
    - Exclude any file under known skip directories (e.g. node_modules, .git)
    - If include/exclude patterns are provided, apply them using fnmatch
    - Otherwise, fall back to extension/special-file rules (env-overridable)
    """
    # 1) Directory-based skip (case-insensitive on Windows)
    skip_dirs = _get_skip_dirs()
    parts_lower = [p.lower() for p in file_path.parts]
    if any(part in skip_dirs for part in parts_lower):
        return False

    # Normalize path for glob matching
    path_posix = file_path.as_posix()

    # 2) Optional pattern-based filtering (used by tests + power users)
    effective_excludes = exclude_patterns or DEFAULT_EXCLUDE_PATTERNS
    for pat in effective_excludes:
        if fnmatch.fnmatch(path_posix, pat) or fnmatch.fnmatch(file_path.name, pat):
            return False

    if include_patterns is not None:
        return any(
            fnmatch.fnmatch(path_posix, pat) or fnmatch.fnmatch(file_path.name, pat)
            for pat in include_patterns
        )

    # 3) Extension/special-file rules (fast, env-overridable)
    file_name = file_path.name.lower()
    if file_name in SPECIAL_FILES:
        return True

    return file_path.suffix.lower() in _get_indexable_extensions()


def _load_gitignore_patterns(root_path: Path) -> Set[str]:
    """Load patterns from .gitignore file if exists.
    
    Returns set of patterns to exclude (directories and files).
    """
    gitignore_path = root_path / ".gitignore"
    patterns = set()
    
    if not gitignore_path.exists():
        return patterns
    
    try:
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                # Remove leading slash
                if line.startswith('/'):
                    line = line[1:]
                # Remove trailing slash for directories
                if line.endswith('/'):
                    line = line[:-1]
                patterns.add(line)
    except Exception:
        pass  # Silently ignore gitignore read errors
    
    return patterns


def _should_skip_by_gitignore(path_str: str, gitignore_patterns: Set[str]) -> bool:
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
        if '/' in pattern and fnmatch.fnmatch(path_str, pattern):
            return True
    
    return False


def collect_files(
    root_path: Path,
    include_patterns: List[str] = None,
    exclude_patterns: List[str] = None,
    max_depth: int = None,
) -> List[Path]:
    """Fast file collection using os.walk() instead of pathlib recursion.
    
    Indexes only code/doc files (like Continue plugin), skips all
    binary/cache/node_modules directories.
    ALSO reads .gitignore and applies those exclusion rules dynamically.
    
    Based on RAG config: generic, no backend/frontend split.
    
    Args:
        root_path: Root directory to scan
        include_patterns: Ignored (uses INDEXABLE_EXTENSIONS)
        exclude_patterns: Ignored (uses SKIP_DIRS + .gitignore)
        max_depth: Maximum directory depth (None for unlimited)
        
    Returns:
        List of matching file paths
    """
    if not root_path.exists():
        return []
    
    # Load .gitignore patterns dynamically
    gitignore_patterns = _load_gitignore_patterns(root_path)
    skip_dirs = _get_skip_dirs()
    
    collected: List[Path] = []
    root_str = str(root_path)
    
    # Use os.walk for speed (avoids pathlib.relative_to() overhead)
    for dirpath, dirnames, filenames in os.walk(root_str, topdown=True, onerror=None):
        # Track depth
        depth = dirpath[len(root_str):].count(os.sep)
        if max_depth is not None and depth > max_depth:
            dirnames.clear()  # Don't descend further
            continue
        
        # Get relative path for gitignore matching
        rel_path = dirpath[len(root_str):].lstrip(os.sep)
        
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

