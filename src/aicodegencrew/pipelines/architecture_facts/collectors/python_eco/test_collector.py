"""Python Test Specialist — Extracts Python test facts.

Detects:
- pytest test files (test_*.py, *_test.py)
- conftest.py fixture configuration
- pytest marks as tags
- unittest.TestCase subclasses
- Top-level test functions
"""

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawTestFact


class PythonTestCollector(DimensionCollector):
    """Extracts Python test facts."""

    DIMENSION = "tests"

    SKIP_DIRS = {"node_modules", "dist", "build", "target", ".git", "deployment", "bin", "generated"}

    # Python test patterns
    PYTHON_TEST_FILE_PATTERN = re.compile(r"^test_.*\.py$|.*_test\.py$")
    PYTHON_TEST_CLASS_PATTERN = re.compile(r"class\s+(Test\w+)")
    PYTHON_TEST_FUNCTION_PATTERN = re.compile(r"^(?:    )?def\s+(test_\w+)\s*\(", re.MULTILINE)
    PYTHON_FIXTURE_PATTERN = re.compile(r"@pytest\.fixture")
    PYTHON_MARK_PATTERN = re.compile(r"@pytest\.mark\.(\w+)")
    PYTHON_UNITTEST_PATTERN = re.compile(r"class\s+(\w+)\s*\(\s*(?:unittest\.)?TestCase\s*\)")

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect Python test facts: pytest, unittest."""
        self._log_start()

        py_files = self._find_files("*.py")
        test_files = [f for f in py_files if self.PYTHON_TEST_FILE_PATTERN.match(f.name) or f.name == "conftest.py"]

        if not test_files:
            self._log_end()
            return self.output

        from .....shared.utils.logger import logger
        logger.info(f"[PythonTestCollector] Scanning {len(test_files)} Python test files")

        for test_file in test_files:
            try:
                content = test_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            rel_path = self._relative_path(test_file)

            # conftest.py — fixture configuration files
            if test_file.name == "conftest.py":
                fixtures = self.PYTHON_FIXTURE_PATTERN.findall(content)
                if fixtures:
                    fact = RawTestFact(
                        name=f"conftest:{test_file.parent.name}",
                        test_type="unit",
                        framework="pytest",
                        scenarios=[],
                        tested_component_hint="",
                        file_path=rel_path,
                        container_hint=self.container_id,
                        metadata={"fixture_count": len(fixtures), "kind": "fixture_config"},
                    )
                    fact.add_evidence(path=rel_path, line_start=1, line_end=20, reason=f"pytest conftest ({len(fixtures)} fixtures)")
                    self.output.add_fact(fact)
                continue

            # Detect framework
            framework = "pytest"
            test_type = "unit"
            tags = []

            if self.PYTHON_UNITTEST_PATTERN.search(content):
                framework = "unittest"

            # pytest marks as tags
            tags = list(set(self.PYTHON_MARK_PATTERN.findall(content)))
            if "integration" in tags or "slow" in tags:
                test_type = "integration"

            # Test classes (unittest style or pytest class grouping)
            for class_match in self.PYTHON_TEST_CLASS_PATTERN.finditer(content):
                class_name = class_match.group(1)
                class_line = content[: class_match.start()].count("\n") + 1

                # Find test methods inside this class
                class_start = class_match.end()
                next_class = self.PYTHON_TEST_CLASS_PATTERN.search(content[class_start:])
                class_end = class_start + next_class.start() if next_class else len(content)
                class_body = content[class_start:class_end]

                test_methods = self.PYTHON_TEST_FUNCTION_PATTERN.findall(class_body)
                tested_hint = self._guess_component_from_path(str(test_file))

                fact = RawTestFact(
                    name=class_name,
                    test_type=test_type,
                    framework=framework,
                    scenarios=test_methods,
                    tested_component_hint=tested_hint,
                    file_path=rel_path,
                    container_hint=self.container_id,
                    tags=tags,
                    metadata={"test_method_count": len(test_methods)},
                )
                fact.add_evidence(
                    path=rel_path, line_start=class_line, line_end=class_line + 10,
                    reason=f"Python test class: {class_name} ({len(test_methods)} tests)",
                )
                self.output.add_fact(fact)

            # Unittest TestCase subclasses
            for match in self.PYTHON_UNITTEST_PATTERN.finditer(content):
                class_name = match.group(1)
                # Skip if already found by test class pattern
                if self.PYTHON_TEST_CLASS_PATTERN.match(f"class {class_name}"):
                    continue
                class_line = content[: match.start()].count("\n") + 1
                test_methods = self.PYTHON_TEST_FUNCTION_PATTERN.findall(content[match.end():])

                fact = RawTestFact(
                    name=class_name,
                    test_type=test_type,
                    framework="unittest",
                    scenarios=test_methods[:20],
                    tested_component_hint=self._guess_component_from_path(str(test_file)),
                    file_path=rel_path,
                    container_hint=self.container_id,
                    tags=tags,
                    metadata={"test_method_count": len(test_methods)},
                )
                fact.add_evidence(
                    path=rel_path, line_start=class_line, line_end=class_line + 10,
                    reason=f"unittest TestCase: {class_name} ({len(test_methods)} tests)",
                )
                self.output.add_fact(fact)

            # Top-level test functions (no class)
            top_level_tests = re.findall(r"^def\s+(test_\w+)\s*\(", content, re.MULTILINE)
            if top_level_tests and not self.PYTHON_TEST_CLASS_PATTERN.search(content) and not self.PYTHON_UNITTEST_PATTERN.search(content):
                tested_hint = self._guess_component_from_path(str(test_file))
                fact = RawTestFact(
                    name=test_file.stem,
                    test_type=test_type,
                    framework=framework,
                    scenarios=top_level_tests,
                    tested_component_hint=tested_hint,
                    file_path=rel_path,
                    container_hint=self.container_id,
                    tags=tags,
                    metadata={"test_method_count": len(top_level_tests)},
                )
                fact.add_evidence(
                    path=rel_path, line_start=1, line_end=30,
                    reason=f"Python test file: {test_file.name} ({len(top_level_tests)} tests)",
                )
                self.output.add_fact(fact)

        self._log_end()
        return self.output
