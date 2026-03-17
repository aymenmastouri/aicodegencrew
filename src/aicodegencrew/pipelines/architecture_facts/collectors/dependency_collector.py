"""
Dependency Collector - Thin router that delegates to ecosystem specialists.

Detects active ecosystems and dispatches dependency extraction to:
- SpringDependencyCollector (Maven, Gradle)
- AngularDependencyCollector (NPM)
- PythonDependencyCollector (requirements.txt, pyproject.toml)
- CppDependencyCollector (CMake, Conan, vcpkg)

Output: Dependency facts for dependencies dimension
"""

from dataclasses import dataclass

from ....shared.ecosystems.registry import EcosystemRegistry
from .base import CollectorOutput, DimensionCollector, RawFact


@dataclass
class RawDependency(RawFact):
    """A dependency fact (external library/package)."""

    type: str = ""  # maven, npm, python, gradle
    version: str = ""
    scope: str = "compile"  # compile, runtime, test, dev
    group: str = ""  # groupId for Maven


class DependencyCollector(DimensionCollector):
    """
    Thin router that delegates dependency extraction to ecosystem specialists.

    Detects active ecosystems in the repository and dispatches to the
    appropriate specialist collector for each.
    """

    DIMENSION = "dependencies"

    def __init__(self, repo_path):
        super().__init__(repo_path)
        self._registry = EcosystemRegistry()

    def collect(self) -> CollectorOutput:
        """Collect dependency facts by delegating to ecosystem specialists."""
        self._log_start()

        for eco in self._registry.detect(self.repo_path):
            facts, rels = eco.collect_dimension(self.DIMENSION, self.repo_path)
            for f in facts:
                self.output.add_fact(f)
            for r in rels:
                self.output.add_relation(r)

        self._log_end()
        return self.output
