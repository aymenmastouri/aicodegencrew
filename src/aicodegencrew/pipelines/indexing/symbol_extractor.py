"""Symbol Extractor — Step 2b of the enhanced Discover phase.

Regex-based MVP that extracts symbols per file for Java, TypeScript, and Python.
Symbols: classes, methods, functions, interfaces, endpoints, decorators.
"""

from __future__ import annotations

import re
from pathlib import Path

from ...shared.utils.logger import setup_logger
from .models import SymbolRecord

logger = setup_logger(__name__)

# ── Language detection ──────────────────────────────────────────────────────

EXT_TO_LANG: dict[str, str] = {
    ".java": "java",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".py": "python",
}


# ── Regex patterns per language ─────────────────────────────────────────────

# Java patterns
_JAVA_CLASS = re.compile(
    r"^\s*(?:public\s+|protected\s+|private\s+)?(?:abstract\s+|final\s+)?(?:class|interface|enum)\s+(\w+)",
    re.MULTILINE,
)
_JAVA_METHOD = re.compile(
    r"^\s*(?:public|protected|private)\s+(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?"
    r"(?:\w+(?:<[^>]+>)?)\s+(\w+)\s*\(",
    re.MULTILINE,
)
_JAVA_ANNOTATION = re.compile(
    r"^\s*@(\w+(?:\.\w+)?)", re.MULTILINE
)
_JAVA_IMPORT = re.compile(
    r"^\s*import\s+(?:static\s+)?([\w.]+);", re.MULTILINE
)

# TypeScript patterns
_TS_CLASS = re.compile(
    r"^\s*(?:export\s+)?(?:abstract\s+)?class\s+(\w+)", re.MULTILINE
)
_TS_INTERFACE = re.compile(
    r"^\s*(?:export\s+)?interface\s+(\w+)", re.MULTILINE
)
_TS_FUNCTION = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.MULTILINE
)
_TS_METHOD = re.compile(
    r"^\s+(?:public|protected|private|readonly|static|async|abstract|\s)*(\w+)\s*\(",
    re.MULTILINE,
)
_TS_DECORATOR = re.compile(
    r"^\s*@(\w+)", re.MULTILINE
)

# Python patterns
_PY_CLASS = re.compile(
    r"^class\s+(\w+)\s*[:\(]", re.MULTILINE
)
_PY_FUNCTION = re.compile(
    r"^(?:    )?def\s+(\w+)\s*\(", re.MULTILINE
)
_PY_METHOD = re.compile(
    r"^    def\s+(\w+)\s*\(", re.MULTILINE
)
_PY_DECORATOR = re.compile(
    r"^(?:    )?@(\w+)", re.MULTILINE
)

# Spring endpoint annotations
_SPRING_ENDPOINTS = re.compile(
    r"@(?:Get|Post|Put|Delete|Patch|Request)Mapping\s*\(\s*(?:value\s*=\s*)?\"([^\"]+)\"",
    re.MULTILINE,
)

# Angular/NestJS decorators of interest
_NG_DECORATORS = {"Component", "Injectable", "NgModule", "Directive", "Pipe", "Controller", "Module"}


