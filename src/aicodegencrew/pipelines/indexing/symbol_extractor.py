"""Symbol Extractor — Step 2b of the enhanced Discover phase.

Dispatches to ecosystem-specific extractors for Java, TypeScript, Python, C, and C++.
Symbols: classes, methods, functions, interfaces, endpoints, decorators,
structs, unions, enums, typedefs, macros, namespaces.
"""

from __future__ import annotations

from pathlib import Path

from ...shared.ecosystems import EcosystemRegistry
from ...shared.utils.logger import setup_logger
from .models import SymbolRecord

logger = setup_logger(__name__)

# ── Registry-based language detection ───────────────────────────────────────

_registry = EcosystemRegistry()
EXT_TO_LANG: dict[str, str] = _registry.get_ext_to_lang()


class SymbolExtractor:
    """Extract symbols from source files using ecosystem-specific extractors."""

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

        # Find the ecosystem that handles this extension
        ecosystem = _registry.get_ecosystem_for_extension(ext)
        if ecosystem is None:
            return []

        # Dispatch to ecosystem-specific extractor
        raw_records = ecosystem.extract_symbols(rel_path, content, lines, lang, module)

        # Convert dicts to SymbolRecord objects
        return [
            SymbolRecord(
                symbol=r["symbol"],
                kind=r["kind"],
                path=r["path"],
                line=r["line"],
                end_line=r.get("end_line", 0),
                language=r.get("language", lang),
                module=r.get("module", module),
            )
            for r in raw_records
        ]

    # Keep static helpers available for backward compatibility
    @staticmethod
    def _find_block_end(lines: list[str], start_idx: int) -> int:
        """Find end of a brace-delimited block. Returns 1-based line."""
        from ...shared.ecosystems._utils import find_block_end
        return find_block_end(lines, start_idx)

    @staticmethod
    def _find_python_block_end(lines: list[str], start_idx: int) -> int:
        """Find end of a Python indented block. Returns 1-based line."""
        from ...shared.ecosystems._utils import find_python_block_end
        return find_python_block_end(lines, start_idx)
