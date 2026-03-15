"""DataCollector — deterministic data gathering for chapter generation.

Collects facts, RAG results, and component lists based on a ChapterRecipe.
No LLM calls, no agents — pure Python data collection.
"""

import json
import logging
from pathlib import Path
from typing import Any

from .data_recipes import ChapterRecipe

logger = logging.getLogger(__name__)


class DataCollector:
    """Collects all data needed for a chapter from facts, RAG, and component tools."""

    def __init__(
        self,
        facts_path: str | Path = "knowledge/extract/architecture_facts.json",
        analyzed_path: str | Path = "knowledge/analyze/analyzed_architecture.json",
        chroma_dir: str | None = None,
    ):
        self._facts: dict[str, Any] = {}
        self._analyzed: dict[str, Any] = {}
        self._facts_path = Path(facts_path)
        self._analyzed_path = Path(analyzed_path)
        self._chroma_dir = chroma_dir
        self._dimension_cache: dict[str, Any] = {}

    def load(self) -> None:
        """Load base facts and analyzed data from disk."""
        if self._facts_path.exists():
            self._facts = json.loads(self._facts_path.read_text(encoding="utf-8"))
            logger.info("[DataCollector] Loaded facts: %d keys", len(self._facts))

        if self._analyzed_path.exists():
            self._analyzed = json.loads(self._analyzed_path.read_text(encoding="utf-8"))
            logger.info("[DataCollector] Loaded analyzed: %d keys", len(self._analyzed))

    def collect(self, recipe: ChapterRecipe) -> dict[str, Any]:
        """Collect all data needed for a chapter based on its recipe.

        Returns a dict with:
        - facts: dict of category → data
        - rag_results: list of RAG search results
        - components: dict of stereotype → component list
        - analyzed: analyzed architecture data
        - system_summary: pre-computed system summary string
        """
        data: dict[str, Any] = {
            "facts": {},
            "rag_results": [],
            "components": {},
            "analyzed": self._analyzed,
            "system_summary": self._build_system_summary(),
        }

        # 1. Collect facts by category
        for category, params in recipe.facts:
            fact_data = self._query_facts(category, **params)
            data["facts"][category] = fact_data

        # 2. Collect RAG results
        for query in recipe.rag_queries:
            results = self._rag_query(query)
            data["rag_results"].append({"query": query, "results": results})

        # 3. Collect components by stereotype
        for stereotype in recipe.components:
            components = self._list_components(stereotype)
            data["components"][stereotype] = components

        logger.info(
            "[DataCollector] %s: %d fact categories, %d RAG queries, %d stereotypes",
            recipe.id,
            len(data["facts"]),
            len(data["rag_results"]),
            len(data["components"]),
        )

        return data

    def _query_facts(self, category: str, **params) -> Any:
        """Query architecture facts by category."""
        if category == "all":
            return self._get_system_overview()

        # Load dimension files lazily
        dimension_map = {
            "containers": "containers",
            "components": "components",
            "interfaces": "interfaces",
            "relations": "relations",
            "data_model": "data_model",
        }

        dim_key = dimension_map.get(category, category)
        if dim_key in self._dimension_cache:
            return self._dimension_cache[dim_key]

        # Try dimension file first
        dim_path = self._facts_path.parent / f"{dim_key}.json"
        if dim_path.exists():
            data = json.loads(dim_path.read_text(encoding="utf-8"))
            self._dimension_cache[dim_key] = data
            return data

        # Fallback to main facts file
        data = self._facts.get(dim_key, self._facts.get(category, {}))
        self._dimension_cache[dim_key] = data
        return data

    def _get_system_overview(self) -> dict[str, Any]:
        """Build system overview from facts."""
        overview: dict[str, Any] = {}

        # Component counts
        components = self._facts.get("components", [])
        if isinstance(components, list):
            overview["total_components"] = len(components)
            stereotypes: dict[str, int] = {}
            for comp in components:
                if isinstance(comp, dict):
                    st = comp.get("stereotype", "unknown")
                    stereotypes[st] = stereotypes.get(st, 0) + 1
            overview["components_by_stereotype"] = stereotypes

        # Container info
        containers = self._facts.get("containers", {})
        if isinstance(containers, dict):
            overview["architecture_style"] = containers.get("architecture_style", "")
            overview["patterns"] = containers.get("patterns", [])
            overview["technologies"] = containers.get("technologies", [])

        # Interface count
        interfaces = self._facts.get("interfaces", [])
        if isinstance(interfaces, list):
            overview["total_interfaces"] = len(interfaces)

        return overview

    def _rag_query(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Execute semantic search via RAG."""
        try:
            from ...shared.tools.rag_query_tool import RAGQueryTool

            tool = RAGQueryTool(chroma_dir=self._chroma_dir)
            result_json = tool._run(query=query, limit=limit)
            result = json.loads(result_json)
            return result.get("results", [])
        except Exception as exc:
            logger.warning("[DataCollector] RAG query failed for '%s': %s", query, exc)
            return []

    def _list_components(self, stereotype: str, limit: int = 30) -> list[dict[str, Any]]:
        """List components by stereotype from facts."""
        components = self._facts.get("components", [])
        if not isinstance(components, list):
            return []

        filtered = [
            c for c in components if isinstance(c, dict) and c.get("stereotype", "").lower() == stereotype.lower()
        ]

        # Sort by name and limit
        filtered.sort(key=lambda c: c.get("name", ""))
        return filtered[:limit]

    def _build_system_summary(self) -> str:
        """Build a concise system summary string for prompt context."""
        overview = self._get_system_overview()
        parts = []

        if overview.get("total_components"):
            parts.append(f"{overview['total_components']} components")
        if overview.get("total_interfaces"):
            parts.append(f"{overview['total_interfaces']} interfaces")
        if overview.get("architecture_style"):
            parts.append(f"style: {overview['architecture_style']}")

        stereotypes = overview.get("components_by_stereotype", {})
        if stereotypes:
            top = sorted(stereotypes.items(), key=lambda x: -x[1])[:5]
            parts.append("top types: " + ", ".join(f"{k}({v})" for k, v in top))

        return " | ".join(parts) if parts else "No system data available"
