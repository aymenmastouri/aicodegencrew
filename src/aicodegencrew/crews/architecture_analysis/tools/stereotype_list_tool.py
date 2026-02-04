"""
Stereotype List Tool - Get components by stereotype

CrewAI Best Practice: Get focused lists of components by stereotype
to reduce context size and improve agent focus.

Usage:
- list_components_by_stereotype(stereotype="controller")
- list_components_by_stereotype(stereotype="service", container="backend")

Relevance Sorting:
- Components are sorted by architectural layer importance
- Backend: controller → service → repository → entity → rest
- Frontend: component → module → service → pipe → directive → rest
"""

import json
from pathlib import Path
from typing import Type, Dict, Any, Optional, List
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

from ....shared.utils.logger import setup_logger

logger = setup_logger(__name__)

# Dynamic layer priority based on common patterns
# Lower number = higher priority (shown first)
LAYER_PRIORITY = {
    # Backend layers (Spring/Java patterns)
    "controller": 1,       # REST entry points - most important for understanding API
    "rest_controller": 1,
    "resource": 1,
    "service": 2,          # Business logic layer
    "facade": 2,
    "manager": 2,
    "repository": 3,       # Data access layer
    "dao": 3,
    "entity": 4,           # Domain model
    "model": 4,
    "dto": 4,
    "mapper": 5,
    "validator": 5,
    "config": 6,
    "configuration": 6,
    
    # Frontend layers (Angular/React patterns)
    "component": 1,        # UI entry points
    "page": 1,
    "container": 1,
    "module": 2,           # Feature modules
    "service": 2,          # Shared services (also backend)
    "store": 2,            # State management
    "reducer": 2,
    "guard": 3,
    "resolver": 3,
    "interceptor": 3,
    "pipe": 4,
    "directive": 4,
    "effect": 4,
    
    # Infrastructure
    "integration": 3,
    "adapter": 3,
    "client": 3,
    "gateway": 3,
    
    # Architecture patterns
    "design_pattern": 1,   # Show patterns first
    "architecture_style": 1,
    
    # Database/Schema
    "database_connection": 5,
    "database_schema": 5,
    "sql_script": 6,
}

DEFAULT_PRIORITY = 10  # Unknown stereotypes get lowest priority


class StereotypeListInput(BaseModel):
    """Input for listing components by stereotype."""
    stereotype: str = Field(
        ...,
        description="Component stereotype: 'controller', 'service', 'repository', 'entity', 'design_pattern', 'architecture_style'"
    )
    container: str = Field(
        default="",
        description="Optional container filter"
    )
    limit: int = Field(
        default=100,
        description="Maximum results to return (default 100, max 500 for large repos)"
    )
    offset: int = Field(
        default=0,
        description="Number of results to skip for pagination (default 0)"
    )


