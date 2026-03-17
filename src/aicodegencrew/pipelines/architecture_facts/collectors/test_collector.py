"""
TestCollector - Extracts test facts from unit, integration, and E2E tests.

Thin router that delegates ecosystem-specific collection to specialist
collectors via the EcosystemRegistry.

Cross-cutting (language-agnostic) collection:
- Cucumber/Gherkin .feature files

Delegated to ecosystems:
- Java: SpringTestCollector (JUnit, @SpringBootTest)
- TypeScript: AngularTestCollector (Jasmine, Jest, Playwright)
- Python: PythonTestCollector (pytest, unittest)
- C/C++: CppTestCollector (GoogleTest, Catch2, doctest, CTest)

Output -> tests dimension
"""

import re
from pathlib import Path

from ....shared.ecosystems.registry import EcosystemRegistry
from ....shared.utils.logger import logger
from .base import CollectorOutput, DimensionCollector, RawTestFact


class TestCollector(DimensionCollector):
    """Collects test facts from all test types in the project.

    Thin router: runs cross-cutting feature file collection, then
    delegates to ecosystem specialists via EcosystemRegistry.
    """

    DIMENSION = "tests"

    SKIP_DIRS = {"node_modules", "dist", "build", "target", ".git", "deployment", "bin", "generated"}

    # Cucumber/Gherkin patterns (cross-cutting, language-agnostic)
    FEATURE_PATTERN = re.compile(r"^Feature:\s*(.+)", re.MULTILINE)
    SCENARIO_PATTERN = re.compile(r"^\s*(?:Scenario|Scenario Outline|Szenario|Szenariovorlage):\s*(.+)", re.MULTILINE)
    GHERKIN_TAG_PATTERN = re.compile(r"@(\w+)")

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id
        self._registry = EcosystemRegistry()

    def collect(self) -> CollectorOutput:
        """Collect all test facts."""
        self._log_start()

        # Cross-cutting: Cucumber/Gherkin .feature files
        self._collect_feature_files()

        # Delegate to ecosystem specialists
        for eco in self._registry.detect(self.repo_path):
            facts, rels = eco.collect_dimension(self.DIMENSION, self.repo_path, self.container_id)
            for f in facts:
                self.output.add_fact(f)
            for r in rels:
                self.output.add_relation(r)

        self._log_end()
        return self.output

    # =========================================================================
    # Cucumber / Gherkin (cross-cutting)
    # =========================================================================

    def _collect_feature_files(self):
        """Collect Cucumber/Gherkin .feature files."""
        feature_files = self._find_files("*.feature")

        logger.info(f"[TestCollector] Scanning {len(feature_files)} .feature files")

        for feature_file in feature_files:
            try:
                content = feature_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # Feature name
            feature_match = self.FEATURE_PATTERN.search(content)
            feature_name = feature_match.group(1).strip() if feature_match else feature_file.stem

            # Scenarios
            scenarios = [m.group(1).strip() for m in self.SCENARIO_PATTERN.finditer(content)]

            # Tags (file-level and scenario-level)
            tags = list(set(self.GHERKIN_TAG_PATTERN.findall(content)))

            # Guess tested component from file path or feature name
            tested_hint = self._guess_component_from_path(feature_file)

            fact = RawTestFact(
                name=feature_name,
                test_type="e2e",
                framework="cucumber",
                scenarios=scenarios,
                tested_component_hint=tested_hint,
                file_path=self._relative_path(feature_file),
                container_hint=self.container_id,
                tags=tags,
                metadata={"scenario_count": len(scenarios)},
            )
            fact.add_evidence(
                path=self._relative_path(feature_file),
                line_start=1,
                line_end=min(len(content.split("\n")), 50),
                reason=f"Cucumber feature: {feature_name} ({len(scenarios)} scenarios)",
            )
            self.output.add_fact(fact)

    # =========================================================================
    # Helpers
    # =========================================================================

    def _guess_component_from_path(self, file_path: Path) -> str:
        """Guess the component under test from file path."""
        stem = file_path.stem
        # Remove test suffixes
        for suffix in [".e2e-spec", ".spec", ".e2e", "Test", "IT", "Tests", "Spec"]:
            stem = stem.replace(suffix, "")
        # Remove leading test-
        if stem.startswith("test-"):
            stem = stem[5:]
        return stem if stem else ""

    def _should_skip(self, path: Path) -> bool:
        """Check if path should be skipped (path-component matching, not substring)."""
        return bool(set(p.lower() for p in path.parts) & self.SKIP_DIRS)

    def _relative_path(self, file_path: Path) -> str:
        try:
            return str(file_path.relative_to(self.repo_path))
        except ValueError:
            return str(file_path)
