"""Symbol Query Tool — deterministic lookup into the symbol index.

Lazy-loads `knowledge/discover/symbols.jsonl` and supports:
- Exact name match
- Substring / contains search
- Filter by kind, path, module
- Graceful degradation (returns empty if file missing)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, ClassVar

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class SymbolQueryInput(BaseModel):
    """Input schema for SymbolQueryTool."""

    query: str = Field(
        ...,
        description="Symbol name to search for (e.g. 'AuthService', 'handleLogin')",
    )
    kind: str = Field(
        default="",
        description="Filter by kind: class, method, function, interface, endpoint, decorator",
    )
    path_filter: str = Field(
        default="",
        description="Filter by file path substring (e.g. 'auth/', 'Service.java')",
    )
    module_filter: str = Field(
        default="",
        description="Filter by module name (e.g. 'backend', 'frontend')",
    )
    exact: bool = Field(
        default=False,
        description="If true, match symbol name exactly; otherwise substring match",
    )
    limit: int = Field(
        default=20,
        description="Maximum results to return",
    )


class SymbolQueryTool(BaseTool):
    """Query the extracted symbol index (symbols.jsonl) for deterministic lookups.

    Use this to find exact classes, methods, endpoints, etc. without relying
    on semantic/vector search.

    Examples:
        symbol_query(query="AuthService")
        symbol_query(query="@RestController", kind="decorator")
        symbol_query(query="login", kind="method", module_filter="backend")
    """

    name: str = "symbol_query"
    description: str = (
        "Deterministic lookup in the symbol index. "
        "Find classes, methods, endpoints, interfaces by name. "
        "Much faster and more precise than semantic search for known symbol names."
    )
    args_schema: type[BaseModel] = SymbolQueryInput

    # Internal cache
    _symbols: list[dict[str, Any]] | None = None
    _symbols_path: Path | None = None

    # Standard locations (ClassVar = not a Pydantic field)
    SYMBOLS_PATHS: ClassVar[list[str]] = [
        "knowledge/discover/symbols.jsonl",
    ]

    def _load_symbols(self) -> list[dict[str, Any]]:
        """Lazy-load symbols from JSONL file."""
        if self._symbols is not None:
            return self._symbols

        # Find symbols file
        # Try from project root (__file__ -> src/aicodegencrew/shared/tools/)
        base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent

        symbols_path = None
        for rel in self.SYMBOLS_PATHS:
            candidate = base_dir / rel
            if candidate.exists():
                symbols_path = candidate
                break

        if not symbols_path:
            logger.debug("[SymbolQuery] symbols.jsonl not found — returning empty")
            self._symbols = []
            return self._symbols

        # Parse JSONL
        records = []
        try:
            with open(symbols_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
            logger.info(f"[SymbolQuery] Loaded {len(records)} symbols from {symbols_path}")
        except Exception as e:
            logger.warning(f"[SymbolQuery] Failed to load symbols: {e}")
            records = []

        self._symbols = records
        self._symbols_path = symbols_path
        return self._symbols

    def _run(
        self,
        query: str,
        kind: str = "",
        path_filter: str = "",
        module_filter: str = "",
        exact: bool = False,
        limit: int = 20,
    ) -> str:
        """Execute symbol lookup.

        Returns:
            JSON string with matching symbols.
        """
        symbols = self._load_symbols()

        if not symbols:
            return json.dumps({
                "query": query,
                "result_count": 0,
                "results": [],
                "note": "Symbol index not available. Run Phase 0 (discover) first.",
            })

        query_lower = query.lower()
        results = []

        for sym in symbols:
            sym_name = sym.get("symbol", "")

            # Name match
            if exact:
                if sym_name != query:
                    continue
            else:
                if query_lower not in sym_name.lower():
                    continue

            # Kind filter
            if kind and sym.get("kind", "") != kind:
                continue

            # Path filter
            if path_filter and path_filter.lower() not in sym.get("path", "").lower():
                continue

            # Module filter
            if module_filter and module_filter.lower() not in sym.get("module", "").lower():
                continue

            results.append(sym)

            if len(results) >= limit:
                break

        output = {
            "query": query,
            "filters": {
                "kind": kind or "(any)",
                "path": path_filter or "(any)",
                "module": module_filter or "(any)",
                "exact": exact,
            },
            "result_count": len(results),
            "results": results,
        }

        return json.dumps(output, indent=2, ensure_ascii=False)
