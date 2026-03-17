"""Shared utility functions used by multiple ecosystem modules.

Extracted from SymbolExtractor static methods so they can be reused
across Java, TypeScript, C/C++, and Python ecosystem modules.
"""

from __future__ import annotations


def find_block_end(lines: list[str], start_idx: int) -> int:
    """Find end of a brace-delimited block (Java/TypeScript/C/C++).

    Returns 1-based line number of the closing brace.
    """
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


def find_python_block_end(lines: list[str], start_idx: int) -> int:
    """Find end of a Python indented block.

    Returns 1-based line number.
    """
    if start_idx >= len(lines):
        return start_idx + 1

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


def count_line(content: str, pos: int) -> int:
    """Return 1-based line number for a character position in content."""
    return content[:pos].count("\n") + 1
