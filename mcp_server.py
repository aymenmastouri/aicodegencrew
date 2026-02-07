#!/usr/bin/env python3
"""
AICodeGenCrew Knowledge MCP Server - Standalone Entry Point

This script runs the MCP server in complete isolation from the main
aicodegencrew package to avoid any stdout logging that would corrupt
the JSON-RPC STDIO transport.

Usage:
    python mcp_server.py
    
For CrewAI integration, use this in mcps=[]:
    MCPServerStdio(command="python", args=["mcp_server.py"])
"""

import json
import logging
import sys
from pathlib import Path
from typing import Optional

# Configure logging to stderr ONLY
logging.basicConfig(
    level=logging.WARNING,  # Quiet by default
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)

# Import MCP after logging config
from mcp.server.fastmcp import FastMCP

# =============================================================================
# Knowledge Tools (inline to avoid imports)
# =============================================================================

import re
from dataclasses import dataclass


@dataclass
class KnowledgeConfig:
    """Configuration for knowledge base location."""
    knowledge_path: Path
    
    @classmethod
    def auto_detect(cls) -> "KnowledgeConfig":
        """Auto-detect knowledge directory."""
        candidates = [
            Path.cwd() / "knowledge" / "architecture",
            Path.cwd().parent / "knowledge" / "architecture",
        ]
        for parent in Path.cwd().parents:
            candidates.append(parent / "knowledge" / "architecture")
        
        for path in candidates:
            if path.exists():
                return cls(knowledge_path=path)
        
        # Default fallback
        return cls(knowledge_path=Path.cwd() / "knowledge" / "architecture")


class KnowledgeTools:
    """Tools for querying the architecture knowledge base."""
    
    def __init__(self, config: KnowledgeConfig):
        self.config = config
        self._components_cache = None
        self._relations_cache = None
        self._interfaces_cache = None
        self._evidence_cache = None
    
    def _load_json(self, filename: str) -> dict:
        """Load a JSON file from knowledge base."""
        file_path = self.config.knowledge_path / filename
        if not file_path.exists():
            return {"error": f"File not found: {filename}"}
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    @property
    def components(self) -> dict:
        if self._components_cache is None:
            self._components_cache = self._load_json("components.json")
        return self._components_cache
    
    @property
    def relations(self) -> dict:
        if self._relations_cache is None:
            self._relations_cache = self._load_json("relations.json")
        return self._relations_cache
    
    @property
    def interfaces(self) -> dict:
        if self._interfaces_cache is None:
            self._interfaces_cache = self._load_json("interfaces.json")
        return self._interfaces_cache
    
    @property
    def evidence(self) -> dict:
        if self._evidence_cache is None:
            self._evidence_cache = self._load_json("evidence_map.json")
        return self._evidence_cache
    
    def get_component(self, name: str) -> dict:
        """Get component by name (partial match)."""
        name_lower = name.lower()
        matches = [c for c in self.components.get("components", []) 
                   if name_lower in c.get("name", "").lower()]
        if len(matches) == 1:
            return {"component": matches[0]}
        elif len(matches) > 1:
            return {"matches": len(matches), 
                    "components": [{"id": c["id"], "name": c["name"]} for c in matches[:20]]}
        return {"error": f"No component found: {name}"}
    
    def search_components(self, pattern: str) -> dict:
        """Search components by regex."""
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return {"error": f"Invalid regex: {e}"}
        
        matches = [
            {"id": c["id"], "name": c["name"], "stereotype": c.get("stereotype")}
            for c in self.components.get("components", [])
            if regex.search(f"{c.get('name', '')} {c.get('module', '')}")
        ]
        return {"pattern": pattern, "count": len(matches), "components": matches[:50]}
    
    def list_components_by_stereotype(self, stereotype: str) -> dict:
        """List components by stereotype."""
        matches = [
            {"id": c["id"], "name": c["name"], "layer": c.get("layer")}
            for c in self.components.get("components", [])
            if c.get("stereotype", "").lower() == stereotype.lower()
        ]
        return {"stereotype": stereotype, "count": len(matches), "components": matches}
    
    def get_relations_for(self, component_id: str) -> dict:
        """Get relations for a component."""
        if not component_id.startswith("component."):
            result = self.get_component(component_id)
            if "component" in result:
                component_id = result["component"]["id"]
            else:
                return result
        
        outgoing = [{"to": r["to"], "type": r.get("type")} 
                    for r in self.relations.get("relations", []) if r.get("from") == component_id]
        incoming = [{"from": r["from"], "type": r.get("type")} 
                    for r in self.relations.get("relations", []) if r.get("to") == component_id]
        return {"component_id": component_id, "outgoing": outgoing, "incoming": incoming}
    
    def get_endpoints(self, path_pattern: Optional[str] = None) -> dict:
        """Get REST endpoints."""
        endpoints = [e for e in self.interfaces.get("interfaces", []) 
                     if e.get("type") == "rest_endpoint"]
        if path_pattern:
            try:
                regex = re.compile(path_pattern, re.IGNORECASE)
                endpoints = [e for e in endpoints if regex.search(e.get("path", ""))]
            except re.error:
                pass
        return {"count": len(endpoints), "endpoints": [
            {"path": e.get("path"), "method": e.get("method")} for e in endpoints
        ]}
    
    def get_architecture_summary(self) -> dict:
        """Get high-level architecture summary with breakdowns."""
        return {
            "components": {
                "total": self.components.get("total", 0),
                "by_layer": self.components.get("by_layer", {}),
                "by_stereotype": self.components.get("by_stereotype", {}),
            },
            "relations": {
                "total": self.relations.get("total", 0),
                "by_type": self.relations.get("by_type", {}),
            },
            "interfaces": {
                "total": self.interfaces.get("total", 0),
                "by_type": self.interfaces.get("by_type", {}),
            },
        }

    def get_statistics(self) -> dict:
        """Get detailed statistics."""
        comp_data = self.components
        rel_data = self.relations
        iface_data = self.interfaces
        return {
            "knowledge_path": str(self.config.knowledge_path),
            "components": {
                "total": comp_data.get("total", 0),
                "layers": list(comp_data.get("by_layer", {}).keys()),
                "stereotypes": list(comp_data.get("by_stereotype", {}).keys()),
            },
            "relations": {
                "total": rel_data.get("total", 0),
                "types": list(rel_data.get("by_type", {}).keys()),
            },
            "interfaces": {
                "total": iface_data.get("total", 0),
                "types": list(iface_data.get("by_type", {}).keys()),
            },
        }


