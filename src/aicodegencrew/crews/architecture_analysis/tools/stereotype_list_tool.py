"""
Stereotype List Tool - Get components by stereotype

CrewAI Best Practice: Get focused lists of components by stereotype
to reduce context size and improve agent focus.

Usage:
- list_components_by_stereotype(stereotype="controller")
- list_components_by_stereotype(stereotype="service", container="backend")
"""

import json
from pathlib import Path
from typing import Type, Dict, Any, Optional, List
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

from ....shared.utils.logger import setup_logger

logger = setup_logger(__name__)


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
        default=30,
        description="Maximum results to return (default 30)"
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
        "Stereotypes: controller, service, repository, entity, design_pattern, architecture_style. "
        "Use this to discover architecture elements by type."
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
        limit: int = 30
    ) -> str:
        """Get components by stereotype (limited to prevent token overflow)."""
        
        MAX_RESULTS = min(limit, 50)  # Hard cap
        
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
        
        # LIMIT results to prevent token overflow
        limited = filtered[:MAX_RESULTS]
        
        # Build result with summary
        result = {
            "stereotype": stereotype,
            "container_filter": container,
            "total_count": total_count,
            "returned_count": len(limited),
            "note": f"Showing top {len(limited)} of {total_count}. Focus on these key components." if total_count > MAX_RESULTS else None,
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
    
    def get_stereotype_summary(self) -> Dict[str, int]:
        """Get count of components per stereotype."""
        facts = self._load_facts()
        components = facts.get("components", [])
        
        summary = {}
        for c in components:
            stereotype = c.get("stereotype", "unknown")
            summary[stereotype] = summary.get(stereotype, 0) + 1
        
        return summary
