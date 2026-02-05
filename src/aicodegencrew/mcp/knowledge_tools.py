"""
Knowledge Tools - Core logic for querying Phase 1 architecture facts.

These tools solve the token limit problem by providing structured,
targeted queries instead of loading entire codebase into context.
"""

import json
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class KnowledgeConfig:
    """Configuration for knowledge base location."""
    knowledge_path: Path
    
    @classmethod
    def from_env(cls, knowledge_dir: Optional[str] = None) -> "KnowledgeConfig":
        """Create config from environment or default."""
        if knowledge_dir:
            path = Path(knowledge_dir)
        else:
            # Default to knowledge/architecture in project root
            path = Path.cwd() / "knowledge" / "architecture"
        return cls(knowledge_path=path)


class KnowledgeTools:
    """
    Tools for querying the architecture knowledge base.
    
    Provides targeted access to Phase 1 facts without token explosion.
    """
    
    def __init__(self, config: KnowledgeConfig):
        self.config = config
        self._components_cache = None
        self._relations_cache = None
        self._interfaces_cache = None
        self._evidence_cache = None
        self._data_model_cache = None
    
    def _load_json(self, filename: str) -> dict:
        """Load a JSON file from knowledge base."""
        file_path = self.config.knowledge_path / filename
        if not file_path.exists():
            return {"error": f"File not found: {filename}"}
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    @property
    def components(self) -> dict:
        """Lazy load components."""
        if self._components_cache is None:
            self._components_cache = self._load_json("components.json")
        return self._components_cache
    
    @property
    def relations(self) -> dict:
        """Lazy load relations."""
        if self._relations_cache is None:
            self._relations_cache = self._load_json("relations.json")
        return self._relations_cache
    
    @property
    def interfaces(self) -> dict:
        """Lazy load interfaces."""
        if self._interfaces_cache is None:
            self._interfaces_cache = self._load_json("interfaces.json")
        return self._interfaces_cache
    
    @property
    def evidence(self) -> dict:
        """Lazy load evidence map."""
        if self._evidence_cache is None:
            self._evidence_cache = self._load_json("evidence_map.json")
        return self._evidence_cache
    
    @property
    def data_model(self) -> dict:
        """Lazy load data model."""
        if self._data_model_cache is None:
            self._data_model_cache = self._load_json("data_model.json")
        return self._data_model_cache
    
    # ========== Component Tools ==========
    
    def get_component(self, name: str) -> dict:
        """
        Get a component by name (case-insensitive partial match).
        
        Args:
            name: Component name or partial name (e.g., "WorkflowController")
            
        Returns:
            Component details or list of matches
        """
        name_lower = name.lower()
        matches = []
        
        for comp in self.components.get("components", []):
            if name_lower in comp.get("name", "").lower():
                matches.append(comp)
        
        if len(matches) == 1:
            return {"component": matches[0]}
        elif len(matches) > 1:
            return {
                "matches": len(matches),
                "components": [{"id": c["id"], "name": c["name"], "stereotype": c.get("stereotype")} for c in matches[:20]],
                "hint": "Multiple matches. Use more specific name or full ID."
            }
        else:
            return {"error": f"No component found matching '{name}'"}
    
    def get_component_by_id(self, component_id: str) -> dict:
        """
        Get a component by exact ID.
        
        Args:
            component_id: Full component ID (e.g., "component.backend.service.workflow_service")
        """
        for comp in self.components.get("components", []):
            if comp.get("id") == component_id:
                return {"component": comp}
        return {"error": f"Component not found: {component_id}"}
    
    def list_components_by_stereotype(self, stereotype: str) -> dict:
        """
        List all components of a given stereotype.
        
        Args:
            stereotype: e.g., "service", "controller", "repository", "entity"
        """
        matches = [
            {"id": c["id"], "name": c["name"], "layer": c.get("layer")}
            for c in self.components.get("components", [])
            if c.get("stereotype", "").lower() == stereotype.lower()
        ]
        return {
            "stereotype": stereotype,
            "count": len(matches),
            "components": matches
        }
    
    def list_components_by_layer(self, layer: str) -> dict:
        """
        List all components in a given layer.
        
        Args:
            layer: e.g., "presentation", "application", "domain", "dataaccess"
        """
        matches = [
            {"id": c["id"], "name": c["name"], "stereotype": c.get("stereotype")}
            for c in self.components.get("components", [])
            if c.get("layer", "").lower() == layer.lower()
        ]
        return {
            "layer": layer,
            "count": len(matches),
            "components": matches
        }
    
    def search_components(self, pattern: str) -> dict:
        """
        Search components by regex pattern.
        
        Args:
            pattern: Regex pattern to match against name, module, or file path
        """
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return {"error": f"Invalid regex: {e}"}
        
        matches = []
        for comp in self.components.get("components", []):
            searchable = f"{comp.get('name', '')} {comp.get('module', '')} {' '.join(comp.get('file_paths', []))}"
            if regex.search(searchable):
                matches.append({
                    "id": comp["id"],
                    "name": comp["name"],
                    "stereotype": comp.get("stereotype"),
                    "file": comp.get("file_paths", [""])[0] if comp.get("file_paths") else None
                })
        
        return {
            "pattern": pattern,
            "count": len(matches),
            "components": matches[:50]  # Limit results
        }
    
    # ========== Relation Tools ==========
    
    def get_relations_for(self, component_id: str) -> dict:
        """
        Get all relations for a component (incoming and outgoing).
        
        Args:
            component_id: Full component ID or partial name
        """
        # If partial name, try to find the component first
        if not component_id.startswith("component."):
            result = self.get_component(component_id)
            if "error" in result:
                return result
            if "component" in result:
                component_id = result["component"]["id"]
            else:
                return {"error": "Ambiguous component name. Please use full ID."}
        
        outgoing = []
        incoming = []
        
        for rel in self.relations.get("relations", []):
            if rel.get("from") == component_id:
                outgoing.append({
                    "to": rel["to"],
                    "type": rel.get("type"),
                    "to_name": self._get_component_name(rel["to"])
                })
            if rel.get("to") == component_id:
                incoming.append({
                    "from": rel["from"],
                    "type": rel.get("type"),
                    "from_name": self._get_component_name(rel["from"])
                })
        
        return {
            "component_id": component_id,
            "outgoing": {"count": len(outgoing), "relations": outgoing},
            "incoming": {"count": len(incoming), "relations": incoming}
        }
    
    def get_call_graph(self, component_id: str, depth: int = 2) -> dict:
        """
        Get the call graph for a component up to specified depth.
        
        Args:
            component_id: Starting component ID or name
            depth: How many levels deep to traverse (default: 2)
        """
        # Resolve component ID
        if not component_id.startswith("component."):
            result = self.get_component(component_id)
            if "error" in result:
                return result
            if "component" in result:
                component_id = result["component"]["id"]
            else:
                return {"error": "Ambiguous component name. Please use full ID."}
        
        visited = set()
        graph = {"root": component_id, "nodes": [], "edges": []}
        
        def traverse(comp_id: str, current_depth: int):
            if current_depth > depth or comp_id in visited:
                return
            visited.add(comp_id)
            
            graph["nodes"].append({
                "id": comp_id,
                "name": self._get_component_name(comp_id),
                "depth": current_depth
            })
            
            for rel in self.relations.get("relations", []):
                if rel.get("from") == comp_id:
                    graph["edges"].append({
                        "from": comp_id,
                        "to": rel["to"],
                        "type": rel.get("type")
                    })
                    traverse(rel["to"], current_depth + 1)
        
        traverse(component_id, 0)
        
        return {
            "component_id": component_id,
            "depth": depth,
            "graph": graph
        }
    
    def _get_component_name(self, component_id: str) -> str:
        """Helper to get component name from ID."""
        for comp in self.components.get("components", []):
            if comp.get("id") == component_id:
                return comp.get("name", component_id)
        return component_id.split(".")[-1]
    
    # ========== Interface Tools ==========
    
    def get_endpoints(self, path_pattern: Optional[str] = None) -> dict:
        """
        Get REST endpoints, optionally filtered by path pattern.
        
        Args:
            path_pattern: Optional regex to filter paths (e.g., "/workflow.*")
        """
        endpoints = []
        regex = None
        
        if path_pattern:
            try:
                regex = re.compile(path_pattern, re.IGNORECASE)
            except re.error as e:
                return {"error": f"Invalid regex: {e}"}
        
        for iface in self.interfaces.get("interfaces", []):
            if iface.get("type") != "rest_endpoint":
                continue
            if regex and not regex.search(iface.get("path", "")):
                continue
            endpoints.append({
                "path": iface.get("path"),
                "method": iface.get("method"),
                "implemented_by": iface.get("implemented_by"),
                "id": iface.get("id")
            })
        
        return {
            "filter": path_pattern,
            "count": len(endpoints),
            "endpoints": endpoints
        }
    
    def get_endpoint_by_path(self, path: str, method: Optional[str] = None) -> dict:
        """
        Get endpoint details by exact path.
        
        Args:
            path: Exact path (e.g., "/uvz/v1/workflow/{id}")
            method: Optional HTTP method filter (GET, POST, etc.)
        """
        for iface in self.interfaces.get("interfaces", []):
            if iface.get("path") == path:
                if method and iface.get("method") != method.upper():
                    continue
                return {"endpoint": iface}
        return {"error": f"Endpoint not found: {method or 'ANY'} {path}"}
    
    def get_routes(self) -> dict:
        """Get all frontend routes."""
        routes = [
            {"path": iface.get("path"), "id": iface.get("id")}
            for iface in self.interfaces.get("interfaces", [])
            if iface.get("type") == "route"
        ]
        return {"count": len(routes), "routes": routes}
    
    # ========== Evidence Tools ==========
    
    def get_evidence(self, evidence_id: str) -> dict:
        """
        Get evidence by ID (the actual code snippet).
        
        Args:
            evidence_id: Evidence ID (e.g., "ev_123")
        """
        evidence_list = self.evidence.get("evidence", [])
        for ev in evidence_list:
            if ev.get("id") == evidence_id:
                return {"evidence": ev}
        return {"error": f"Evidence not found: {evidence_id}"}
    
    def get_evidence_for_component(self, component_id: str) -> dict:
        """
        Get all evidence for a component.
        
        Args:
            component_id: Component ID or name
        """
        # Resolve component
        if not component_id.startswith("component."):
            result = self.get_component(component_id)
            if "error" in result:
                return result
            if "component" in result:
                component_id = result["component"]["id"]
                evidence_ids = result["component"].get("evidence_ids", [])
            else:
                return {"error": "Ambiguous component name."}
        else:
            comp_result = self.get_component_by_id(component_id)
            if "error" in comp_result:
                return comp_result
            evidence_ids = comp_result["component"].get("evidence_ids", [])
        
        evidence_list = []
        for ev_id in evidence_ids:
            ev_result = self.get_evidence(ev_id)
            if "evidence" in ev_result:
                evidence_list.append(ev_result["evidence"])
        
        return {
            "component_id": component_id,
            "count": len(evidence_list),
            "evidence": evidence_list
        }
    
    # ========== Summary Tools ==========
    
    def get_architecture_summary(self) -> dict:
        """Get high-level architecture summary."""
        return {
            "components": {
                "total": self.components.get("total", 0),
                "by_layer": self.components.get("by_layer", {}),
                "by_stereotype": self.components.get("by_stereotype", {})
            },
            "relations": {
                "total": self.relations.get("total", 0),
                "by_type": self.relations.get("by_type", {})
            },
            "interfaces": {
                "total": self.interfaces.get("total", 0),
                "by_type": self.interfaces.get("by_type", {})
            }
        }
    
    def get_statistics(self) -> dict:
        """Get detailed statistics about the knowledge base."""
        comp_data = self.components
        rel_data = self.relations
        iface_data = self.interfaces
        
        return {
            "knowledge_path": str(self.config.knowledge_path),
            "components": {
                "total": comp_data.get("total", 0),
                "layers": list(comp_data.get("by_layer", {}).keys()),
                "stereotypes": list(comp_data.get("by_stereotype", {}).keys())
            },
            "relations": {
                "total": rel_data.get("total", 0),
                "types": list(rel_data.get("by_type", {}).keys())
            },
            "interfaces": {
                "total": iface_data.get("total", 0),
                "rest_endpoints": iface_data.get("by_type", {}).get("rest_endpoint", {}).get("count", 0),
                "routes": iface_data.get("by_type", {}).get("route", {}).get("count", 0)
            }
        }
