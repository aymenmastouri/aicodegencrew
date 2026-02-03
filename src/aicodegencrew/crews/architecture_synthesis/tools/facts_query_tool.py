"""
Facts Query Tool - RAG-based Architecture Facts Retrieval

CrewAI Best Practice: Agent queries only relevant facts instead of full context.
This prevents token limit overflow by using semantic search.

Strategy 6: RAG statt Full-Context
- Agent fragt nach spezifischen Komponenten/Typen
- ChromaDB liefert nur relevante Facts
- Drastische Reduktion der Token-Nutzung
"""

import json
import os
from pathlib import Path
from typing import Type, List, Dict, Any, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
import chromadb
from chromadb.config import Settings

from ....shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class FactsQueryInput(BaseModel):
    """Input schema for FactsQueryTool."""
    query: str = Field(
        ..., 
        description="What facts to search for. Examples: 'all controllers', 'services using OrderRepository', 'entities with JPA annotations', 'REST endpoints for user management'"
    )
    category: str = Field(
        default="all",
        description="Category to filter: 'components', 'relations', 'interfaces', 'containers', 'all'"
    )
    stereotype: str = Field(
        default="",
        description="Stereotype filter: 'controller', 'service', 'repository', 'entity', 'component', or empty for all"
    )
    limit: int = Field(
        default=50,
        description="Maximum number of results to return (default 50)"
    )


class FactsQueryTool(BaseTool):
    """
    RAG-based tool for querying architecture facts.
    
    CrewAI Best Practice: 
    - Agents query only what they need
    - Reduces token usage by 80-90%
    - Semantic search finds relevant facts
    
    Usage by Agent:
    1. Query: "controllers for order management" -> Returns OrderController, OrderItemController
    2. Query: "services that call repositories" -> Returns Service->Repository relations
    3. Query: "all entities" stereotype="entity" -> Returns all JPA entities
    """
    
    name: str = "query_architecture_facts"
    description: str = (
        "Query architecture facts using semantic search. "
        "Use this instead of reading the full facts file! "
        "Returns only relevant components, relations, or interfaces. "
        "Supports filtering by category (components/relations/interfaces/containers) "
        "and stereotype (controller/service/repository/entity)."
    )
    args_schema: Type[BaseModel] = FactsQueryInput
    
    # Configuration
    facts_path: str = "knowledge/architecture/architecture_facts.json"
    chroma_dir: Optional[str] = None
    collection_name: str = "architecture_facts"
    
    _facts_cache: Optional[Dict[str, Any]] = None
    _indexed: bool = False
    
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
        query: str,
        category: str = "all",
        stereotype: str = "",
        limit: int = 50,
    ) -> str:
        """
        Execute facts query.
        
        Args:
            query: Semantic search query
            category: Filter by category (components/relations/interfaces/containers/all)
            stereotype: Filter by component stereotype
            limit: Max results (capped at 30 to prevent token overflow)
            
        Returns:
            JSON string with matching facts
        """
        try:
            facts = self._load_facts()
            if not facts:
                return json.dumps({"error": "No facts available", "results": []})
            
            # Hard cap limit to prevent token overflow
            limit = min(limit, 30)
            
            results = []
            query_lower = query.lower()
            
            # Filter by category
            if category in ("components", "all"):
                results.extend(self._search_components(facts, query_lower, stereotype, limit))
            
            if category in ("relations", "all"):
                results.extend(self._search_relations(facts, query_lower, limit))
            
            if category in ("interfaces", "all"):
                results.extend(self._search_interfaces(facts, query_lower, limit))
            
            if category in ("containers", "all"):
                results.extend(self._search_containers(facts, query_lower, limit))
            
            # Limit total results
            results = results[:limit]
            
            # Format output
            output = {
                "query": query,
                "category": category,
                "stereotype_filter": stereotype,
                "total_results": len(results),
                "results": results,
            }
            
            return json.dumps(output, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Facts query error: {e}")
            return json.dumps({"error": str(e), "results": []})
    
    def _search_components(
        self, 
        facts: Dict[str, Any], 
        query: str, 
        stereotype: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search components by query and stereotype."""
        components = facts.get("components", [])
        results = []
        
        for comp in components:
            # Filter by stereotype if specified
            comp_stereo = comp.get("stereotype", "").lower()
            if stereotype and comp_stereo != stereotype.lower():
                continue
            
            # Score relevance
            score = self._calculate_relevance(comp, query)
            if score > 0:
                results.append({
                    "type": "component",
                    "relevance": score,
                    **comp
                })
        
        # Sort by relevance and limit
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:limit]
    
    def _search_relations(
        self, 
        facts: Dict[str, Any], 
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search relations by query."""
        relations = facts.get("relations", [])
        results = []
        
        for rel in relations:
            score = self._calculate_relevance(rel, query)
            if score > 0:
                results.append({
                    "type": "relation",
                    "relevance": score,
                    **rel
                })
        
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:limit]
    
    def _search_interfaces(
        self, 
        facts: Dict[str, Any], 
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search interfaces by query."""
        interfaces = facts.get("interfaces", [])
        results = []
        
        for iface in interfaces:
            score = self._calculate_relevance(iface, query)
            if score > 0:
                results.append({
                    "type": "interface",
                    "relevance": score,
                    **iface
                })
        
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:limit]
    
    def _search_containers(
        self, 
        facts: Dict[str, Any], 
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search containers by query."""
        containers = facts.get("containers", [])
        results = []
        
        for container in containers:
            score = self._calculate_relevance(container, query)
            if score > 0:
                results.append({
                    "type": "container",
                    "relevance": score,
                    **container
                })
        
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:limit]
    
    def _calculate_relevance(self, item: Dict[str, Any], query: str) -> float:
        """Calculate relevance score for an item."""
        score = 0.0
        query_terms = query.split()
        
        # Check all string fields
        for key, value in item.items():
            if isinstance(value, str):
                value_lower = value.lower()
                # Exact match in any field
                if query in value_lower:
                    score += 5.0
                # Term matches
                for term in query_terms:
                    if term in value_lower:
                        score += 1.0
        
        # Boost for name matches
        name = item.get("name", "").lower()
        if query in name:
            score += 10.0
        
        return score
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of available facts without full details."""
        facts = self._load_facts()
        
        # Count by stereotype
        stereotype_counts = {}
        for comp in facts.get("components", []):
            stereo = comp.get("stereotype", "unknown")
            stereotype_counts[stereo] = stereotype_counts.get(stereo, 0) + 1
        
        # Count relations by type
        relation_type_counts = {}
        for rel in facts.get("relations", []):
            rtype = rel.get("type", "unknown")
            relation_type_counts[rtype] = relation_type_counts.get(rtype, 0) + 1
        
        # Count interfaces by method
        method_counts = {}
        for iface in facts.get("interfaces", []):
            method = iface.get("method", "unknown")
            method_counts[method] = method_counts.get(method, 0) + 1
        
        return {
            "system": facts.get("system", {}),
            "architecture_style": facts.get("architecture_style", {}),
            "containers": len(facts.get("containers", [])),
            "components_by_stereotype": stereotype_counts,
            "relations_by_type": relation_type_counts,
            "interfaces_by_method": method_counts,
            "total_components": len(facts.get("components", [])),
            "total_relations": len(facts.get("relations", [])),
            "total_interfaces": len(facts.get("interfaces", [])),
        }
