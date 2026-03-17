"""Angular Test Specialist — Extracts TypeScript test facts.

Detects:
- .spec.ts / .e2e-spec.ts files
- describe/it blocks (Jasmine, Jest)
- Playwright test/test.describe blocks
- Test-to-component mapping via file naming convention
"""

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawTestFact


class AngularTestCollector(DimensionCollector):
    """Extracts TypeScript test facts."""

    DIMENSION = "tests"

    SKIP_DIRS = {"node_modules", "dist", "build", "target", ".git", "deployment", "bin", "generated"}

    # TypeScript test patterns
    TS_DESCRIBE_PATTERN = re.compile(r"describe\s*\(\s*['\"]([^'\"]+)['\"]")
    TS_IT_PATTERN = re.compile(r"(?:it|test)\s*\(\s*['\"]([^'\"]+)['\"]")
    PLAYWRIGHT_TEST_PATTERN = re.compile(r"test\s*\(\s*['\"]([^'\"]+)['\"]")
    PLAYWRIGHT_DESCRIBE_PATTERN = re.compile(r"test\.describe\s*\(\s*['\"]([^'\"]+)['\"]")

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect TypeScript test facts (.spec.ts, .e2e-spec.ts)."""
        self._log_start()

        spec_files = self._find_files("*.spec.ts") + self._find_files("*.e2e-spec.ts")

        from .....shared.utils.logger import logger
        logger.info(f"[AngularTestCollector] Scanning {len(spec_files)} TypeScript spec files")

        for spec_file in spec_files:
            try:
                content = spec_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # Determine test type
            file_str = str(spec_file).lower()
            if ".e2e-spec." in file_str or "e2e" in file_str:
                test_type = "e2e"
                framework = "playwright" if "playwright" in content or "@playwright" in content else "protractor"
            else:
                test_type = "unit"
                framework = "jasmine"
                if "jest" in content.lower() or "jest" in file_str:
                    framework = "jest"

            # Describe blocks
            describes = self.TS_DESCRIBE_PATTERN.findall(content)
            playwright_describes = self.PLAYWRIGHT_DESCRIBE_PATTERN.findall(content)

            # It/test blocks
            its = self.TS_IT_PATTERN.findall(content)
            playwright_tests = self.PLAYWRIGHT_TEST_PATTERN.findall(content)

            scenarios = list(set(its + playwright_tests))
            top_describe = (
                describes[0] if describes else (playwright_describes[0] if playwright_describes else spec_file.stem)
            )

            # Guess tested component
            tested_hint = self._guess_component_from_path_ts(spec_file)

            fact = RawTestFact(
                name=top_describe,
                test_type=test_type,
                framework=framework,
                scenarios=scenarios,
                tested_component_hint=tested_hint,
                file_path=self._relative_path(spec_file),
                container_hint="frontend" if test_type != "e2e" else self.container_id,
                metadata={"scenario_count": len(scenarios)},
            )
            fact.add_evidence(
                path=self._relative_path(spec_file),
                line_start=1,
                line_end=min(len(content.split("\n")), 30),
                reason=f"TypeScript test: {top_describe} ({len(scenarios)} tests)",
            )
            self.output.add_fact(fact)

        self._log_end()
        return self.output

    @staticmethod
    def _guess_component_from_path_ts(file_path: Path) -> str:
        """Guess the component under test from file path.

        Uses the original TestCollector logic which strips .e2e-spec, .spec,
        .e2e, Test, IT, Tests, Spec suffixes and leading test- prefix.
        """
        stem = file_path.stem
        # Remove test suffixes
        for suffix in [".e2e-spec", ".spec", ".e2e", "Test", "IT", "Tests", "Spec"]:
            stem = stem.replace(suffix, "")
        # Remove leading test-
        if stem.startswith("test-"):
            stem = stem[5:]
        return stem if stem else ""
