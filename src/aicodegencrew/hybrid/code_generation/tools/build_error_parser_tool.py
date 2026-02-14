"""
Build Error Parser Tool - Parse build output into structured errors.

Reuses all regex patterns, ANSI stripping, and deduplication logic from
Stage 4b (Build Verifier). Supports Gradle/javac, Maven, npm/Angular/TypeScript.
"""

import json
import re
from dataclasses import dataclass

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ....shared.utils.logger import setup_logger
from ....shared.utils.token_budget import truncate_response

logger = setup_logger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns (reused from stage4b_build_verifier.py)
# ---------------------------------------------------------------------------

# Gradle/javac: File.java:42: error: message
# Handles both relative paths and Windows absolute paths (C:\...\File.java)
_JAVAC_PATTERN = re.compile(
    r"^(?P<file>.+?\.java):(?P<line>\d+):\s*error:\s*(?P<msg>.+)$", re.MULTILINE
)

# Angular/TypeScript error patterns
_TSC_PATTERN1 = re.compile(
    r"^(?:Error:\s*|ERROR\s+in\s*|\.\/)?(?P<file>[^\s:]+\.(?:ts|html)):(?P<line>\d+):(?P<col>\d+)\s*-\s*error\s+(?P<code>(?:TS|NG)\d+):\s*(?P<msg>.+)$",
    re.MULTILINE,
)

# TypeScript alternate: file.ts(42,10): error TS2345: message
_TSC_PATTERN2 = re.compile(
    r"^(?:Error:\s*|ERROR\s+in\s*|\.\/)?(?P<file>[^\s(]+\.(?:ts|html))\((?P<line>\d+),(?P<col>\d+)\):\s*error\s+(?P<code>(?:TS|NG)\d+):\s*(?P<msg>.+)$",
    re.MULTILINE,
)

# Maven/javac: [ERROR] /path/File.java:[42,10] error message
_MAVEN_PATTERN = re.compile(
    r"^\[ERROR\]\s*(?P<file>.+?\.java):\[(?P<line>\d+),(?P<col>\d+)\]\s*(?P<msg>.+)$",
    re.MULTILINE,
)

# ANSI escape code stripper
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    """Remove ANSI color/style escape codes from text."""
    return _ANSI_ESCAPE.sub("", text)


@dataclass
class BuildError:
    """A single parsed build error."""

    file_path: str
    line: int = 0
    column: int = 0
    code: str = ""
    message: str = ""


def _parse_build_errors(output: str, build_tool: str) -> list[BuildError]:
    """Parse build output into structured errors based on build tool."""
    output = _strip_ansi(output)
    errors: list[BuildError] = []

    if build_tool in ("gradle", "maven"):
        for m in _JAVAC_PATTERN.finditer(output):
            errors.append(BuildError(
                file_path=m.group("file"),
                line=int(m.group("line")),
                message=m.group("msg").strip(),
            ))
        for m in _MAVEN_PATTERN.finditer(output):
            errors.append(BuildError(
                file_path=m.group("file"),
                line=int(m.group("line")),
                column=int(m.group("col")),
                message=m.group("msg").strip(),
            ))
    elif build_tool in ("npm", "angular"):
        for pattern in (_TSC_PATTERN1, _TSC_PATTERN2):
            for m in pattern.finditer(output):
                errors.append(BuildError(
                    file_path=m.group("file"),
                    line=int(m.group("line")),
                    column=int(m.group("col")),
                    code=m.group("code"),
                    message=m.group("msg").strip(),
                ))

    # Deduplicate
    seen = set()
    unique: list[BuildError] = []
    for e in errors:
        key = (e.file_path, e.line, e.code)
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique


def _auto_detect_tool(build_output: str) -> str:
    """Auto-detect build tool from output content."""
    cleaned = _strip_ansi(build_output)
    if ".java:" in cleaned or "javac" in cleaned.lower():
        return "gradle"
    if "TS" in cleaned and ".ts:" in cleaned:
        return "npm"
    if "NG" in cleaned and (".ts:" in cleaned or ".html:" in cleaned):
        return "npm"
    if "[ERROR]" in cleaned and ".java:" in cleaned:
        return "maven"
    return "gradle"  # fallback


class BuildErrorParserInput(BaseModel):
    """Input schema for BuildErrorParserTool."""

    build_output: str = Field(
        ..., description="Raw build output text to parse for errors"
    )
    build_tool: str = Field(
        default="auto",
        description="Build tool type: 'gradle', 'maven', 'npm', 'angular', or 'auto' for auto-detection",
    )


class BuildErrorParserTool(BaseTool):
    """
    Parse build output into structured error objects.

    Supports Gradle/javac, Maven, and npm/Angular/TypeScript error formats.
    Handles ANSI escape codes and Windows absolute paths.

    Usage Examples:
    1. parse_errors(build_output="...", build_tool="gradle")
    2. parse_errors(build_output="...", build_tool="auto")
    """

    name: str = "parse_build_errors"
    description: str = (
        "Parse raw build output into structured errors with file path, line, column, "
        "error code, and message. Supports Gradle/javac, Maven, npm/Angular/TypeScript. "
        "Use build_tool='auto' to auto-detect the format."
    )
    args_schema: type[BaseModel] = BuildErrorParserInput

    def _run(self, build_output: str, build_tool: str = "auto") -> str:
        """Parse build output and return structured errors."""
        try:
            if not build_output or not build_output.strip():
                return json.dumps({
                    "errors": [],
                    "error_count": 0,
                    "files_affected": [],
                })

            # Auto-detect build tool if needed
            if build_tool == "auto":
                build_tool = _auto_detect_tool(build_output)
                logger.info(f"[BuildErrorParser] Auto-detected build tool: {build_tool}")

            errors = _parse_build_errors(build_output, build_tool)

            # Collect affected files
            files_affected = sorted(set(e.file_path for e in errors))

            # Convert to serializable dicts
            error_dicts = [
                {
                    "file_path": e.file_path,
                    "line": e.line,
                    "column": e.column,
                    "code": e.code,
                    "message": e.message,
                }
                for e in errors
            ]

            result = {
                "build_tool": build_tool,
                "error_count": len(errors),
                "files_affected": files_affected,
                "errors": error_dicts,
            }

            output = json.dumps(result, ensure_ascii=False)
            return truncate_response(output, hint="some errors may be truncated")

        except Exception as e:
            logger.error(f"BuildErrorParserTool error: {e}")
            return json.dumps({"error": str(e), "errors": [], "error_count": 0})
