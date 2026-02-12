"""
Collector Config — Read/write per-collector enable/disable state.

Persists to config/collectors_config.json alongside phases_config.yaml.
All collectors are enabled by default.
"""

from __future__ import annotations

import json
from pathlib import Path

from .registry import COLLECTOR_REGISTRY, get_disableable_ids


def _default_config() -> dict[str, bool]:
    """Return default config: all collectors enabled."""
    return {c["id"]: True for c in COLLECTOR_REGISTRY}


def load_collector_config(config_dir: Path) -> dict[str, bool]:
    """Load enable/disable state from config/collectors_config.json.

    Returns a dict mapping collector_id -> enabled (bool).
    Missing collectors default to True (enabled).
    """
    config_path = Path(config_dir) / "collectors_config.json"
    defaults = _default_config()

    if not config_path.exists():
        return defaults

    try:
        with open(config_path, encoding="utf-8") as f:
            saved = json.load(f)
    except (json.JSONDecodeError, OSError):
        return defaults

    # Merge saved values into defaults (only for known collector IDs)
    for cid, enabled in saved.items():
        if cid in defaults and isinstance(enabled, bool):
            defaults[cid] = enabled

    return defaults


def save_collector_config(config_dir: Path, config: dict[str, bool]) -> None:
    """Save enable/disable state to config/collectors_config.json.

    Only saves disableable collectors (core collectors are always enabled).
    """
    config_path = Path(config_dir) / "collectors_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Only persist disableable IDs
    disableable = set(get_disableable_ids())
    to_save = {cid: enabled for cid, enabled in config.items() if cid in disableable}

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(to_save, f, indent=2, ensure_ascii=False)


def toggle_collector(config_dir: Path, collector_id: str, enabled: bool) -> dict[str, bool]:
    """Toggle a single collector and return updated config.

    Raises ValueError if collector_id is not disableable.
    """
    disableable = set(get_disableable_ids())
    if collector_id not in disableable:
        raise ValueError(f"Collector '{collector_id}' cannot be disabled")

    config = load_collector_config(config_dir)
    config[collector_id] = enabled
    save_collector_config(config_dir, config)
    return config
