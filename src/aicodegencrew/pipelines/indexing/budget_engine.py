"""Budget Engine — Step 2c of the enhanced Discover phase.

Classifies files into priority tiers (A/B/C) and reorders them so that
high-value files are indexed first within the token/chunk budget.

Tiers:
  A (high)  — docs/ADRs, API controllers, root configs, Angular modules
  B (medium) — services, repositories, entities, components, files with 3+ symbols
  C (low)   — tests, utilities, generated code, remaining files

Controlled by env vars:
  INDEX_ENABLE_BUDGET  (default: true)
  INDEX_PRIORITY_A_PCT (default: 40)
  INDEX_PRIORITY_B_PCT (default: 40)
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from ...shared.utils.logger import setup_logger
from .models import SymbolRecord

logger = setup_logger(__name__)

# ── Tier classification rules ───────────────────────────────────────────────

# Path patterns (case-insensitive) → tier
_TIER_A_PATTERNS = [
    re.compile(r"(?i)readme", re.IGNORECASE),
    re.compile(r"(?i)adr[/\\]", re.IGNORECASE),
    re.compile(r"(?i)docs?[/\\]", re.IGNORECASE),
    re.compile(r"(?i)controller", re.IGNORECASE),
    re.compile(r"(?i)resource\.java$", re.IGNORECASE),
    re.compile(r"(?i)\.module\.ts$", re.IGNORECASE),
    re.compile(r"(?i)routing\.module\.ts$", re.IGNORECASE),
    re.compile(r"(?i)app\.config", re.IGNORECASE),
    re.compile(r"(?i)application\.(yml|yaml|properties)$", re.IGNORECASE),
    re.compile(r"(?i)pom\.xml$", re.IGNORECASE),
    re.compile(r"(?i)build\.gradle", re.IGNORECASE),
    re.compile(r"(?i)angular\.json$", re.IGNORECASE),
    re.compile(r"(?i)package\.json$", re.IGNORECASE),
]

_TIER_B_PATTERNS = [
    re.compile(r"(?i)service", re.IGNORECASE),
    re.compile(r"(?i)repository", re.IGNORECASE),
    re.compile(r"(?i)entity", re.IGNORECASE),
    re.compile(r"(?i)model", re.IGNORECASE),
    re.compile(r"(?i)\.component\.ts$", re.IGNORECASE),
    re.compile(r"(?i)\.pipe\.ts$", re.IGNORECASE),
    re.compile(r"(?i)\.directive\.ts$", re.IGNORECASE),
    re.compile(r"(?i)\.guard\.ts$", re.IGNORECASE),
    re.compile(r"(?i)\.interceptor\.", re.IGNORECASE),
]

_TIER_C_PATTERNS = [
    re.compile(r"(?i)test", re.IGNORECASE),
    re.compile(r"(?i)spec\.ts$", re.IGNORECASE),
    re.compile(r"(?i)__tests__", re.IGNORECASE),
    re.compile(r"(?i)generated", re.IGNORECASE),
    re.compile(r"(?i)\.min\.", re.IGNORECASE),
    re.compile(r"(?i)\.d\.ts$", re.IGNORECASE),
    re.compile(r"(?i)polyfills", re.IGNORECASE),
    re.compile(r"(?i)vendor[/\\]", re.IGNORECASE),
]


def is_budget_enabled() -> bool:
    """Check if budget prioritisation is enabled."""
    return os.getenv("INDEX_ENABLE_BUDGET", "true").lower() in ("true", "1", "yes")


class BudgetEngine:
    """Classify and reorder files by priority tier."""

    def __init__(
        self,
        a_pct: int | None = None,
        b_pct: int | None = None,
    ):
        self.a_pct = a_pct if a_pct is not None else int(os.getenv("INDEX_PRIORITY_A_PCT", "40"))
        self.b_pct = b_pct if b_pct is not None else int(os.getenv("INDEX_PRIORITY_B_PCT", "40"))
        # C gets the remainder
        self.c_pct = 100 - self.a_pct - self.b_pct

    def classify(
        self,
        file_path: str,
        symbol_count: int = 0,
    ) -> str:
        """Classify a single file into tier A, B, or C.

        Args:
            file_path: Relative file path.
            symbol_count: Number of symbols extracted from this file.

        Returns:
            "A", "B", or "C".
        """
        # Normalize path for matching
        norm = file_path.replace("\\", "/")

        # Check explicit C-tier first (tests, generated)
        for pat in _TIER_C_PATTERNS:
            if pat.search(norm):
                return "C"

        # Check A-tier (docs, controllers, configs)
        for pat in _TIER_A_PATTERNS:
            if pat.search(norm):
                return "A"

        # Check B-tier (services, entities, components)
        for pat in _TIER_B_PATTERNS:
            if pat.search(norm):
                return "B"

        # Files with 3+ symbols get promoted to B
        if symbol_count >= 3:
            return "B"

        return "C"

    def reorder(
        self,
        file_paths: list[str],
        symbols_by_path: dict[str, list[SymbolRecord]] | None = None,
    ) -> list[str]:
        """Reorder file paths by priority tier (A first, then B, then C).

        Within each tier, original order is preserved (stable sort).

        Args:
            file_paths: List of file paths to reorder.
            symbols_by_path: Optional dict mapping path -> extracted symbols.

        Returns:
            Reordered list of file paths.
        """
        if not is_budget_enabled():
            return file_paths

        symbols_by_path = symbols_by_path or {}

        tiers: dict[str, list[str]] = {"A": [], "B": [], "C": []}

        for fp in file_paths:
            sym_count = len(symbols_by_path.get(fp, []))
            tier = self.classify(fp, sym_count)
            tiers[tier].append(fp)

        total = len(file_paths)
        a_limit = max(1, (total * self.a_pct) // 100)
        b_limit = max(1, (total * self.b_pct) // 100)

        # Take up to limit from each tier; overflow goes into the next tier
        result_a = tiers["A"][:a_limit]
        overflow_a = tiers["A"][a_limit:]

        tier_b_extended = overflow_a + tiers["B"]
        result_b = tier_b_extended[:b_limit]
        overflow_b = tier_b_extended[b_limit:]

        result_c = overflow_b + tiers["C"]

        result = result_a + result_b + result_c

        logger.info(
            f"[Budget] Reordered {total} files: "
            f"A={len(result_a)}, B={len(result_b)}, C={len(result_c)}"
        )

        return result
