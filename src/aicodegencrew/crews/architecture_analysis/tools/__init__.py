"""Tools for Architecture Analysis Crew - Phase 2.

CrewAI Best Practice Tools:
- FactsStatisticsTool: Get overview stats for large repos (use FIRST)
- FactsQueryTool: Query architecture facts with filtering and pagination
- RAGQueryTool: ChromaDB semantic search for code context
- StereotypeListTool: Get components by stereotype
- PartialResultsTool: Read partial analysis outputs for synthesis

All tools are designed to DISCOVER architecture (not hardcode).
For 100k+ component repos: Use FactsStatisticsTool first, then paginated queries.
"""

from .facts_query_tool import FactsQueryTool
from .facts_statistics_tool import FactsStatisticsTool
from .partial_results_tool import PartialResultsTool
from .rag_query_tool import RAGQueryTool
from .stereotype_list_tool import StereotypeListTool

__all__ = [
    "FactsQueryTool",
    "FactsStatisticsTool",
    "PartialResultsTool",
    "RAGQueryTool",
    "StereotypeListTool",
]
