"""
Facts Query Tool - Architecture Facts Retrieval

CrewAI Best Practice: Agent queries only relevant facts instead of full context.
This prevents token limit overflow by using smart filtering.

ARCHITECTURE DECISION:
- Uses Dimension Files instead of monolithic architecture_facts.json
- Each category loads only its own file (lazy loading)
- Reduces memory usage by 80-90% for targeted queries

Dimension Files:
- components.json (438 KB) - All components
- relations.json (28 KB) - Component relations
- interfaces.json (37 KB) - API interfaces
- containers.json (6 KB) - System containers
- data_model.json (64 KB) - Entities and data
- runtime.json (47 KB) - Profiles, configs
- evidence_map.json (284 KB) - Source evidence

Usage:
- query_facts(category="components", stereotype="controller")
- query_facts(category="relations", limit=20)

Relevance Sorting:
- Components are sorted by architectural layer importance
- Backend: controller -> service -> repository -> entity -> rest
- Frontend: component -> module -> service -> pipe -> directive -> rest
"""

import json
from pathlib import Path
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

from ..utils.logger import setup_logger
from ..utils.token_budget import truncate_response

logger = setup_logger(__name__)

# Priority for sorting (lower = more important, shown first)
DEFAULT_PRIORITY = 10

# Mapping category -> dimension file
DIMENSION_FILES = {
    "components": "components.json",
    "relations": "relations.json",
    "interfaces": "interfaces.json",
    "containers": "containers.json",
    "data_model": "data_model.json",
    "runtime": "runtime.json",
    "evidence": "evidence_map.json",
    "system": "system.json",
}


class FactsQueryInput(BaseModel):
    """Input schema for FactsQueryTool."""

    category: str = Field(
        default="all",
        description="Category to query: 'components', 'relations', 'interfaces', 'containers', 'data_model', 'all'",
    )
    query: str = Field(default="", description="Search text to filter results (searches in name, package, description)")
    stereotype: str = Field(
        default="",
        description="Stereotype filter: 'controller', 'service', 'repository', 'entity', 'design_pattern', 'architecture_style'",
    )
    container: str = Field(default="", description="Container filter: filter by container name")
    limit: int = Field(default=50, description="Maximum number of results per page (default 50, max 100)")
    offset: int = Field(default=0, description="Skip first N results for pagination (use with limit for large repos)")


