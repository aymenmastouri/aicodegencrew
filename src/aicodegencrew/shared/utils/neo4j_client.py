"""Neo4J Knowledge Graph client for architecture facts.

Exports architecture facts (components, interfaces, dependencies) as a
knowledge graph. All methods are no-op when NEO4J_URI is not set.

Env vars:
    NEO4J_URI: Neo4J bolt URI (e.g. bolt://localhost:7687). Empty = disabled.
    NEO4J_USER: Username (default: neo4j)
    NEO4J_PASSWORD: Password
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Neo4J graph database client for architecture knowledge graphs."""

    def __init__(self):
        self._driver = None
        self._uri = os.getenv("NEO4J_URI", "").strip()

        if not self._uri:
            return

        user = os.getenv("NEO4J_USER", "neo4j").strip()
        password = os.getenv("NEO4J_PASSWORD", "").strip()

        try:
            from neo4j import GraphDatabase

            self._driver = GraphDatabase.driver(self._uri, auth=(user, password))
            logger.info("[Neo4J] Connected to %s", self._uri)
        except ImportError:
            logger.warning("[Neo4J] neo4j package not installed — pip install neo4j")
        except Exception as exc:
            logger.warning("[Neo4J] Failed to connect: %s", exc)

    @property
    def enabled(self) -> bool:
        return self._driver is not None

    def health_check(self) -> bool:
        """Verify connectivity to Neo4J."""
        if not self._driver:
            return False
        try:
            self._driver.verify_connectivity()
            return True
        except Exception as exc:
            logger.warning("[Neo4J] Health check failed: %s", exc)
            return False

    def export_architecture_facts(self, facts: dict[str, Any]) -> None:
        """Export architecture facts dict as a knowledge graph.

        Creates:
            (:Component {name, stereotype, layer, module, file_path})
            (:Interface {name, type, path, method})
            (:Component)-[:DEPENDS_ON {type, evidence}]->(:Component)
            (:Component)-[:IMPLEMENTS]->(:Interface)
        """
        if not self._driver or not facts:
            return

        try:
            with self._driver.session() as session:
                # Export components
                components = facts.get("components", [])
                if isinstance(components, list):
                    for comp in components:
                        if not isinstance(comp, dict):
                            continue
                        session.run(
                            """
                            MERGE (c:Component {name: $name})
                            SET c.stereotype = $stereotype,
                                c.layer = $layer,
                                c.module = $module,
                                c.file_path = $file_path
                            """,
                            name=comp.get("name", "unknown"),
                            stereotype=comp.get("stereotype", ""),
                            layer=comp.get("layer", ""),
                            module=comp.get("module", ""),
                            file_path=comp.get("file_path", ""),
                        )

                # Export interfaces
                interfaces = facts.get("interfaces", [])
                if isinstance(interfaces, list):
                    for iface in interfaces:
                        if not isinstance(iface, dict):
                            continue
                        session.run(
                            """
                            MERGE (i:Interface {name: $name})
                            SET i.type = $type,
                                i.path = $path,
                                i.method = $method
                            """,
                            name=iface.get("name", "unknown"),
                            type=iface.get("type", ""),
                            path=iface.get("path", ""),
                            method=iface.get("method", ""),
                        )

                # Export dependencies
                dependencies = facts.get("dependencies", [])
                if isinstance(dependencies, list):
                    for dep in dependencies:
                        if not isinstance(dep, dict):
                            continue
                        session.run(
                            """
                            MATCH (a:Component {name: $source})
                            MATCH (b:Component {name: $target})
                            MERGE (a)-[r:DEPENDS_ON]->(b)
                            SET r.type = $type, r.evidence = $evidence
                            """,
                            source=dep.get("source", ""),
                            target=dep.get("target", ""),
                            type=dep.get("type", ""),
                            evidence=dep.get("evidence", ""),
                        )

                # Export component->interface implementations
                implementations = facts.get("implementations", [])
                if isinstance(implementations, list):
                    for impl in implementations:
                        if not isinstance(impl, dict):
                            continue
                        session.run(
                            """
                            MATCH (c:Component {name: $component})
                            MATCH (i:Interface {name: $interface})
                            MERGE (c)-[:IMPLEMENTS]->(i)
                            """,
                            component=impl.get("component", ""),
                            interface=impl.get("interface", ""),
                        )

                logger.info(
                    "[Neo4J] Exported %d components, %d interfaces, %d dependencies",
                    len(components) if isinstance(components, list) else 0,
                    len(interfaces) if isinstance(interfaces, list) else 0,
                    len(dependencies) if isinstance(dependencies, list) else 0,
                )
        except Exception as exc:
            logger.warning("[Neo4J] Export failed: %s", exc)

    def query_dependencies(self, component: str) -> list[dict[str, Any]]:
        """Query all dependencies of a component."""
        if not self._driver:
            return []

        try:
            with self._driver.session() as session:
                result = session.run(
                    """
                    MATCH (a:Component {name: $name})-[r:DEPENDS_ON]->(b:Component)
                    RETURN b.name AS target, r.type AS type, r.evidence AS evidence
                    """,
                    name=component,
                )
                return [dict(record) for record in result]
        except Exception as exc:
            logger.warning("[Neo4J] Query failed: %s", exc)
            return []

    def close(self) -> None:
        """Close the Neo4J driver connection."""
        if self._driver:
            try:
                self._driver.close()
            except Exception:
                pass
            self._driver = None
