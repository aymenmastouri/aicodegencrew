"""
Facts Statistics Tool - Overview without loading all data.

For large repositories (100,000+ components), agents need:
1. High-level statistics first
2. Then targeted queries

This prevents token overflow while giving complete picture.
"""

import json
from collections import Counter
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ....shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class FactsStatisticsInput(BaseModel):
    """Input schema for FactsStatisticsTool."""

    include_samples: bool = Field(default=False, description="Include 3 sample items per category for context")


class FactsStatisticsTool(BaseTool):
    """
    Tool for getting architecture facts statistics WITHOUT loading all data.

    Use this FIRST to understand the scale of the repository:
    - Total components, relations, interfaces
    - Breakdown by stereotype
    - Breakdown by container

    Then use targeted queries with filters.
    """

    name: str = "get_facts_statistics"
    description: str = (
        "Get statistics about architecture facts WITHOUT loading all data. "
        "Use FIRST to understand repository scale. "
        "Returns: total counts, stereotype breakdown, container breakdown. "
        "For 100k+ component repos, this is essential before querying."
    )
    args_schema: type[BaseModel] = FactsStatisticsInput

    # Configuration
    facts_path: str = "knowledge/extract/architecture_facts.json"

    def __init__(self, facts_path: str = None, **kwargs):
        """Initialize with optional facts path override."""
        super().__init__(**kwargs)
        if facts_path:
            self.facts_path = facts_path

    def _run(self, include_samples: bool = False) -> str:
        """
        Get statistics about architecture facts.

        Args:
            include_samples: Include 3 sample items per category

        Returns:
            JSON string with statistics
        """
        try:
            path = Path(self.facts_path)
            if not path.exists():
                return json.dumps({"error": f"Facts file not found: {path}"})

            with open(path, encoding="utf-8") as f:
                facts = json.load(f)

            components = facts.get("components", [])
            relations = facts.get("relations", [])
            interfaces = facts.get("interfaces", [])
            containers = facts.get("containers", [])

            # Stereotype breakdown
            stereotype_counts = Counter(c.get("stereotype", "unknown") for c in components)

            # Container breakdown
            container_counts = Counter(c.get("container", "unknown") for c in components)

            # Relation type breakdown
            relation_type_counts = Counter(r.get("type", "unknown") for r in relations)

            stats = {
                "repository_scale": self._classify_scale(len(components)),
                "totals": {
                    "components": len(components),
                    "relations": len(relations),
                    "interfaces": len(interfaces),
                    "containers": len(containers),
                },
                "components_by_stereotype": dict(stereotype_counts.most_common(20)),
                "components_by_container": dict(container_counts.most_common(10)),
                "relations_by_type": dict(relation_type_counts.most_common(10)),
                "recommendation": self._get_query_recommendation(len(components)),
            }

            if include_samples:
                stats["samples"] = {
                    "components": [{"name": c.get("name"), "stereotype": c.get("stereotype")} for c in components[:3]],
                    "relations": [
                        {"from": r.get("from"), "to": r.get("to"), "type": r.get("type")} for r in relations[:3]
                    ],
                }

            return json.dumps(stats, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Statistics error: {e}")
            return json.dumps({"error": str(e)})

    def _classify_scale(self, component_count: int) -> str:
        """Classify repository scale."""
        if component_count < 100:
            return "small (< 100 components)"
        elif component_count < 1000:
            return "medium (100-1000 components)"
        elif component_count < 10000:
            return "large (1000-10000 components)"
        else:
            return f"enterprise ({component_count:,} components)"

    def _get_query_recommendation(self, component_count: int) -> str:
        """Recommend query strategy based on scale."""
        if component_count < 500:
            return "Small repo: Use query_facts with limit=100 to see most components"
        elif component_count < 5000:
            return "Medium repo: Query by stereotype, use limit=200 per query"
        elif component_count < 50000:
            return "Large repo: Query by stereotype AND container, use pagination"
        else:
            return (
                "Enterprise repo: Use paginated_query with offset/limit. "
                "Query one stereotype at a time. Process in batches of 500."
            )
