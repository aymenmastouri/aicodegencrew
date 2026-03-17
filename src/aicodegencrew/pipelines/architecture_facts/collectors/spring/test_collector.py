"""Spring Test Specialist — Extracts Java/Kotlin test facts.

Detects:
- JUnit test classes (*Test.java, *IT.java, *Tests.java, *Spec.java)
- @Test methods, @DisplayName annotations
- Framework detection: @SpringBootTest, @DataJpaTest, @WebMvcTest
- Test-to-component mapping via class naming convention
"""

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawTestFact


class SpringTestCollector(DimensionCollector):
    """Extracts Java/Kotlin test facts."""

    DIMENSION = "tests"

    SKIP_DIRS = {"node_modules", "dist", "build", "target", ".git", "deployment", "bin", "generated"}

    # Java test patterns
    JAVA_TEST_CLASS_PATTERN = re.compile(r"class\s+(\w+(?:Test|IT|Tests|Spec))\b")
    JAVA_TEST_METHOD_PATTERN = re.compile(r"@Test\s+.*?(?:public|private|protected)?\s+void\s+(\w+)\s*\(", re.DOTALL)
    JAVA_TEST_ANNOTATION_PATTERN = re.compile(r"@(SpringBootTest|DataJpaTest|WebMvcTest|MockitoExtension|ExtendWith)")
    JAVA_DISPLAY_NAME_PATTERN = re.compile(r'@DisplayName\s*\(\s*"([^"]+)"')

    # Test component hint patterns
    TEST_COMPONENT_HINT = re.compile(r"^(\w+?)(?:Test|IT|Tests|Spec|E2eSpec)$")

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect Java/Kotlin test class facts."""
        self._log_start()

        test_patterns = ["*Test.java", "*IT.java", "*Tests.java", "*Spec.java", "*Test.kt", "*IT.kt"]
        test_files = []
        for pattern in test_patterns:
            test_files.extend(self._find_files(pattern))

        from .....shared.utils.logger import logger
        logger.info(f"[SpringTestCollector] Scanning {len(test_files)} Java/Kotlin test files")

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

        self._log_end()
        return self.output
