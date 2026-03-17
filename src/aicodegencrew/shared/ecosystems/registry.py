"""EcosystemRegistry — Detects active ecosystems and provides aggregated queries.

Singleton that registers all built-in ecosystems, detects which ones
are present in a repository, and provides merged extension/marker data.
Supports config-driven enable/disable and priority overrides, plus
plugin discovery from plugins/ecosystems/.
"""

from __future__ import annotations

import importlib.util
import inspect
import logging
import os
from pathlib import Path

from .base import EcosystemDefinition, MarkerFile
from .ecosystem_config import load_ecosystem_config

logger = logging.getLogger(__name__)


class EcosystemRegistry:
    """Registry for all known ecosystems.

    Usage:
        registry = EcosystemRegistry()
        active = registry.detect(repo_path)
        ext_to_lang = registry.get_ext_to_lang(active)
    """

    def __init__(self):
        self._ecosystems: list[EcosystemDefinition] = []
        self._disabled_ids: set[str] = set()
        self._priority_overrides: dict[str, int] = {}
        self._register_builtins()
        self._discover_plugins()
        self._load_config()

    def _register_builtins(self):
        """Import and register all built-in ecosystem modules."""
        from .c_cpp import CCppEcosystem
        from .java_jvm import JavaJvmEcosystem
        from .javascript_typescript import JavaScriptTypeScriptEcosystem
        from .python_ecosystem import PythonEcosystem

        self._ecosystems = [
            JavaJvmEcosystem(),
            JavaScriptTypeScriptEcosystem(),
            CCppEcosystem(),
            PythonEcosystem(),
        ]

    def _load_config(self):
        """Load ecosystem config and apply enable/disable + priority overrides."""
        config_dir = Path(os.getenv("AICODEGENCREW_ROOT", ".")) / "config"
        config = load_ecosystem_config(config_dir)
        for eco_id, entry in config.items():
            if not entry.get("enabled", True):
                self._disabled_ids.add(eco_id)
            if "priority" in entry:
                self._priority_overrides[eco_id] = entry["priority"]

    def _discover_plugins(self):
        """Discover and register plugin ecosystems from plugins/ecosystems/."""
        plugins_dir = Path(os.getenv("AICODEGENCREW_ROOT", ".")) / "plugins" / "ecosystems"
        if not plugins_dir.is_dir():
            return

        known_ids = {eco.id for eco in self._ecosystems}

        for child in sorted(plugins_dir.iterdir()):
            if not child.is_dir() or child.name.startswith(("_", ".")):
                continue

            init_file = child / "__init__.py"
            if not init_file.exists():
                continue

            try:
                spec = importlib.util.spec_from_file_location(
                    f"aicodegencrew_plugin_eco_{child.name}", str(init_file)
                )
                if spec is None or spec.loader is None:
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for _name, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(obj, EcosystemDefinition)
                        and obj is not EcosystemDefinition
                        and not inspect.isabstract(obj)
                    ):
                        instance = obj()
                        if instance.id not in known_ids:
                            self._ecosystems.append(instance)
                            known_ids.add(instance.id)
                            logger.info("Loaded plugin ecosystem: %s (%s)", instance.name, instance.id)

            except Exception:
                logger.warning("Failed to load plugin ecosystem from %s", child, exc_info=True)

    def register(self, eco: EcosystemDefinition) -> None:
        """Register an ecosystem at runtime (for plugins or testing)."""
        known_ids = {e.id for e in self._ecosystems}
        if eco.id not in known_ids:
            self._ecosystems.append(eco)

    def _effective_priority(self, eco: EcosystemDefinition) -> int:
        """Get priority with config override applied."""
        return self._priority_overrides.get(eco.id, eco.priority)

    @property
    def all_ecosystems(self) -> list[EcosystemDefinition]:
        """All registered ecosystems, sorted by effective priority."""
        return sorted(self._ecosystems, key=self._effective_priority)

    def detect(self, repo_path: Path) -> list[EcosystemDefinition]:
        """Detect which ecosystems are present in the repository.

        Returns list of active EcosystemDefinitions, sorted by effective priority.
        Disabled ecosystems are excluded.
        """
        active = [
            eco for eco in self._ecosystems
            if eco.id not in self._disabled_ids and eco.detect(repo_path)
        ]
        return sorted(active, key=self._effective_priority)

    def is_disabled(self, eco_id: str) -> bool:
        """Check if an ecosystem is disabled via config."""
        return eco_id in self._disabled_ids

    def get_priority_override(self, eco_id: str) -> int | None:
        """Get the config priority override for an ecosystem, or None."""
        return self._priority_overrides.get(eco_id)

    # ── Aggregation Queries ─────────────────────────────────────────────────

    def get_ext_to_lang(self, active_only: list[EcosystemDefinition] | None = None) -> dict[str, str]:
        """Merged extension-to-language mapping."""
        result = {}
        for eco in (active_only or self._ecosystems):
            result.update(eco.ext_to_lang)
        return result

    def get_all_source_extensions(self, active_only: list[EcosystemDefinition] | None = None) -> set[str]:
        """Union of all source extensions."""
        result: set[str] = set()
        for eco in (active_only or self._ecosystems):
            result |= eco.source_extensions
        return result

    def get_all_exclude_extensions(self, active_only: list[EcosystemDefinition] | None = None) -> set[str]:
        """Union of all exclude extensions."""
        result: set[str] = set()
        for eco in (active_only or self._ecosystems):
            result |= eco.exclude_extensions
        return result

    def get_all_skip_directories(self, active_only: list[EcosystemDefinition] | None = None) -> set[str]:
        """Union of all skip directories."""
        result: set[str] = set()
        for eco in (active_only or self._ecosystems):
            result |= eco.skip_directories
        return result

    def get_framework_markers(self, active_only: list[EcosystemDefinition] | None = None) -> dict[str, str]:
        """Merged marker file to framework label mapping."""
        result = {}
        for eco in (active_only or self._ecosystems):
            for marker in eco.marker_files:
                result[marker.filename] = marker.framework_label
        return result

    def get_ecosystem_for_extension(self, ext: str) -> EcosystemDefinition | None:
        """Find the ecosystem that handles a given file extension."""
        for eco in self._ecosystems:
            if ext in eco.source_extensions or ext in eco.ext_to_lang:
                return eco
        return None

    def get_ecosystem_for_technology(self, technology: str) -> EcosystemDefinition | None:
        """Find the ecosystem that handles a given technology string.

        First tries exact match, then prefix match to handle compound
        technology strings like 'C++/CMake (Qt, Boost)'.
        """
        # Exact match first
        for eco in self._ecosystems:
            if technology in eco.get_component_technologies():
                return eco
        # Prefix match fallback for compound technology strings
        for eco in self._ecosystems:
            for known_tech in eco.get_component_technologies():
                if technology.startswith(known_tech):
                    return eco
        return None

    def get_ecosystems_by_priority(self) -> list[EcosystemDefinition]:
        """All ecosystems sorted by container detection priority (lowest first)."""
        return sorted(self._ecosystems, key=self._effective_priority)
