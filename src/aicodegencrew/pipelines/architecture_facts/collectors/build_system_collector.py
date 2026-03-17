"""
BuildSystemCollector - Thin router that delegates to ecosystem specialists.

Each ecosystem provides its own build system specialist:
- SpringBuildSystemCollector: Gradle, Maven
- AngularBuildSystemCollector: npm, Angular
- PythonBuildSystemCollector: pyproject.toml, setup.py, tox
- CppBuildSystemCollector: CMake, Meson

Output -> build_system.json
"""

from dataclasses import dataclass, field
from pathlib import Path

from ....shared.ecosystems.registry import EcosystemRegistry
from .base import CollectorOutput, DimensionCollector, RawFact


@dataclass
class RawBuildFact(RawFact):
    """A build system fact."""

    build_tool: str = ""
    module: str = ""
    module_path: str = ""
    tasks: list[str] = field(default_factory=list)
    source_dirs: list[str] = field(default_factory=list)
    plugins: list[str] = field(default_factory=list)
    wrapper_path: str | None = None
    parent_module: str | None = None
    build_file: str = ""
    properties: dict[str, str] = field(default_factory=dict)


class BuildSystemCollector(DimensionCollector):
    """
    Routes build system collection to ecosystem-specific specialists.

    Detects active ecosystems via EcosystemRegistry, then delegates
    to each ecosystem's build_system dimension handler.
    """

    DIMENSION = "build_system"

    def __init__(self, repo_path: Path):
        super().__init__(repo_path)
        self._registry = EcosystemRegistry()

    def collect(self) -> CollectorOutput:
        """Collect build system facts from all detected ecosystems."""
        self._log_start()
        for eco in self._registry.detect(self.repo_path):
            facts, rels = eco.collect_dimension(self.DIMENSION, self.repo_path)
            for f in facts:
                self.output.add_fact(f)
            for r in rels:
                self.output.add_relation(r)
        self._log_end()
        return self.output
