"""Service for reading and writing .env configuration."""

from __future__ import annotations

import re
from pathlib import Path

from ..config import settings
from ..schemas import EnvVariable

# Group definitions: (group_name, key_prefixes_or_keys)
_ENV_GROUPS = [
    ("Repository", ["PROJECT_PATH"]),
    ("LLM", ["LLM_", "MODEL", "API_BASE", "OPENAI_API_KEY", "MAX_LLM_"]),
    ("Embeddings", ["OLLAMA_", "EMBED_", "NO_PROXY"]),
    ("Indexing", ["INDEX_", "CHROMA_", "CHUNK_", "MAX_FILE_", "MAX_RAG_"]),
    ("Phase Control", ["SKIP_", "TASK_INPUT_DIR", "REQUIREMENTS_DIR", "LOGS_DIR", "REFERENCE_DIR"]),
    ("Output", ["DOCS_OUTPUT_DIR", "ARC42_LANGUAGE"]),
    ("Logging", ["LOG_LEVEL", "CREWAI_TRACING"]),
]

_REQUIRED_KEYS = {"PROJECT_PATH", "LLM_PROVIDER", "MODEL", "API_BASE"}


def _classify_group(key: str) -> str:
    """Determine the group for a given env key."""
    for group_name, prefixes in _ENV_GROUPS:
        for prefix in prefixes:
            if key == prefix or key.startswith(prefix):
                return group_name
    return "General"


def read_env(path: Path | None = None) -> dict[str, str]:
    """Parse .env file into key-value dict, ignoring comments and blank lines."""
    env_path = path or settings.env_file
    result: dict[str, str] = {}

    if not env_path.exists():
        return result

    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip empty, BOM, comments
            if not line or line.startswith("#") or line.startswith("\ufeff#"):
                continue
            # Remove inline comments (but not # inside values)
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            # Strip inline comment: only if # is preceded by whitespace
            value = re.split(r"\s+#\s", value, maxsplit=1)[0].strip()
            if key:
                result[key] = value

    return result


def _validate_env_entries(values: dict[str, str]) -> None:
    """Reject keys/values that could inject additional env vars."""
    for key, value in values.items():
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            raise ValueError(f"Invalid env key: {key!r}")
        if "\n" in value or "\r" in value or "\x00" in value:
            raise ValueError(f"Env value for {key!r} contains invalid characters")


def write_env(values: dict[str, str], path: Path | None = None) -> None:
    """Update .env file preserving comments and order. Only changes existing keys or appends new ones."""
    _validate_env_entries(values)
    env_path = path or settings.env_file
    lines: list[str] = []

    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            lines = f.readlines()

    applied: set[str] = set()
    result: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in values:
                result.append(f"{key}={values[key]}\n")
                applied.add(key)
                continue
        result.append(line)

    # Append any new keys
    for key, value in values.items():
        if key not in applied:
            result.append(f"{key}={value}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(result)


def get_env_schema() -> list[EnvVariable]:
    """Return variable metadata from .env.example with current values from .env."""
    example_vars = _parse_example_file()
    current_values = read_env()

    variables: list[EnvVariable] = []
    for name, description in example_vars:
        variables.append(
            EnvVariable(
                name=name,
                value=current_values.get(name, ""),
                description=description,
                group=_classify_group(name),
                required=name in _REQUIRED_KEYS,
            )
        )

    return variables


def _parse_example_file() -> list[tuple[str, str]]:
    """Parse .env.example extracting variable names and preceding comments as descriptions."""
    example_path = settings.env_example
    if not example_path.exists():
        # Fallback: return current .env keys with no descriptions
        current = read_env()
        return [(k, "") for k in current]

    variables: list[tuple[str, str]] = []
    pending_comments: list[str] = []

    with open(example_path, encoding="utf-8-sig") as f:
        for line in f:
            stripped = line.strip()

            if not stripped:
                pending_comments = []
                continue

            if stripped.startswith("#"):
                comment = stripped.lstrip("#").strip()
                if comment:
                    pending_comments.append(comment)
                continue

            if "=" in stripped:
                key = stripped.split("=", 1)[0].strip()
                description = " ".join(pending_comments) if pending_comments else ""
                variables.append((key, description))
                pending_comments = []

    return variables