class SymbolExtractor:
    """Extract symbols from source files using regex patterns."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path

    def extract_file(self, file_path: str, content: str) -> list[SymbolRecord]:
        """Extract symbols from a single file.

        Args:
            file_path: Relative or absolute file path.
            content: File content string.

        Returns:
            List of SymbolRecord for this file.
        """
        ext = Path(file_path).suffix.lower()
        lang = EXT_TO_LANG.get(ext)
        if not lang:
            return []

        # Compute relative path and module
        try:
            rel_path = str(Path(file_path).relative_to(self.repo_path)).replace("\\", "/")
        except ValueError:
            rel_path = file_path.replace("\\", "/")

        parts = rel_path.split("/")
        module = parts[0] if len(parts) > 1 else ""

        lines = content.splitlines()

        if lang == "java":
            return self._extract_java(rel_path, content, lines, module)
        elif lang in ("typescript", "javascript"):
            return self._extract_typescript(rel_path, content, lines, lang, module)
        elif lang == "python":
            return self._extract_python(rel_path, content, lines, module)

        return []

    def _extract_java(
        self, path: str, content: str, lines: list[str], module: str
    ) -> list[SymbolRecord]:
        records: list[SymbolRecord] = []

        # Classes / interfaces / enums
        for m in _JAVA_CLASS.finditer(content):
            line_no = content[:m.start()].count("\n") + 1
            end_line = self._find_block_end(lines, line_no - 1)
            records.append(SymbolRecord(
                symbol=m.group(1), kind="class", path=path,
                line=line_no, end_line=end_line, language="java", module=module,
            ))

        # Methods
        for m in _JAVA_METHOD.finditer(content):
            name = m.group(1)
            if name in ("if", "for", "while", "switch", "catch", "return"):
                continue
            line_no = content[:m.start()].count("\n") + 1
            end_line = self._find_block_end(lines, line_no - 1)
            records.append(SymbolRecord(
                symbol=name, kind="method", path=path,
                line=line_no, end_line=end_line, language="java", module=module,
            ))

        # Spring endpoints
        for m in _SPRING_ENDPOINTS.finditer(content):
            line_no = content[:m.start()].count("\n") + 1
            records.append(SymbolRecord(
                symbol=m.group(1), kind="endpoint", path=path,
                line=line_no, language="java", module=module,
            ))

        # Key annotations (Spring stereotypes)
        spring_annots = {"RestController", "Controller", "Service", "Repository",
                         "Component", "Configuration", "Entity"}
        for m in _JAVA_ANNOTATION.finditer(content):
            name = m.group(1)
            if name in spring_annots:
                line_no = content[:m.start()].count("\n") + 1
                records.append(SymbolRecord(
                    symbol=f"@{name}", kind="decorator", path=path,
                    line=line_no, language="java", module=module,
                ))

        return records

    def _extract_typescript(
        self, path: str, content: str, lines: list[str], lang: str, module: str
    ) -> list[SymbolRecord]:
        records: list[SymbolRecord] = []

        # Classes
        for m in _TS_CLASS.finditer(content):
            line_no = content[:m.start()].count("\n") + 1
            end_line = self._find_block_end(lines, line_no - 1)
            records.append(SymbolRecord(
                symbol=m.group(1), kind="class", path=path,
                line=line_no, end_line=end_line, language=lang, module=module,
            ))

        # Interfaces
        for m in _TS_INTERFACE.finditer(content):
            line_no = content[:m.start()].count("\n") + 1
            end_line = self._find_block_end(lines, line_no - 1)
            records.append(SymbolRecord(
                symbol=m.group(1), kind="interface", path=path,
                line=line_no, end_line=end_line, language=lang, module=module,
            ))

        # Functions
        for m in _TS_FUNCTION.finditer(content):
            line_no = content[:m.start()].count("\n") + 1
            end_line = self._find_block_end(lines, line_no - 1)
            records.append(SymbolRecord(
                symbol=m.group(1), kind="function", path=path,
                line=line_no, end_line=end_line, language=lang, module=module,
            ))

        # Decorators (Angular/NestJS)
        for m in _TS_DECORATOR.finditer(content):
            name = m.group(1)
            if name in _NG_DECORATORS:
                line_no = content[:m.start()].count("\n") + 1
                records.append(SymbolRecord(
                    symbol=f"@{name}", kind="decorator", path=path,
                    line=line_no, language=lang, module=module,
                ))

        return records

    def _extract_python(
        self, path: str, content: str, lines: list[str], module: str
    ) -> list[SymbolRecord]:
        records: list[SymbolRecord] = []

        # Classes
        for m in _PY_CLASS.finditer(content):
            line_no = content[:m.start()].count("\n") + 1
            end_line = self._find_python_block_end(lines, line_no - 1)
            records.append(SymbolRecord(
                symbol=m.group(1), kind="class", path=path,
                line=line_no, end_line=end_line, language="python", module=module,
            ))

        # Top-level functions (no indent)
        for m in re.finditer(r"^def\s+(\w+)\s*\(", content, re.MULTILINE):
            name = m.group(1)
            line_no = content[:m.start()].count("\n") + 1
            end_line = self._find_python_block_end(lines, line_no - 1)
            records.append(SymbolRecord(
                symbol=name, kind="function", path=path,
                line=line_no, end_line=end_line, language="python", module=module,
            ))

        # Methods (indented def)
        for m in _PY_METHOD.finditer(content):
            name = m.group(1)
            line_no = content[:m.start()].count("\n") + 1
            # Skip if already captured as top-level function
            if any(r.symbol == name and r.line == line_no for r in records):
                continue
            end_line = self._find_python_block_end(lines, line_no - 1)
            records.append(SymbolRecord(
                symbol=name, kind="method", path=path,
                line=line_no, end_line=end_line, language="python", module=module,
            ))

        # Decorators
        for m in _PY_DECORATOR.finditer(content):
            name = m.group(1)
            if name in ("property", "staticmethod", "classmethod", "abstractmethod"):
                continue
            line_no = content[:m.start()].count("\n") + 1
            records.append(SymbolRecord(
                symbol=f"@{name}", kind="decorator", path=path,
                line=line_no, language="python", module=module,
            ))

        return records

    @staticmethod
    def _find_block_end(lines: list[str], start_idx: int) -> int:
        """Find end of a brace-delimited block (Java/TS). Returns 1-based line."""
        depth = 0
        started = False
        for i in range(start_idx, min(start_idx + 500, len(lines))):
            line = lines[i]
            depth += line.count("{") - line.count("}")
            if "{" in line:
                started = True
            if started and depth <= 0:
                return i + 1  # 1-based
        return start_idx + 1

    @staticmethod
    def _find_python_block_end(lines: list[str], start_idx: int) -> int:
        """Find end of a Python indented block. Returns 1-based line."""
        if start_idx >= len(lines):
            return start_idx + 1

        # Find the indentation of the def/class line
        base_line = lines[start_idx]
        base_indent = len(base_line) - len(base_line.lstrip())

        for i in range(start_idx + 1, min(start_idx + 500, len(lines))):
            line = lines[i]
            stripped = line.strip()
            if not stripped:
                continue  # skip blank lines
            indent = len(line) - len(line.lstrip())
            if indent <= base_indent and stripped:
                return i  # 1-based (the line before is the last)

        return len(lines)