class FactsQueryTool(BaseTool):
    """
    Tool for querying architecture facts with filtering.

    ARCHITECTURE: Uses Dimension Files (lazy loading)
    - Only loads the specific dimension file needed
    - components.json, relations.json, interfaces.json, etc.
    - Reduces memory usage by 80-90% compared to monolith

    CrewAI Best Practice:
    - Agents query only what they need
    - Reduces token usage significantly
    - Smart filtering by category/stereotype/text

    Usage Examples:
    1. query_facts(category="components", stereotype="controller")
    2. query_facts(category="relations", query="OrderService")
    3. query_facts(category="containers")
    """

    name: str = "query_facts"
    description: str = (
        "Query architecture facts from Phase 1 dimension files. "
        "Filter by category (components/relations/interfaces/containers/data_model) and stereotype. "
        "Use this to discover architecture elements - don't assume or hardcode!"
    )
    args_schema: type[BaseModel] = FactsQueryInput

    # Configuration - base directory for dimension files
    facts_dir: str = "knowledge/extract"

    # Cache per dimension (lazy loading) — PrivateAttr ensures each instance gets its own dict
    _dimension_cache: dict[str, Any] = PrivateAttr(default_factory=dict)

    def __init__(self, facts_dir: str = None, **kwargs):
        """Initialize with optional facts directory override."""
        super().__init__(**kwargs)
        if facts_dir:
            self.facts_dir = facts_dir
        self._dimension_cache = {}

    def _load_dimension(self, category: str) -> Any:
        """Load a specific dimension file with caching.

        This is the key optimization: only load what's needed.
        """
        if category in self._dimension_cache:
            return self._dimension_cache[category]

        filename = DIMENSION_FILES.get(category)
        if not filename:
            logger.warning(f"Unknown dimension category: {category}")
            return []

        path = Path(self.facts_dir) / filename
        if not path.exists():
            logger.warning(f"Dimension file not found: {path}")
            return []

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        # Handle different file structures
        if isinstance(data, dict):
            # data_model.json has complex structure - return as-is
            if category == "data_model":
                self._dimension_cache[category] = data
                logger.info(
                    f"Loaded dimension {category}: entities={data.get('entities', {}).get('total', 0)}, tables={data.get('tables', {}).get('total', 0)}"
                )
                return data

            # evidence_map.json is a dict of evidence entries
            if category == "evidence":
                self._dimension_cache[category] = data
                logger.info(f"Loaded dimension {category}: {len(data)} evidence entries")
                return data

            # Files like components.json have {"components": [...]}
            if category in data:
                data = data[category]
            elif "items" in data:
                data = data["items"]

        self._dimension_cache[category] = data
        logger.info(f"Loaded dimension {category}: {len(data) if isinstance(data, list) else 'dict'} items")
        return data

    def _run(
        self,
        category: str = "all",
        query: str = "",
        stereotype: str = "",
        container: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> str:
        """
        Execute facts query with pagination support.

        Uses lazy loading - only loads dimension files that are needed.

        Args:
            category: Filter by category (components/relations/interfaces/containers/data_model/all)
            query: Search text for filtering
            stereotype: Filter by component stereotype
            container: Filter by container name
            limit: Max results per page (max 100)
            offset: Skip first N results for pagination

        Returns:
            JSON string with matching facts and pagination info
        """
        try:
            # Cap limit to prevent context overflow
            limit = min(limit, 100)
            offset = max(offset, 0)

            results = {}
            query_lower = query.lower()
            container_lower = container.lower() if container else ""

            # Track totals for pagination info
            pagination_info = {}

            # Determine which categories to query
            if category == "all":
                categories_to_query = ["components", "relations", "interfaces", "containers"]
            else:
                categories_to_query = [category]

            # Query each category (lazy loads only what's needed)
            for cat in categories_to_query:
                if cat == "components":
                    all_components = self._load_dimension("components")
                    components, total_matching = self._filter_components(
                        all_components, query_lower, stereotype, container_lower, limit, offset
                    )
                    if components:
                        results["components"] = components
                    pagination_info["components"] = {
                        "returned": len(components),
                        "total_matching": total_matching,
                        "offset": offset,
                        "has_more": (offset + len(components)) < total_matching,
                    }

                elif cat == "relations":
                    all_relations = self._load_dimension("relations")
                    relations, total_rel = self._filter_relations(all_relations, query_lower, limit, offset)
                    if relations:
                        results["relations"] = relations
                    pagination_info["relations"] = {
                        "returned": len(relations),
                        "total_matching": total_rel,
                        "has_more": (offset + len(relations)) < total_rel,
                    }

                elif cat == "interfaces":
                    interfaces = self._filter_items(self._load_dimension("interfaces"), query_lower, limit)
                    if interfaces:
                        results["interfaces"] = interfaces

                elif cat == "containers":
                    containers = self._filter_items(self._load_dimension("containers"), query_lower, limit)
                    if containers:
                        results["containers"] = containers

                elif cat == "data_model":
                    dm = self._load_dimension("data_model")
                    # data_model has complex structure: entities, tables, migrations
                    data_model_results = self._filter_data_model(dm, query_lower, limit)
                    if data_model_results:
                        results["data_model"] = data_model_results

            # Build output with summary and pagination
            total_items = sum(len(v) if isinstance(v, list) else 1 for v in results.values())
            output = {
                "query_params": {
                    "category": category,
                    "search": query,
                    "stereotype": stereotype,
                    "container": container,
                    "limit": limit,
                    "offset": offset,
                },
                "result_count": total_items,
                "pagination": pagination_info,
                "results": results,
            }

            # TOKEN BUDGET: Truncate if too large
            output_str = json.dumps(output, indent=2, ensure_ascii=False)
            output_str = truncate_response(output_str, hint="use offset/limit for pagination")

            return output_str

        except Exception as e:
            logger.error(f"Facts query error: {e}")
            return json.dumps({"error": str(e), "results": {}})

    def _filter_components(
        self,
        components: list[dict[str, Any]],
        query: str,
        stereotype: str,
        container_filter: str,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
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

        # Sort by layer relevance before pagination
        matching = self._sort_by_relevance(matching)

        # Apply pagination
        paginated = matching[offset : offset + limit]

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
            filtered.append(
                {
                    "name": c.get("name"),
                    "stereotype": c.get("stereotype"),
                    "package": package,
                    "container": c.get("container"),
                    "description": (c.get("description", "") or "")[:100],  # Truncate
                }
            )

        return filtered, total_matching

    def _filter_relations(
        self, relations: list[dict[str, Any]], query: str, limit: int, offset: int
    ) -> tuple[list[dict[str, Any]], int]:
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
        paginated = matching[offset : offset + limit]

        # Transform to output format
        filtered = []
        for r in paginated:
            filtered.append(
                {
                    "source": r.get("from", ""),
                    "target": r.get("to", ""),
                    "type": r.get("type"),
                    "description": (r.get("description", "") or "")[:80],
                }
            )

        return filtered, total_matching

    def _filter_items(self, items: list[dict[str, Any]], query: str, limit: int) -> list[dict[str, Any]]:
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

    def _filter_data_model(self, data_model: dict[str, Any], query: str, limit: int) -> dict[str, Any]:
        """Filter data model (entities, tables, migrations).

        Returns structured data model with filtered items.
        """
        result = {}

        # Filter entities
        entities_data = data_model.get("entities", {})
        entities = entities_data.get("items", [])
        filtered_entities = []
        for e in entities:
            if query:
                searchable = f"{e.get('name', '')} {e.get('module', '')}".lower()
                if query not in searchable:
                    continue
            filtered_entities.append(e)
            if len(filtered_entities) >= limit:
                break

        if filtered_entities:
            result["entities"] = {
                "total": entities_data.get("total", len(entities)),
                "returned": len(filtered_entities),
                "items": filtered_entities,
            }

        # Filter tables
        tables_data = data_model.get("tables", {})
        tables = tables_data.get("items", [])
        filtered_tables = []
        for t in tables:
            if query:
                searchable = f"{t.get('name', '')}".lower()
                if query not in searchable:
                    continue
            filtered_tables.append(t)
            if len(filtered_tables) >= limit:
                break

        if filtered_tables:
            result["tables"] = {
                "total": tables_data.get("total", len(tables)),
                "returned": len(filtered_tables),
                "items": filtered_tables,
            }

        # Filter migrations
        migrations_data = data_model.get("migrations", {})
        migrations = migrations_data.get("items", [])
        filtered_migrations = []
        for m in migrations:
            if query:
                searchable = f"{m.get('name', '')}".lower()
                if query not in searchable:
                    continue
            filtered_migrations.append(m)
            if len(filtered_migrations) >= limit:
                break

        if filtered_migrations:
            result["migrations"] = {
                "total": migrations_data.get("total", len(migrations)),
                "returned": len(filtered_migrations),
                "items": filtered_migrations,
            }

        # Include relationships if present
        relationships = data_model.get("relationships", [])
        if relationships:
            result["relationships"] = relationships[:limit]

        return result

    def _sort_by_relevance(self, components: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Sort components by architectural layer relevance.

        Priority is determined dynamically by:
        1. Class name suffix patterns (Controller, Service, Repository, etc.)
        2. Package name patterns (controller, service, repository, etc.)
        3. Stereotype as fallback

        This ensures agents see architecturally important components first.
        """

        def get_priority(component: dict[str, Any]) -> tuple:
            name = component.get("name", "").lower()
            package = (component.get("package") or component.get("module") or "").lower()
            component.get("stereotype", "").lower()

            layer_priority = DEFAULT_PRIORITY

            # Check class name patterns (most reliable)
            # Backend patterns
            if (
                name.endswith("controller")
                or name.endswith("resource")
                or name.endswith("restcontroller")
                or name.endswith("restservice")
            ):
                layer_priority = 1
            elif name.endswith("service") or name.endswith("serviceimpl") or name.endswith("facade"):
                layer_priority = 2
            elif (
                name.endswith("repository")
                or name.endswith("repositoryimpl")
                or name.endswith("dao")
                or name.endswith("daoimpl")
            ):
                layer_priority = 3
            elif name.endswith("entity") or name.endswith("model") or name.endswith("dto"):
                layer_priority = 4
            elif name.endswith("mapper") or name.endswith("validator") or name.endswith("converter"):
                layer_priority = 5
            # Frontend patterns
            elif name.endswith("component") or name.endswith("page"):
                layer_priority = 1
            elif name.endswith("module") or name.endswith("store"):
                layer_priority = 2
            elif name.endswith("guard") or name.endswith("resolver") or name.endswith("interceptor"):
                layer_priority = 3
            elif name.endswith("pipe") or name.endswith("directive"):
                layer_priority = 4

            # Check package patterns if no name match
            if layer_priority == DEFAULT_PRIORITY:
                if any(p in package for p in ["controller", "rest", "adapter", "web", "api"]):
                    layer_priority = 1
                elif any(p in package for p in ["service", "logic", "business", "usecase"]):
                    layer_priority = 2
                elif any(p in package for p in ["repository", "dataaccess", "dao", "persistence"]):
                    layer_priority = 3
                elif any(p in package for p in ["entity", "domain", "model"]):
                    layer_priority = 4
                elif any(p in package for p in ["component", "page", "container"]):
                    layer_priority = 1

            # Secondary sort: alphabetically by name for consistency
            return (layer_priority, name)

        return sorted(components, key=get_priority)