class StereotypeListTool(BaseTool):
    """
    Get component lists by stereotype.
    
    CrewAI Best Practice: 
    - Agent requests specific stereotype list
    - Reduces context size vs full components list
    - Focused discovery per component type
    
    Usage Examples:
    1. list_components_by_stereotype(stereotype="controller") - All controllers
    2. list_components_by_stereotype(stereotype="design_pattern") - All detected patterns
    3. list_components_by_stereotype(stereotype="entity", container="backend") - Backend entities
    """
    
    name: str = "list_components_by_stereotype"
    description: str = (
        "Get list of components filtered by stereotype. "
        "REQUIRED: stereotype (string) - one of: controller, service, repository, entity, design_pattern, architecture_style, component, module. "
        "OPTIONAL: container (string) - filter by container name like 'backend' or 'frontend'. "
        "OPTIONAL: limit (int) - max results, default 100. "
        "Example: list_components_by_stereotype(stereotype='controller', limit=50)"
    )
    args_schema: Type[BaseModel] = StereotypeListInput
    
    facts_path: str = "knowledge/architecture/architecture_facts.json"
    _facts_cache: Optional[Dict[str, Any]] = None
    
    def __init__(self, facts_path: str = None, **kwargs):
        super().__init__(**kwargs)
        if facts_path:
            self.facts_path = facts_path
    
    def _load_facts(self) -> Dict[str, Any]:
        if self._facts_cache is not None:
            return self._facts_cache
        
        path = Path(self.facts_path)
        if not path.exists():
            return {}
        
        with open(path, 'r', encoding='utf-8') as f:
            self._facts_cache = json.load(f)
        return self._facts_cache
    
    def _run(
        self,
        stereotype: str,
        container: str = "",
        limit: int = 100,
        offset: int = 0
    ) -> str:
        """Get components by stereotype (limited to prevent token overflow)."""
        
        MAX_RESULTS = min(limit, 50)  # Hard cap at 50 to prevent context overflow
        
        facts = self._load_facts()
        components = facts.get("components", [])
        
        # Filter by stereotype
        filtered = [
            c for c in components 
            if c.get("stereotype", "").lower() == stereotype.lower()
        ]
        
        # Filter by container if specified
        if container:
            filtered = [
                c for c in filtered 
                if container.lower() in c.get("container", "").lower()
            ]
        
        total_count = len(filtered)
        
        # SORT by layer relevance - most architecturally important first
        filtered = self._sort_by_relevance(filtered)
        
        # Apply offset and limit for pagination
        start_idx = min(offset, total_count)
        end_idx = min(start_idx + MAX_RESULTS, total_count)
        limited = filtered[start_idx:end_idx]
        
        # Build result with summary
        result = {
            "stereotype": stereotype,
            "container_filter": container,
            "total_count": total_count,
            "offset": start_idx,
            "returned_count": len(limited),
            "has_more": end_idx < total_count,
            "note": f"Showing {start_idx+1}-{end_idx} of {total_count}. Use offset={end_idx} to get next page." if end_idx < total_count else f"Showing all {total_count} results.",
            "components": [
                {
                    "name": c.get("name", "Unknown"),
                    "package": c.get("package", ""),
                    "container": c.get("container", ""),
                    "description": (c.get("description", "") or "")[:100],  # Truncate
                }
                for c in limited
            ]
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
    
    def _sort_by_relevance(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort components by architectural layer relevance.
        
        Priority is determined by:
        1. Class name suffix patterns (Controller, Service, Repository, etc.)
        2. Package name patterns (controller, service, repository, etc.)
        3. Stereotype as fallback
        """
        def get_priority(component: Dict[str, Any]) -> tuple:
            name = component.get("name", "").lower()
            package = component.get("package", "").lower()
            stereotype = component.get("stereotype", "").lower()
            
            # Try to detect layer from class name suffix
            layer_priority = DEFAULT_PRIORITY
            
            # Check class name patterns (most reliable)
            name_patterns = [
                ("controller", 1), ("resource", 1), ("restcontroller", 1), ("restservice", 1),
                ("service", 2), ("facade", 2), ("manager", 2),
                ("repository", 3), ("dao", 3), ("repo", 3), ("daoimpl", 3),
                ("entity", 4), ("model", 4), ("dto", 4),
                ("mapper", 5), ("validator", 5), ("converter", 5),
                ("component", 1), ("page", 1),  # Frontend
                ("module", 2), ("store", 2),
                ("guard", 3), ("resolver", 3), ("interceptor", 3),
                ("pipe", 4), ("directive", 4),
            ]
            
            for pattern, priority in name_patterns:
                if name.endswith(pattern) or name.endswith(pattern + "impl"):
                    layer_priority = min(layer_priority, priority)
                    break
            
            # Check package patterns if no name match
            if layer_priority == DEFAULT_PRIORITY:
                package_patterns = [
                    ("controller", 1), ("rest", 1), ("adapter", 1), ("web", 1),
                    ("service", 2), ("logic", 2), ("business", 2),
                    ("repository", 3), ("dataaccess", 3), ("dao", 3), ("persistence", 3),
                    ("entity", 4), ("domain", 4), ("model", 4),
                    ("component", 1), ("page", 1), ("container", 1),
                ]
                
                for pattern, priority in package_patterns:
                    if pattern in package:
                        layer_priority = min(layer_priority, priority)
                        break
            
            # Fall back to stereotype priority
            if layer_priority == DEFAULT_PRIORITY:
                layer_priority = LAYER_PRIORITY.get(stereotype, DEFAULT_PRIORITY)
            
            # Secondary sort: alphabetically by name for consistency
            return (layer_priority, name)
        
        return sorted(components, key=get_priority)
    
    def get_stereotype_summary(self) -> Dict[str, int]:
        """Get count of components per stereotype."""
        facts = self._load_facts()
        components = facts.get("components", [])
        
        summary = {}
        for c in components:
            stereotype = c.get("stereotype", "unknown")
            summary[stereotype] = summary.get(stereotype, 0) + 1
        
        return summary
