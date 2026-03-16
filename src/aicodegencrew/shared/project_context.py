"""Project context — multi-project discover isolation.

Manages per-project subfolders under ``knowledge/discover/{slug}/``
so that multiple target repositories can be indexed side by side.

Public API:
    derive_project_slug(repo_path)        -> "uvz"
    get_active_project_slug()             -> "uvz" | None
    set_active_project(slug, repo_path)   -> None
    get_discover_dir(project_slug=None)   -> "knowledge/discover/uvz"
    migrate_legacy_to_subfolder(repo_path)-> slug
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from .utils.logger import setup_logger

logger = setup_logger(__name__)

# The .active_project marker lives directly inside knowledge/discover/
_DISCOVER_BASE = Path("knowledge/discover")
_ACTIVE_PROJECT_FILE = _DISCOVER_BASE / ".active_project"

# Files that belong to a discover subfolder (legacy flat layout)
_DISCOVER_ARTIFACTS = (
    "symbols.jsonl",
    "evidence.jsonl",
    "repo_manifest.json",
    ".indexing_state.json",
    ".zero_chunk_hashes.json",
)

# Legacy ChromaDB internal files/dirs (sqlite + uuid-named dirs)
# Kept for migration of old installations.
_CHROMA_INTERNALS = (
    "chroma.sqlite3",
)


# ── Slug derivation ─────────────────────────────────────────────────────────


def derive_project_slug(repo_path: str | Path) -> str:
    """Derive a filesystem-safe slug from a repository path.

    Inside Docker the repo is mounted at a generic path like ``/project``.
    To keep per-project isolation, ``PROJECT_PATH_HOST`` carries the
    original host path so the slug reflects the real repo name.

    >>> derive_project_slug("C:\\\\uvz")
    'uvz'
    >>> derive_project_slug("/home/user/my-app")
    'my-app'
    """
    import os

    resolved = Path(repo_path).resolve()
    # Inside Docker the mount point is /project or /repo — use host path instead
    if resolved.name in ("project", "repo"):
        host_path = os.getenv("PROJECT_PATH_HOST", "")
        if host_path:
            resolved = Path(host_path)

    name = resolved.name
    # lowercase, keep alphanumeric + hyphen + underscore
    slug = re.sub(r"[^a-z0-9_-]", "", name.lower())
    return slug or "default"


def derive_branch_slug(repo_path: str | Path) -> str:
    """Detect the current git branch and return a slug-safe version.

    Returns "unknown" if not a git repo or git is unavailable.

    >>> derive_branch_slug("C:\\\\uvz")  # on master
    'master'
    >>> derive_branch_slug("C:\\\\uvz")  # on feature/auth-service
    'feature-auth-service'
    """
    import subprocess

    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            # Slugify: replace / with -, lowercase, keep safe chars
            slug = re.sub(r"[^a-z0-9_-]", "-", branch.lower()).strip("-")
            return slug or "unknown"
    except Exception:
        pass
    return "unknown"


def derive_collection_name(repo_path: str | Path) -> str:
    """Derive a Qdrant/ChromaDB collection name scoped to repo (+ branch if git).

    Format:
    - Git repo:     repo_docs_{repo_slug}_{branch_slug}
    - Non-git dir:  repo_docs_{repo_slug}

    This ensures multi-user/multi-branch isolation:
    - User A on uvz@master    → repo_docs_uvz_master
    - User B on uvz@feature-x → repo_docs_uvz_feature-x
    - User C on other-app@main → repo_docs_other-app_main
    - Plain folder /data/docs  → repo_docs_docs

    Qdrant collection names: max 255 chars, alphanumeric + _ + -.
    """
    repo_slug = derive_project_slug(repo_path)
    branch_slug = derive_branch_slug(repo_path)
    if branch_slug == "unknown":
        return f"repo_docs_{repo_slug}"
    return f"repo_docs_{repo_slug}_{branch_slug}"


# ── Active project ───────────────────────────────────────────────────────────


def get_active_project() -> dict[str, str] | None:
    """Read ``.active_project`` marker. Returns ``{"slug": ..., "repo_path": ...}`` or None."""
    if not _ACTIVE_PROJECT_FILE.exists():
        return None
    try:
        data = json.loads(_ACTIVE_PROJECT_FILE.read_text(encoding="utf-8"))
        if data.get("slug"):
            return data
    except Exception:
        pass
    return None


def get_active_project_slug() -> str | None:
    """Return the slug of the currently active project, or None."""
    info = get_active_project()
    return info["slug"] if info else None


def set_active_project(slug: str, repo_path: str | Path = "") -> None:
    """Write ``.active_project`` marker."""
    _DISCOVER_BASE.mkdir(parents=True, exist_ok=True)
    data = {"slug": slug, "repo_path": str(repo_path)}
    _ACTIVE_PROJECT_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("[ProjectContext] Active project set to '%s'", slug)


# ── Discover directory resolution ────────────────────────────────────────────


def get_discover_dir(project_slug: str | None = None) -> str:
    """Return the discover subfolder for *project_slug*.

    Resolution order:
    1. Explicit ``project_slug`` argument  -> ``knowledge/discover/{slug}``
    2. ``.active_project`` marker          -> ``knowledge/discover/{slug}``
    3. Single existing subfolder           -> that subfolder
    4. Legacy flat layout                  -> ``knowledge/discover`` (backward compat)
    """
    if project_slug:
        return str(_DISCOVER_BASE / project_slug)

    # Try .active_project
    active = get_active_project_slug()
    if active:
        return str(_DISCOVER_BASE / active)

    # Single subfolder heuristic
    slug = _detect_single_subfolder()
    if slug:
        return str(_DISCOVER_BASE / slug)

    # Legacy fallback
    return str(_DISCOVER_BASE)


def _detect_single_subfolder() -> str | None:
    """If exactly one project subfolder exists, return its name."""
    if not _DISCOVER_BASE.exists():
        return None
    subdirs = [
        d.name for d in _DISCOVER_BASE.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ]
    if len(subdirs) == 1:
        return subdirs[0]
    return None


# ── Legacy migration ─────────────────────────────────────────────────────────


def migrate_legacy_to_subfolder(repo_path: str | Path) -> str:
    """Move flat discover artifacts into a project subfolder.

    Called once on first index after upgrade.  If the flat layout has any
    discover artifacts (symbols.jsonl, etc.) they are moved
    into ``knowledge/discover/{slug}/``.

    Returns the slug.
    """
    slug = derive_project_slug(repo_path)
    target = _DISCOVER_BASE / slug

    if target.exists():
        logger.debug("[Migration] Subfolder '%s' already exists — skipping", slug)
        set_active_project(slug, repo_path)
        return slug

    # Check if there are legacy flat artifacts to migrate
    has_legacy = any(
        (_DISCOVER_BASE / name).exists()
        for name in (*_DISCOVER_ARTIFACTS, *_CHROMA_INTERNALS)
    )
    if not has_legacy:
        logger.debug("[Migration] No legacy artifacts found — nothing to migrate")
        return slug

    logger.info("[Migration] Moving legacy discover artifacts to subfolder '%s'", slug)
    target.mkdir(parents=True, exist_ok=True)

    # Move artifact files
    for name in _DISCOVER_ARTIFACTS:
        src = _DISCOVER_BASE / name
        if src.exists():
            dst = target / name
            shutil.move(str(src), str(dst))
            logger.debug("[Migration] Moved %s -> %s", src, dst)

    # Move legacy ChromaDB sqlite + internal UUID dirs (if any remain)
    for item in _DISCOVER_BASE.iterdir():
        if item.name.startswith("."):
            continue
        if item == target:
            continue
        # Skip other project subfolders
        if item.is_dir() and (item / ".indexing_state.json").exists():
            continue
        # Legacy ChromaDB files: chroma.sqlite3, uuid-named dirs
        if item.name in _CHROMA_INTERNALS or _is_chroma_internal_dir(item):
            dst = target / item.name
            shutil.move(str(item), str(dst))
            logger.debug("[Migration] Moved %s -> %s", item, dst)

    set_active_project(slug, repo_path)
    logger.info("[Migration] Legacy migration complete -> %s", target)
    return slug


def _is_chroma_internal_dir(path: Path) -> bool:
    """Detect legacy ChromaDB internal UUID-named directories."""
    if not path.is_dir():
        return False
    # ChromaDB creates dirs with UUID-like names (hex, 36 chars with dashes)
    name = path.name
    if len(name) == 36 and name.count("-") == 4:
        return True
    return False