# =============================================================================
# MCP Server
# =============================================================================

mcp = FastMCP("aicodegencrew-knowledge")
_tools: Optional[KnowledgeTools] = None


def get_tools() -> KnowledgeTools:
    global _tools
    if _tools is None:
        config = KnowledgeConfig.auto_detect()
        _tools = KnowledgeTools(config)
    return _tools


@mcp.tool()
def get_component(name: str) -> str:
    """Get a component by name."""
    return json.dumps(get_tools().get_component(name), indent=2)


@mcp.tool()
def search_components(pattern: str) -> str:
    """Search components by regex pattern."""
    return json.dumps(get_tools().search_components(pattern), indent=2)


@mcp.tool()
def list_components_by_stereotype(stereotype: str) -> str:
    """List all components of a given stereotype (service, controller, etc.)."""
    return json.dumps(get_tools().list_components_by_stereotype(stereotype), indent=2)


@mcp.tool()
def get_relations_for(component_id: str) -> str:
    """Get all relations for a component."""
    return json.dumps(get_tools().get_relations_for(component_id), indent=2)


@mcp.tool()
def get_endpoints(path_pattern: str = "") -> str:
    """Get REST endpoints, optionally filtered by path pattern."""
    return json.dumps(get_tools().get_endpoints(path_pattern or None), indent=2)


@mcp.tool()
def get_architecture_summary() -> str:
    """Get high-level architecture summary."""
    return json.dumps(get_tools().get_architecture_summary(), indent=2)


@mcp.tool()
def get_statistics() -> str:
    """Get detailed knowledge base statistics."""
    return json.dumps(get_tools().get_statistics(), indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
