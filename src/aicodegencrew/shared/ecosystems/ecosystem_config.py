"""
Ecosystem Config — Read/write per-ecosystem enable/disable and priority state.

Persists to config/ecosystems_config.json alongside phases_config.yaml.
All ecosystems are enabled by default with priorities from their code.
"""

from __future__ import annotations

import json
from pathlib import Path


def load_ecosystem_config(config_dir: Path) -> dict[str, dict]:
    """Load ecosystem config from config/ecosystems_config.json.

    Returns a dict mapping eco_id -> {"enabled": bool, "priority": int}.
    Missing ecosystems are not included (defaults come from code).
    """
    config_path = Path(config_dir) / "ecosystems_config.json"

    if not config_path.exists():
        return {}

    try:
        with open(config_path, encoding="utf-8") as f:
            saved = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

    # Validate structure
    result: dict[str, dict] = {}
    for eco_id, entry in saved.items():
        if not isinstance(entry, dict):
            continue
        clean: dict = {}
        if "enabled" in entry and isinstance(entry["enabled"], bool):
            clean["enabled"] = entry["enabled"]
        if "priority" in entry and isinstance(entry["priority"], int):
            clean["priority"] = entry["priority"]
        if clean:
            result[eco_id] = clean

    return result


def save_ecosystem_config(config_dir: Path, config: dict[str, dict]) -> None:
    """Save ecosystem config to config/ecosystems_config.json."""
    config_path = Path(config_dir) / "ecosystems_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def toggle_ecosystem(config_dir: Path, eco_id: str, enabled: bool) -> dict:
    """Toggle a single ecosystem's enabled state, return its updated config entry."""
    config = load_ecosystem_config(config_dir)

    if eco_id not in config:
        config[eco_id] = {}
    config[eco_id]["enabled"] = enabled

    save_ecosystem_config(config_dir, config)
    return config[eco_id]


def update_priority(config_dir: Path, eco_id: str, priority: int) -> dict:
    """Update a single ecosystem's priority, return its updated config entry."""
    config = load_ecosystem_config(config_dir)

    if eco_id not in config:
        config[eco_id] = {}
    config[eco_id]["priority"] = priority

    save_ecosystem_config(config_dir, config)
    return config[eco_id]
