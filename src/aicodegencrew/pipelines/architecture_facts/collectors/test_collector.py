"""
TestCollector - Extracts test facts from unit, integration, and E2E tests.

Detects:
1. .feature files: Cucumber/Gherkin scenarios, tags (@smoke, @regression)
2. *Test.java / *IT.java: JUnit test classes, @Test methods, @SpringBootTest
3. .spec.ts / .e2e-spec.ts: Playwright/Jasmine tests, describe/it blocks
4. Test -> Component mapping (e.g. LoginControllerTest -> LoginController)

Output -> tests dimension
"""

import re
from pathlib import Path

from ....shared.utils.logger import logger
from .base import CollectorOutput, DimensionCollector, RawTestFact


class TestCollector(DimensionCollector):
    """Collects test facts from all test types in the project."""

    DIMENSION = "tests"

    SKIP_DIRS = {"node_modules", "dist", "build", "target", ".git", "deployment", "bin", "generated"}

    # Cucumber/Gherkin patterns
    FEATURE_PATTERN = re.compile(r"^Feature:\s*(.+)", re.MULTILINE)
    SCENARIO_PATTERN = re.compile(r"^\s*(?:Scenario|Scenario Outline|Szenario|Szenariovorlage):\s*(.+)", re.MULTILINE)
    GHERKIN_TAG_PATTERN = re.compile(r"@(\w+)")

    # Java test patterns
    JAVA_TEST_CLASS_PATTERN = re.compile(r"class\s+(\w+(?:Test|IT|Tests|Spec))\b")
    JAVA_TEST_METHOD_PATTERN = re.compile(r"@Test\s+.*?(?:public|private|protected)?\s+void\s+(\w+)\s*\(", re.DOTALL)
    JAVA_TEST_ANNOTATION_PATTERN = re.compile(r"@(SpringBootTest|DataJpaTest|WebMvcTest|MockitoExtension|ExtendWith)")
    JAVA_DISPLAY_NAME_PATTERN = re.compile(r'@DisplayName\s*\(\s*"([^"]+)"')

    # TypeScript test patterns
    TS_DESCRIBE_PATTERN = re.compile(r"describe\s*\(\s*['\"]([^'\"]+)['\"]")
    TS_IT_PATTERN = re.compile(r"(?:it|test)\s*\(\s*['\"]([^'\"]+)['\"]")
    PLAYWRIGHT_TEST_PATTERN = re.compile(r"test\s*\(\s*['\"]([^'\"]+)['\"]")
    PLAYWRIGHT_DESCRIBE_PATTERN = re.compile(r"test\.describe\s*\(\s*['\"]([^'\"]+)['\"]")

    # Test component hint patterns
    TEST_COMPONENT_HINT = re.compile(r"^(\w+?)(?:Test|IT|Tests|Spec|E2eSpec)$")

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect all test facts."""
        self._log_start()

        # 1. Cucumber .feature files
        self._collect_feature_files()

        # 2. Java test files
        self._collect_java_tests()

        # 3. TypeScript test files (.spec.ts, .e2e-spec.ts)
        self._collect_typescript_tests()

        self._log_end()
        return self.output

    # =========================================================================
    # Cucumber / Gherkin
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
    # Java Tests
    # =========================================================================

    def _collect_java_tests(self):
        """Collect Java/Kotlin test class facts."""
        test_patterns = ["*Test.java", "*IT.java", "*Tests.java", "*Spec.java", "*Test.kt", "*IT.kt"]
        test_files = []
        for pattern in test_patterns:
            test_files.extend(self._find_files(pattern))

        logger.info(f"[TestCollector] Scanning {len(test_files)} Java/Kotlin test files")

        for test_file in test_files:
            try:
                content = test_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # Class name
            class_match = self.JAVA_TEST_CLASS_PATTERN.search(content)
            class_name = class_match.group(1) if class_match else test_file.stem

            # Test methods
            test_methods = self.JAVA_TEST_METHOD_PATTERN.findall(content)

            # Display names
            display_names = self.JAVA_DISPLAY_NAME_PATTERN.findall(content)

            # Framework detection
            framework = "junit"
            annotations = self.JAVA_TEST_ANNOTATION_PATTERN.findall(content)
            test_type = "unit"

            if "SpringBootTest" in annotations:
                framework = "spring_boot_test"
                test_type = "integration"
            elif "DataJpaTest" in annotations:
                framework = "data_jpa_test"
                test_type = "integration"
            elif "WebMvcTest" in annotations:
                framework = "web_mvc_test"
                test_type = "integration"

            if class_name.endswith("IT"):
                test_type = "integration"

            # Guess tested component
            hint_match = self.TEST_COMPONENT_HINT.match(class_name)
            tested_hint = hint_match.group(1) if hint_match else ""

            scenarios = display_names if display_names else test_methods

            fact = RawTestFact(
                name=class_name,
                test_type=test_type,
                framework=framework,
                scenarios=scenarios,
                tested_component_hint=tested_hint,
                file_path=self._relative_path(test_file),
                container_hint=self.container_id,
                tags=annotations,
                metadata={"test_method_count": len(test_methods)},
            )

            line_num = content[: class_match.start()].count("\n") + 1 if class_match else 1
            fact.add_evidence(
                path=self._relative_path(test_file),
                line_start=line_num,
                line_end=line_num + 20,
                reason=f"Java test class: {class_name} ({len(test_methods)} tests)",
            )
            self.output.add_fact(fact)

    # =========================================================================
    # TypeScript Tests
    # =========================================================================

    def _collect_typescript_tests(self):
        """Collect TypeScript test files (.spec.ts, .e2e-spec.ts)."""
        spec_files = self._find_files("*.spec.ts") + self._find_files("*.e2e-spec.ts")

        logger.info(f"[TestCollector] Scanning {len(spec_files)} TypeScript spec files")

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
            tested_hint = self._guess_component_from_path(spec_file)

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
        path_str = str(path).lower()
        return any(skip_dir in path_str for skip_dir in self.SKIP_DIRS)

    def _relative_path(self, file_path: Path) -> str:
        try:
            return str(file_path.relative_to(self.repo_path))
        except ValueError:
            return str(file_path)
