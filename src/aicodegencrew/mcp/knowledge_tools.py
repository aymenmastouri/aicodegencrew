"""
Knowledge Tools - Core logic for querying Phase 1 architecture facts.

These tools solve the token limit problem by providing structured,
targeted queries instead of loading entire codebase into context.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class KnowledgeConfig:
    """Configuration for knowledge base location."""

    knowledge_path: Path

    @classmethod
    def from_env(cls, knowledge_dir: str | None = None) -> "KnowledgeConfig":
        """Create config from environment or default."""
        if knowledge_dir:
            path = Path(knowledge_dir)
        else:
            # Default to knowledge/extract in project root
            path = Path.cwd() / "knowledge" / "extract"
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
        with open(file_path, encoding="utf-8") as f:
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
                "components": [
                    {"id": c["id"], "name": c["name"], "stereotype": c.get("stereotype")} for c in matches[:20]
                ],
                "hint": "Multiple matches. Use more specific name or full ID.",
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
        return {"stereotype": stereotype, "count": len(matches), "components": matches}

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
        return {"layer": layer, "count": len(matches), "components": matches}

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
                matches.append(
                    {
                        "id": comp["id"],
                        "name": comp["name"],
                        "stereotype": comp.get("stereotype"),
                        "file": comp.get("file_paths", [""])[0] if comp.get("file_paths") else None,
                    }
                )

        return {
            "pattern": pattern,
            "count": len(matches),
            "components": matches[:50],  # Limit results
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
                outgoing.append(
                    {"to": rel["to"], "type": rel.get("type"), "to_name": self._get_component_name(rel["to"])}
                )
            if rel.get("to") == component_id:
                incoming.append(
                    {"from": rel["from"], "type": rel.get("type"), "from_name": self._get_component_name(rel["from"])}
                )

        return {
            "component_id": component_id,
            "outgoing": {"count": len(outgoing), "relations": outgoing},
            "incoming": {"count": len(incoming), "relations": incoming},
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

            graph["nodes"].append({"id": comp_id, "name": self._get_component_name(comp_id), "depth": current_depth})

            for rel in self.relations.get("relations", []):
                if rel.get("from") == comp_id:
                    graph["edges"].append({"from": comp_id, "to": rel["to"], "type": rel.get("type")})
                    traverse(rel["to"], current_depth + 1)

        traverse(component_id, 0)

        return {"component_id": component_id, "depth": depth, "graph": graph}

    def _get_component_name(self, component_id: str) -> str:
        """Helper to get component name from ID."""
        for comp in self.components.get("components", []):
            if comp.get("id") == component_id:
                return comp.get("name", component_id)
        return component_id.split(".")[-1]

    # ========== Interface Tools ==========

    def get_endpoints(self, path_pattern: str | None = None) -> dict:
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
            endpoints.append(
                {
                    "path": iface.get("path"),
                    "method": iface.get("method"),
                    "implemented_by": iface.get("implemented_by"),
                    "id": iface.get("id"),
                }
            )

        return {"filter": path_pattern, "count": len(endpoints), "endpoints": endpoints}

    def get_endpoint_by_path(self, path: str, method: str | None = None) -> dict:
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

        return {"component_id": component_id, "count": len(evidence_list), "evidence": evidence_list}

    # ========== Module Dimension Tools ==========

    def get_module_overview(self, module: str) -> dict:
        """
        Get complete overview of a module: all components, relations, and endpoints.

        Args:
            module: Module name (e.g., "workflow", "deed", "user")
        """
        module_lower = module.lower()

        # Find all components in this module
        components = [
            {"id": c["id"], "name": c["name"], "stereotype": c.get("stereotype"), "layer": c.get("layer")}
            for c in self.components.get("components", [])
            if module_lower in c.get("module", "").lower() or module_lower in c.get("name", "").lower()
        ]

        component_ids = {c["id"] for c in components}

        # Find internal relations (within module)
        internal_relations = [
            {"from": r["from"], "to": r["to"], "type": r.get("type")}
            for r in self.relations.get("relations", [])
            if r.get("from") in component_ids and r.get("to") in component_ids
        ]

        # Find external relations (crossing module boundary)
        external_relations = [
            {
                "from": r["from"],
                "to": r["to"],
                "type": r.get("type"),
                "direction": "outgoing" if r.get("from") in component_ids else "incoming",
            }
            for r in self.relations.get("relations", [])
            if (r.get("from") in component_ids) != (r.get("to") in component_ids)
        ]

        # Find endpoints for this module
        endpoints = [
            {"path": i.get("path"), "method": i.get("method")}
            for i in self.interfaces.get("interfaces", [])
            if i.get("type") == "rest_endpoint"
            and any(cid in str(i.get("implemented_by", "")) for cid in component_ids)
        ]

        return {
            "module": module,
            "components": {"count": len(components), "items": components},
            "internal_relations": {"count": len(internal_relations), "items": internal_relations[:50]},
            "external_relations": {"count": len(external_relations), "items": external_relations[:50]},
            "endpoints": {"count": len(endpoints), "items": endpoints},
        }

    def list_modules(self) -> dict:
        """
        List all modules/packages in the codebase with component counts.
        """
        modules = {}
        for comp in self.components.get("components", []):
            module = comp.get("module", "unknown")
            if module not in modules:
                modules[module] = {"count": 0, "stereotypes": {}}
            modules[module]["count"] += 1
            stereo = comp.get("stereotype", "unknown")
            modules[module]["stereotypes"][stereo] = modules[module]["stereotypes"].get(stereo, 0) + 1

        return {
            "total_modules": len(modules),
            "modules": [
                {"name": name, "component_count": data["count"], "stereotypes": data["stereotypes"]}
                for name, data in sorted(modules.items(), key=lambda x: -x[1]["count"])
            ],
        }

    # ========== Dependency Dimension Tools ==========

    def get_dependencies_tree(self, component_id: str, depth: int = 3, direction: str = "outgoing") -> dict:
        """
        Get full dependency tree for a component.

        Args:
            component_id: Component ID or name
            depth: How deep to traverse (default: 3)
            direction: "outgoing" (what I depend on), "incoming" (what depends on me), or "both"
        """
        # Resolve component
        if not component_id.startswith("component."):
            result = self.get_component(component_id)
            if "error" in result:
                return result
            if "component" in result:
                component_id = result["component"]["id"]
            else:
                return {"error": "Ambiguous component name. Please use full ID."}

        visited = set()
        tree = {"root": component_id, "root_name": self._get_component_name(component_id), "children": []}

        def build_tree(comp_id: str, current_depth: int) -> list:
            if current_depth > depth or comp_id in visited:
                return []
            visited.add(comp_id)

            children = []
            for rel in self.relations.get("relations", []):
                target = None
                if direction in ("outgoing", "both") and rel.get("from") == comp_id:
                    target = rel["to"]
                elif direction in ("incoming", "both") and rel.get("to") == comp_id:
                    target = rel["from"]

                if target and target not in visited:
                    children.append(
                        {
                            "id": target,
                            "name": self._get_component_name(target),
                            "relation_type": rel.get("type"),
                            "children": build_tree(target, current_depth + 1),
                        }
                    )
            return children

        tree["children"] = build_tree(component_id, 1)
        tree["total_dependencies"] = len(visited) - 1

        return tree

    def get_circular_dependencies(self) -> dict:
        """
        Find potential circular dependencies in the codebase.
        """
        # Build adjacency list
        adj = {}
        for rel in self.relations.get("relations", []):
            from_id = rel.get("from")
            to_id = rel.get("to")
            if from_id not in adj:
                adj[from_id] = []
            adj[from_id].append(to_id)

        cycles = []
        visited = set()
        path = []
        path_set = set()

        def dfs(node):
            if node in path_set:
                # Found cycle
                cycle_start = path.index(node)
                cycle = [*path[cycle_start:], node]
                cycles.append([self._get_component_name(n) for n in cycle])
                return
            if node in visited:
                return

            visited.add(node)
            path.append(node)
            path_set.add(node)

            for neighbor in adj.get(node, []):
                dfs(neighbor)

            path.pop()
            path_set.remove(node)

        for node in adj:
            if node not in visited:
                dfs(node)

        return {
            "cycles_found": len(cycles),
            "cycles": cycles[:20],  # Limit output
        }

    # ========== Data Dimension Tools ==========

    def get_entities(self) -> dict:
        """
        Get all entity/domain model classes.
        """
        entities = [
            {
                "id": c["id"],
                "name": c["name"],
                "module": c.get("module"),
                "file": c.get("file_paths", [""])[0] if c.get("file_paths") else None,
            }
            for c in self.components.get("components", [])
            if c.get("stereotype", "").lower() in ("entity", "model", "domain", "aggregate", "value_object")
        ]

        return {"count": len(entities), "entities": entities}

    def get_entity_relationships(self, entity_name: str) -> dict:
        """
        Get all relationships for an entity (JPA relations, references, etc.).

        Args:
            entity_name: Entity name (e.g., "DeedEntry", "Workflow")
        """
        result = self.get_component(entity_name)
        if "error" in result:
            return result
        if "component" not in result:
            return {"error": "Ambiguous entity name."}

        entity = result["component"]
        entity_id = entity["id"]

        # Get relations
        relations_result = self.get_relations_for(entity_id)

        # Categorize by relation type
        jpa_relations = []
        other_relations = []

        for rel in relations_result.get("outgoing", {}).get("relations", []):
            if rel.get("type") in ("one_to_many", "many_to_one", "one_to_one", "many_to_many"):
                jpa_relations.append(rel)
            else:
                other_relations.append(rel)

        return {
            "entity": {"id": entity_id, "name": entity["name"]},
            "jpa_relations": jpa_relations,
            "other_relations": other_relations,
            "referenced_by": relations_result.get("incoming", {}).get("relations", []),
        }

    # ========== API Dimension Tools ==========

    def get_api_overview(self) -> dict:
        """
        Get complete API overview: all endpoints grouped by controller/resource.
        """
        endpoints = self.interfaces.get("interfaces", [])
        rest_endpoints = [e for e in endpoints if e.get("type") == "rest_endpoint"]

        # Group by base path (first 2 segments)
        by_resource = {}
        for ep in rest_endpoints:
            path = ep.get("path", "")
            parts = path.strip("/").split("/")
            resource = "/" + "/".join(parts[:2]) if len(parts) >= 2 else path

            if resource not in by_resource:
                by_resource[resource] = []
            by_resource[resource].append(
                {"path": path, "method": ep.get("method"), "implemented_by": ep.get("implemented_by")}
            )

        return {
            "total_endpoints": len(rest_endpoints),
            "resources": [
                {"base_path": resource, "endpoint_count": len(eps), "endpoints": eps}
                for resource, eps in sorted(by_resource.items())
            ],
        }

    def get_controllers_with_endpoints(self) -> dict:
        """
        Get all controllers with their endpoints.
        """
        controllers = [
            c
            for c in self.components.get("components", [])
            if c.get("stereotype", "").lower() in ("controller", "rest_controller", "resource")
        ]

        result = []
        for ctrl in controllers:
            ctrl_endpoints = [
                {"path": e.get("path"), "method": e.get("method")}
                for e in self.interfaces.get("interfaces", [])
                if e.get("type") == "rest_endpoint" and ctrl["id"] in str(e.get("implemented_by", ""))
            ]
            result.append({"controller": ctrl["name"], "id": ctrl["id"], "endpoints": ctrl_endpoints})

        return {"controller_count": len(result), "controllers": result}

    # ========== Batch Query Tool ==========

    def batch_query(self, queries: list) -> dict:
        """
        Execute multiple queries in one call to minimize token usage.

        Args:
            queries: List of query dicts, each with 'tool' and 'args'
                    e.g., [{"tool": "get_component", "args": {"name": "WorkflowService"}},
                           {"tool": "get_relations_for", "args": {"component_id": "..."}}]
        """
        results = []
        tool_map = {
            "get_component": self.get_component,
            "get_component_by_id": self.get_component_by_id,
            "list_components_by_stereotype": self.list_components_by_stereotype,
            "list_components_by_layer": self.list_components_by_layer,
            "search_components": self.search_components,
            "get_relations_for": self.get_relations_for,
            "get_call_graph": self.get_call_graph,
            "get_dependencies_tree": self.get_dependencies_tree,
            "get_endpoints": self.get_endpoints,
            "get_endpoint_by_path": self.get_endpoint_by_path,
            "get_routes": self.get_routes,
            "get_evidence": self.get_evidence,
            "get_evidence_for_component": self.get_evidence_for_component,
            "get_module_overview": self.get_module_overview,
            "list_modules": self.list_modules,
            "get_entities": self.get_entities,
            "get_entity_relationships": self.get_entity_relationships,
            "get_api_overview": self.get_api_overview,
            "get_controllers_with_endpoints": self.get_controllers_with_endpoints,
            "get_architecture_summary": self.get_architecture_summary,
            "get_statistics": self.get_statistics,
        }

        for i, query in enumerate(queries):
            tool_name = query.get("tool")
            args = query.get("args", {})

            if tool_name not in tool_map:
                results.append({"query_index": i, "error": f"Unknown tool: {tool_name}"})
                continue

            try:
                result = tool_map[tool_name](**args)
                results.append({"query_index": i, "tool": tool_name, "result": result})
            except Exception as e:
                results.append({"query_index": i, "tool": tool_name, "error": str(e)})

        return {"queries_executed": len(queries), "results": results}

    # ========== Summary Tools ==========

    def get_architecture_summary(self) -> dict:
        """Get high-level architecture summary."""
        return {
            "components": {
                "total": self.components.get("total", 0),
                "by_layer": self.components.get("by_layer", {}),
                "by_stereotype": self.components.get("by_stereotype", {}),
            },
            "relations": {"total": self.relations.get("total", 0), "by_type": self.relations.get("by_type", {})},
            "interfaces": {"total": self.interfaces.get("total", 0), "by_type": self.interfaces.get("by_type", {})},
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
                "stereotypes": list(comp_data.get("by_stereotype", {}).keys()),
            },
            "relations": {"total": rel_data.get("total", 0), "types": list(rel_data.get("by_type", {}).keys())},
            "interfaces": {
                "total": iface_data.get("total", 0),
                "rest_endpoints": iface_data.get("by_type", {}).get("rest_endpoint", {}).get("count", 0),
                "routes": iface_data.get("by_type", {}).get("route", {}).get("count", 0),
            },
        }
