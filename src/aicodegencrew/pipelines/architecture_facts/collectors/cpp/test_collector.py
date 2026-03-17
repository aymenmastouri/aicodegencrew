"""C/C++ Test Specialist — Extracts C/C++ test facts.

Detects:
- GoogleTest: TEST(), TEST_F(), TEST_P()
- Catch2: TEST_CASE()
- doctest: DOCTEST_TEST_CASE()
- CTest: add_test() in CMakeLists.txt
"""

import re
from pathlib import Path

from ..base import CollectorOutput, DimensionCollector, RawTestFact


class CppTestCollector(DimensionCollector):
    """Extracts C/C++ test facts."""

    DIMENSION = "tests"

    SKIP_DIRS = {"node_modules", "dist", "build", "target", ".git", "deployment", "bin", "generated"}

    # C/C++ test patterns
    GTEST_PATTERN = re.compile(r"\b(TEST|TEST_F|TEST_P)\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)")
    CATCH2_PATTERN = re.compile(r'TEST_CASE\s*\(\s*"([^"]+)"')
    CTEST_ADD_TEST = re.compile(r"add_test\s*\(\s*(?:NAME\s+)?(\w+)")
    DOCTEST_PATTERN = re.compile(r'DOCTEST_TEST_CASE\s*\(\s*"([^"]+)"')

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id

    def collect(self) -> CollectorOutput:
        """Collect C/C++ test facts: GoogleTest, Catch2, CTest, doctest."""
        self._log_start()

        cpp_patterns = ["*.cpp", "*.cc", "*.cxx", "*.hpp", "*.h"]
        cpp_files = []
        for pattern in cpp_patterns:
            cpp_files.extend(self._find_files(pattern))

        if cpp_files:
            self._collect_cpp_test_files(cpp_files)

        # CTest: add_test() in CMakeLists.txt
        cmake_files = self._find_files("CMakeLists.txt")
        self._collect_ctest_files(cmake_files)

        self._log_end()
        return self.output

    def _collect_cpp_test_files(self, cpp_files):
        """Scan C/C++ files for test frameworks."""
        for cpp_file in cpp_files:
            try:
                content = cpp_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            rel_path = self._relative_path(cpp_file)

            # GoogleTest: TEST(), TEST_F(), TEST_P()
            gtest_matches = list(self.GTEST_PATTERN.finditer(content))
            if gtest_matches:
                test_suite = cpp_file.stem
                scenarios = [f"{m.group(2)}.{m.group(3)}" for m in gtest_matches]

                fact = RawTestFact(
                    name=test_suite,
                    test_type="unit",
                    framework="googletest",
                    scenarios=scenarios,
                    tested_component_hint=self._guess_component_from_path(str(cpp_file)),
                    file_path=rel_path,
                    container_hint=self.container_id,
                    metadata={"test_count": len(gtest_matches)},
                )
                line_num = content[: gtest_matches[0].start()].count("\n") + 1
                fact.add_evidence(
                    path=rel_path, line_start=line_num, line_end=line_num + 10,
                    reason=f"GoogleTest: {test_suite} ({len(gtest_matches)} tests)",
                )
                self.output.add_fact(fact)
                continue

            # Catch2: TEST_CASE()
            catch2_matches = list(self.CATCH2_PATTERN.finditer(content))
            if catch2_matches:
                test_suite = cpp_file.stem
                scenarios = [m.group(1) for m in catch2_matches]

                fact = RawTestFact(
                    name=test_suite,
                    test_type="unit",
                    framework="catch2",
                    scenarios=scenarios,
                    tested_component_hint=self._guess_component_from_path(str(cpp_file)),
                    file_path=rel_path,
                    container_hint=self.container_id,
                    metadata={"test_count": len(catch2_matches)},
                )
                line_num = content[: catch2_matches[0].start()].count("\n") + 1
                fact.add_evidence(
                    path=rel_path, line_start=line_num, line_end=line_num + 10,
                    reason=f"Catch2: {test_suite} ({len(catch2_matches)} tests)",
                )
                self.output.add_fact(fact)
                continue

            # doctest
            doctest_matches = list(self.DOCTEST_PATTERN.finditer(content))
            if doctest_matches:
                test_suite = cpp_file.stem
                scenarios = [m.group(1) for m in doctest_matches]

                fact = RawTestFact(
                    name=test_suite,
                    test_type="unit",
                    framework="doctest",
                    scenarios=scenarios,
                    tested_component_hint=self._guess_component_from_path(str(cpp_file)),
                    file_path=rel_path,
                    container_hint=self.container_id,
                    metadata={"test_count": len(doctest_matches)},
                )
                line_num = content[: doctest_matches[0].start()].count("\n") + 1
                fact.add_evidence(
                    path=rel_path, line_start=line_num, line_end=line_num + 10,
                    reason=f"doctest: {test_suite} ({len(doctest_matches)} tests)",
                )
                self.output.add_fact(fact)

    def _collect_ctest_files(self, cmake_files):
        """Scan CMakeLists.txt files for CTest add_test() calls."""
        for cmake_file in cmake_files:
            try:
                content = cmake_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            ctest_matches = list(self.CTEST_ADD_TEST.finditer(content))
            if ctest_matches:
                rel_path = self._relative_path(cmake_file)
                scenarios = [m.group(1) for m in ctest_matches]

                fact = RawTestFact(
                    name=f"ctest:{cmake_file.parent.name}",
                    test_type="integration",
                    framework="ctest",
                    scenarios=scenarios,
                    tested_component_hint="",
                    file_path=rel_path,
                    container_hint=self.container_id,
                    metadata={"test_count": len(ctest_matches)},
                )
                line_num = content[: ctest_matches[0].start()].count("\n") + 1
                fact.add_evidence(
                    path=rel_path, line_start=line_num, line_end=line_num + 5,
                    reason=f"CTest: {len(ctest_matches)} test targets",
                )
                self.output.add_fact(fact)
