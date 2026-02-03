"""
Facts Query Tool - Architecture Facts Retrieval

CrewAI Best Practice: Agent queries only relevant facts instead of full context.
This prevents token limit overflow by using smart filtering.

Usage:
- query_facts(category="components", stereotype="controller")
- query_facts(category="relations", limit=20)
"""

import json
from pathlib import Path
from typing import Type, Dict, Any, Optional, List
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

from ....shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class FactsQueryInput(BaseModel):
    """Input schema for FactsQueryTool."""
    category: str = Field(
        default="all",
        description="Category to query: 'components', 'relations', 'interfaces', 'containers', 'all'"
    )
    query: str = Field(
        default="",
        description="Search text to filter results (searches in name, package, description)"
    )
    stereotype: str = Field(
        default="",
        description="Stereotype filter: 'controller', 'service', 'repository', 'entity', 'design_pattern', 'architecture_style'"
    )
    limit: int = Field(
        default=30,
        description="Maximum number of results (default 30, hard cap at 50)"
    )


class FactsQueryTool(BaseTool):
    """
    Tool for querying architecture facts with filtering.
    
    CrewAI Best Practice: 
    - Agents query only what they need
    - Reduces token usage significantly
    - Smart filtering by category/stereotype/text
    
    Usage Examples:
    1. query_facts(category="components", stereotype="controller")
    2. query_facts(category="relations", query="OrderService")
    3. query_facts(category="all", limit=50)
    """
    
    name: str = "query_facts"
    description: str = (
        "Query architecture facts from Phase 1 output. "
        "Filter by category (components/relations/interfaces/containers) and stereotype. "
        "Use this to discover architecture elements - don't assume or hardcode!"
    )
    args_schema: Type[BaseModel] = FactsQueryInput
    
    # Configuration
    facts_path: str = "knowledge/architecture/architecture_facts.json"
    
    _facts_cache: Optional[Dict[str, Any]] = None
    
    def __init__(self, facts_path: str = None, **kwargs):
        """Initialize with optional facts path override."""
        super().__init__(**kwargs)
        if facts_path:
            self.facts_path = facts_path
    
    def _load_facts(self) -> Dict[str, Any]:
        """Load facts from JSON file with caching."""
        if self._facts_cache is not None:
            return self._facts_cache
        
        path = Path(self.facts_path)
        if not path.exists():
            logger.warning(f"Facts file not found: {path}")
            return {}
        
        with open(path, 'r', encoding='utf-8') as f:
            self._facts_cache = json.load(f)
        
        logger.info(f"Loaded facts: {len(self._facts_cache.get('components', []))} components")
        return self._facts_cache
    
    def _run(
        self,
        category: str = "all",
        query: str = "",
        stereotype: str = "",
        limit: int = 30,
    ) -> str:
        """
        Execute facts query.
        
        Args:
            category: Filter by category (components/relations/interfaces/containers/all)
            query: Search text for filtering
            stereotype: Filter by component stereotype
            limit: Max results (hard cap at 50)
            
        Returns:
            JSON string with matching facts
        """
        try:
            facts = self._load_facts()
            if not facts:
                return json.dumps({"error": "No facts available", "results": []})
            
            # Hard cap limit to prevent token overflow
            limit = min(limit, 50)
            
            results = {}
            query_lower = query.lower()
            
            # Query components
            if category in ("components", "all"):
                components = self._filter_components(
                    facts.get("components", []),
                    query_lower,
                    stereotype,
                    limit
                )
                if components:
                    results["components"] = components
            
            # Query relations
            if category in ("relations", "all"):
                relations = self._filter_relations(
                    facts.get("relations", []),
                    query_lower,
                    limit
                )
                if relations:
                    results["relations"] = relations
            
            # Query interfaces
            if category in ("interfaces", "all"):
                interfaces = self._filter_items(
                    facts.get("interfaces", []),
                    query_lower,
                    limit
                )
                if interfaces:
                    results["interfaces"] = interfaces
            
            # Query containers
            if category in ("containers", "all"):
                containers = self._filter_items(
                    facts.get("containers", []),
                    query_lower,
                    limit
                )
                if containers:
                    results["containers"] = containers
            
            # Build output with summary
            total_items = sum(len(v) for v in results.values())
            output = {
                "query_params": {
                    "category": category,
                    "search": query,
                    "stereotype": stereotype,
                    "limit": limit
                },
                "result_count": total_items,
                "results": results
            }
            
            return json.dumps(output, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Facts query error: {e}")
            return json.dumps({"error": str(e), "results": {}})
    
    def _filter_components(
        self,
        components: List[Dict[str, Any]],
        query: str,
        stereotype: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Filter components by query text and stereotype."""
        filtered = []
        
        for c in components:
            # Stereotype filter
            if stereotype:
                c_stereotype = c.get("stereotype", "").lower()
                if stereotype.lower() != c_stereotype:
                    continue
            
            # Text search filter
            if query:
                searchable = f"{c.get('name', '')} {c.get('package', '')} {c.get('description', '')}".lower()
                if query not in searchable:
                    continue
            
            # Add to results (simplified for token efficiency)
            filtered.append({
                "name": c.get("name"),
                "stereotype": c.get("stereotype"),
                "package": c.get("package"),
                "container": c.get("container"),
                "description": (c.get("description", "") or "")[:100],  # Truncate
            })
            
            if len(filtered) >= limit:
                break
        
        return filtered
    
    def _filter_relations(
        self,
        relations: List[Dict[str, Any]],
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Filter relations by query text."""
        filtered = []
        
        for r in relations:
            if query:
                searchable = f"{r.get('source', '')} {r.get('target', '')} {r.get('type', '')}".lower()
                if query not in searchable:
                    continue
            
            filtered.append({
                "source": r.get("source"),
                "target": r.get("target"),
                "type": r.get("type"),
                "description": (r.get("description", "") or "")[:80],
            })
            
            if len(filtered) >= limit:
                break
        
        return filtered
    
    def _filter_items(
        self,
        items: List[Dict[str, Any]],
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Generic filter for interfaces/containers."""
        filtered = []
        
        for item in items:
            if query:
                searchable = json.dumps(item).lower()
                if query not in searchable:
                    continue
            
            filtered.append(item)
            
            if len(filtered) >= limit:
                break
        
        return filtered
