"""
Test Writer Tool - Write test files to the shared staging area.

Shares the staging dict with CodeWriterTool so all generated files
(source + tests) are collected together by the orchestrator.
Validates that test files contain at least one test assertion.
"""

import json
import re
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ....shared.utils.logger import setup_logger
from ....shared.utils.token_budget import truncate_response
from .code_reader_tool import EXT_TO_LANG
from .code_writer_tool import StagingDict

logger = setup_logger(__name__)

# Patterns that indicate test content
_TEST_MARKERS = [
    re.compile(r"@Test\b"),  # JUnit
    re.compile(r"@ParameterizedTest\b"),  # JUnit 5
    re.compile(r"\bit\s*\("),  # Jasmine/Jest/Mocha
    re.compile(r"\bdescribe\s*\("),  # Jasmine/Jest/Mocha
    re.compile(r"\btest\s*\("),  # Jest
    re.compile(r"\bexpect\s*\("),  # Jest/Jasmine assertions
    re.compile(r"assert\w*\s*\("),  # JUnit/TestNG assertions
    re.compile(r"@SpringBootTest\b"),  # Spring Boot test
    re.compile(r"@WebMvcTest\b"),  # Spring MVC test
    re.compile(r"@DataJpaTest\b"),  # Spring Data JPA test
    re.compile(r"TestBed\.configureTestingModule"),  # Angular TestBed
]

# Common test directory patterns
_TEST_PATH_PATTERNS = [
    "src/test/",
    "src/main/test/",
    "__tests__/",
    ".spec.ts",
    ".spec.js",
    ".test.ts",
    ".test.js",
    "Test.java",
    "Tests.java",
    "IT.java",  # Integration test suffix
]


class TestWriterInput(BaseModel):
    """Input schema for TestWriterTool."""

    file_path: str = Field(..., description="Target test file path (absolute or repo-relative)")
    content: str = Field(..., description="Complete test file content")
    tested_component: str = Field(
        default="",
        description="Name of the component being tested (for traceability)",
    )


class TestWriterTool(BaseTool):
    """
    Write test files to the shared staging area.

    Validates that the content contains at least one test marker
    (@Test, it(, describe(, etc.) and that the path follows test conventions.
    Shares the staging dict with CodeWriterTool.

    Usage Examples:
    1. write_test(file_path="src/test/.../FooServiceTest.java", content="...", tested_component="FooService")
    2. write_test(file_path="src/app/foo/foo.component.spec.ts", content="...", tested_component="FooComponent")
    """

    name: str = "write_test"
    description: str = (
        "Write a test file to the staging area. "
        "Validates test content (must contain @Test, it(, describe(, etc.). "
        "Provide the complete test file content and the name of the tested component."
    )
    args_schema: type[BaseModel] = TestWriterInput

    # Configuration
    repo_path: str = ""

    # Shared staging dict (same instance as CodeWriterTool)
    _staging: StagingDict = {}

    def __init__(self, repo_path: str = "", staging: StagingDict | None = None, **kwargs):
        """Initialize with repo path and shared staging dict."""
        super().__init__(**kwargs)
        if repo_path:
            self.repo_path = repo_path
        self._staging = staging if staging is not None else {}

    @property
    def staging(self) -> StagingDict:
        """Access the staging dict."""
        return self._staging

    def _run(
        self,
        file_path: str,
        content: str,
        tested_component: str = "",
    ) -> str:
        """Stage a test file for writing."""
        try:
            # Validate inputs
            if not file_path or not file_path.strip():
                return json.dumps({"error": "file_path cannot be empty"})

            if not content or not content.strip():
                return json.dumps({"error": "content cannot be empty"})

            file_path = file_path.strip()

            # Validate test content
            validation = self._validate_test(file_path, content)

            # Detect language
            ext = Path(file_path).suffix.lower()
            language = EXT_TO_LANG.get(ext, "other")

            # Stage the file
            self._staging[file_path] = {
                "content": content,
                "action": "create",
                "original_content": "",
                "language": language,
                "is_test": True,
                "tested_component": tested_component,
            }

            result = {
                "status": "staged",
                "file_path": file_path,
                "language": language,
                "tested_component": tested_component,
                "size_chars": len(content),
                "total_staged_files": len(self._staging),
                "validation": validation,
            }

            output = json.dumps(result, ensure_ascii=False)
            return truncate_response(output)

        except Exception as e:
            logger.error(f"TestWriterTool error: {e}")
            return json.dumps({"error": str(e), "file_path": file_path})

    @staticmethod
    def _validate_test(file_path: str, content: str) -> dict:
        """Validate that the content looks like a test file."""
        warnings = []

        # Check for test markers
        has_test_marker = any(pattern.search(content) for pattern in _TEST_MARKERS)
        if not has_test_marker:
            warnings.append("No test markers found (@Test, it(, describe(, test(, expect()")

        # Check path follows test conventions
        is_test_path = any(pattern in file_path for pattern in _TEST_PATH_PATTERNS)
        if not is_test_path:
            warnings.append(
                f"Path doesn't follow test conventions (expected .spec.ts, .test.ts, "
                f"Test.java, or src/test/ directory): {file_path}"
            )

        return {
            "has_test_markers": has_test_marker,
            "is_test_path": is_test_path,
            "valid": has_test_marker,  # test markers are required
            "warnings": warnings,
        }
