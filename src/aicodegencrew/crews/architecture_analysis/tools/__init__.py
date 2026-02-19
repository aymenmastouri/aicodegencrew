"""Tools for Architecture Analysis Crew - Phase 2.

CrewAI Best Practice Tools:
- FactsStatisticsTool: Get overview stats for large repos (use FIRST)
- FactsQueryTool: Query architecture facts with filtering and pagination (from shared)
- RAGQueryTool: ChromaDB semantic search for code context (from shared)
- SymbolQueryTool: Deterministic exact/substring lookup in symbols.jsonl (from shared)
- StereotypeListTool: Get components by stereotype
- PartialResultsTool: Read partial analysis outputs for synthesis

All tools are designed to DISCOVER architecture (not hardcode).
For 100k+ component repos: Use FactsStatisticsTool first, then paginated queries.
"""

from ....shared.tools import FactsQueryTool, RAGQueryTool, SymbolQueryTool
from .facts_statistics_tool import FactsStatisticsTool
from .partial_results_tool import PartialResultsTool
from .stereotype_list_tool import StereotypeListTool

__all__ = [
    "FactsQueryTool",
    "FactsStatisticsTool",
    "PartialResultsTool",
    "RAGQueryTool",
    "StereotypeListTool",
    "SymbolQueryTool",
]
