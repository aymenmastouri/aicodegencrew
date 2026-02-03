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
    container: str = Field(
        default="",
        description="Container filter: filter by container name"
    )
    limit: int = Field(
        default=100,
        description="Maximum number of results per page (default 100, max 500)"
    )
    offset: int = Field(
        default=0,
        description="Skip first N results for pagination (use with limit for large repos)"
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
        container: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> str:
        """
        Execute facts query with pagination support.
        
        Args:
            category: Filter by category (components/relations/interfaces/containers/all)
            query: Search text for filtering
            stereotype: Filter by component stereotype
            container: Filter by container name
            limit: Max results per page (max 500 for large repos)
            offset: Skip first N results for pagination
            
        Returns:
            JSON string with matching facts and pagination info
        """
        try:
            facts = self._load_facts()
            if not facts:
                return json.dumps({"error": "No facts available", "results": []})
            
            # Cap limit at 500 for large repo support
            limit = min(limit, 500)
            offset = max(offset, 0)
            
            results = {}
            query_lower = query.lower()
            container_lower = container.lower() if container else ""
            
            # Track totals for pagination info
            pagination_info = {}
            
            # Query components
            if category in ("components", "all"):
                all_components = facts.get("components", [])
                components, total_matching = self._filter_components(
                    all_components,
                    query_lower,
                    stereotype,
                    container_lower,
                    limit,
                    offset
                )
                if components:
                    results["components"] = components
                pagination_info["components"] = {
                    "returned": len(components),
                    "total_matching": total_matching,
                    "offset": offset,
                    "has_more": (offset + len(components)) < total_matching
                }
            
            # Query relations
            if category in ("relations", "all"):
                all_relations = facts.get("relations", [])
                relations, total_rel = self._filter_relations(
                    all_relations,
                    query_lower,
                    limit,
                    offset
                )
                if relations:
                    results["relations"] = relations
                pagination_info["relations"] = {
                    "returned": len(relations),
                    "total_matching": total_rel,
                    "has_more": (offset + len(relations)) < total_rel
                }
            
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
            
            # Build output with summary and pagination
            total_items = sum(len(v) for v in results.values())
            output = {
                "query_params": {
                    "category": category,
                    "search": query,
                    "stereotype": stereotype,
                    "container": container,
                    "limit": limit,
                    "offset": offset
                },
                "result_count": total_items,
                "pagination": pagination_info,
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
        container_filter: str,
        limit: int,
        offset: int
    ) -> tuple[List[Dict[str, Any]], int]:
        """Filter components by query text, stereotype, container with pagination.
        
        Returns:
            Tuple of (filtered_list, total_matching_count)
        """
        # First pass: count all matching (for pagination info)
        matching = []
        
        for c in components:
            # Stereotype filter
            if stereotype:
                c_stereotype = c.get("stereotype", "").lower()
                if stereotype.lower() != c_stereotype:
                    continue
            
            # Container filter
            if container_filter:
                c_container = (c.get("container") or "").lower()
                if container_filter not in c_container:
                    continue
            
            # Text search filter
            if query:
                searchable = f"{c.get('name', '')} {c.get('module', '')} {c.get('file_path', '')} {c.get('description', '')}".lower()
                if query not in searchable:
                    continue
            
            matching.append(c)
        
        total_matching = len(matching)
        
        # Apply pagination
        paginated = matching[offset:offset + limit]
        
        # Transform to output format
        filtered = []
        for c in paginated:
            # Derive package from module or file_path
            package = c.get("module") or ""
            if not package and c.get("file_path"):
                # Extract directory from file path as pseudo-package
                file_path = c.get("file_path", "")
                if "\\" in file_path:
                    package = "\\".join(file_path.split("\\")[:-1])
                elif "/" in file_path:
                    package = "/".join(file_path.split("/")[:-1])
            
            # Add to results (simplified for token efficiency)
            filtered.append({
                "name": c.get("name"),
                "stereotype": c.get("stereotype"),
                "package": package,
                "container": c.get("container"),
                "description": (c.get("description", "") or "")[:100],  # Truncate
            })
        
        return filtered, total_matching
    
    def _filter_relations(
        self,
        relations: List[Dict[str, Any]],
        query: str,
        limit: int,
        offset: int
    ) -> tuple[List[Dict[str, Any]], int]:
        """Filter relations by query text with pagination.
        
        Returns:
            Tuple of (filtered_list, total_matching_count)
        """
        # First pass: find all matching
        matching = []
        
        for r in relations:
            from_comp = r.get("from", "")
            to_comp = r.get("to", "")
            
            if query:
                searchable = f"{from_comp} {to_comp} {r.get('type', '')}".lower()
                if query not in searchable:
                    continue
            
            matching.append(r)
        
        total_matching = len(matching)
        
        # Apply pagination
        paginated = matching[offset:offset + limit]
        
        # Transform to output format
        filtered = []
        for r in paginated:
            filtered.append({
                "source": r.get("from", ""),
                "target": r.get("to", ""),
                "type": r.get("type"),
                "description": (r.get("description", "") or "")[:80],
            })
        
        return filtered, total_matching
    
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
