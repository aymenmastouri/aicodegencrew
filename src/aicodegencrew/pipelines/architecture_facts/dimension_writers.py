"""
Dimension Writers - Write canonical model to separate JSON files.

Each writer is responsible for one architectural dimension:
- system.json
- containers.json
- components.json
- interfaces.json
- data_model.json
- runtime.json
- infrastructure.json
- evidence_map.json

These files come from the Architecture Model Builder, NOT directly from collectors.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ...shared.utils.logger import logger
from .model_builder import ArchitectureLayer, ArchitectureModel, CanonicalComponent


class DimensionWriterBase:
    """Base class for dimension writers."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _write_json(self, filename: str, data: Any) -> Path:
        """Write data to JSON file."""
        path = self.output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"[DimensionWriter] Written: {filename} ({path.stat().st_size / 1024:.1f} KB)")
        return path


class SystemWriter(DimensionWriterBase):
    """Writes system.json - high-level system and domain boundaries."""

    def write(self, model: ArchitectureModel) -> Path:
        """Write system.json."""
        # Detect bounded contexts from component modules
        bounded_contexts = self._detect_bounded_contexts(model)

        # Detect subsystems from containers
        subsystems = [
            {
                "id": c.id,
                "name": c.name,
                "technology": c.technology,
                "category": c.category,
            }
            for c in model.containers.values()
        ]

        data = {
            "id": "system",
            "name": model.system_name,
            "description": f"Architecture model for {model.system_name}",
            "generated_at": datetime.now().isoformat(),
            "bounded_contexts": bounded_contexts,
            "subsystems": subsystems,
            "statistics": model.get_statistics(),
        }

        return self._write_json("system.json", data)

    def _detect_bounded_contexts(self, model: ArchitectureModel) -> list[dict]:
        """Detect bounded contexts from component modules."""
        contexts: dict[str, dict] = {}

        for comp in model.components.values():
            if not comp.module:
                continue

            # Extract first significant module part as context
            parts = comp.module.split("_")
            if parts:
                context_name = parts[0]

                if context_name not in contexts:
                    contexts[context_name] = {
                        "name": context_name,
                        "components": [],
                        "stereotypes": set(),
                    }

                contexts[context_name]["components"].append(comp.id)
                contexts[context_name]["stereotypes"].add(comp.stereotype)

        # Convert to list and clean up
        return [
            {
                "name": ctx["name"],
                "component_count": len(ctx["components"]),
                "stereotypes": list(ctx["stereotypes"]),
            }
            for ctx in contexts.values()
            if len(ctx["components"]) >= 2  # Only contexts with multiple components
        ]


class ContainersWriter(DimensionWriterBase):
    """Writes containers.json - deployable units."""

    def write(self, model: ArchitectureModel) -> Path:
        """Write containers.json."""
        containers = [c.to_dict() for c in model.containers.values()]

        # Add component counts per container
        for container in containers:
            container_id = container["id"]
            components = model.get_components_for_container(container_id)
            container["component_count"] = len(components)
            container["layer_distribution"] = self._get_layer_distribution(components)

        data = {
            "total": len(containers),
            "containers": containers,
        }

        return self._write_json("containers.json", data)

    def _get_layer_distribution(self, components: list[CanonicalComponent]) -> dict[str, int]:
        """Get distribution of components by layer."""
        distribution = {}
        for comp in components:
            distribution[comp.layer] = distribution.get(comp.layer, 0) + 1
        return distribution


class ComponentsWriter(DimensionWriterBase):
    """Writes components.json - internal structure per module."""

    def write(self, model: ArchitectureModel) -> Path:
        """Write components.json."""
        components = [c.to_dict() for c in model.components.values()]

        # Group by layer
        by_layer = {}
        for layer in ArchitectureLayer:
            layer_components = model.get_components_by_layer(layer.value)
            if layer_components:
                by_layer[layer.value] = {
                    "count": len(layer_components),
                    "stereotypes": list(set(c.stereotype for c in layer_components)),
                }

        # Group by stereotype
        by_stereotype = {}
        for comp in model.components.values():
            if comp.stereotype not in by_stereotype:
                by_stereotype[comp.stereotype] = 0
            by_stereotype[comp.stereotype] += 1

        data = {
            "total": len(components),
            "by_layer": by_layer,
            "by_stereotype": by_stereotype,
            "components": components,
        }

        return self._write_json("components.json", data)


class InterfacesWriter(DimensionWriterBase):
    """Writes interfaces.json - all technical entry points."""

    def write(self, model: ArchitectureModel) -> Path:
        """Write interfaces.json."""
        interfaces = [i.to_dict() for i in model.interfaces.values()]

        # Group by type
        by_type = {}
        for iface in model.interfaces.values():
            iface_type = iface.type
            if iface_type not in by_type:
                by_type[iface_type] = {"count": 0, "methods": {}}
            by_type[iface_type]["count"] += 1

            if iface.method:
                by_type[iface_type]["methods"][iface.method] = by_type[iface_type]["methods"].get(iface.method, 0) + 1

        data = {
            "total": len(interfaces),
            "by_type": by_type,
            "interfaces": interfaces,
        }

        return self._write_json("interfaces.json", data)


class DataModelWriter(DimensionWriterBase):
    """Writes data_model.json - entities, tables, relationships."""

    def write(self, model: ArchitectureModel) -> Path:
        """Write data_model.json."""
        # Get entities (domain layer)
        entities = model.get_components_by_stereotype("entity")

        # Get database-related components
        db_migrations = [
            c
            for c in model.components.values()
            if c.stereotype in ("database_migration", "database_schema", "sql_script")
        ]

        # Get database tables - either from stereotype or extract from sql_scripts
        db_tables = model.get_components_by_stereotype("database_table")

        # Also extract table names from sql_script components metadata
        extracted_tables = self._extract_tables_from_migrations(model, db_migrations)

        # Get repository components for relationship hints
        model.get_components_by_stereotype("repository")

        # Extract entity-repository relationships
        entity_relations = []
        for rel in model.relations:
            from_comp = model.components.get(rel.from_id)
            to_comp = model.components.get(rel.to_id)
            if from_comp and to_comp:
                if from_comp.stereotype == "repository" and to_comp.stereotype == "entity":
                    entity_relations.append(
                        {
                            "repository": from_comp.name,
                            "entity": to_comp.name,
                        }
                    )

        # Combine explicit tables and extracted tables
        all_tables = []
        seen_tables = set()

        # Add explicit database_table components
        for t in db_tables:
            if t.name not in seen_tables:
                all_tables.append(
                    {
                        "id": t.id,
                        "name": t.name,
                        "source": "explicit",
                        "file_path": t.file_paths[0] if t.file_paths else None,
                    }
                )
                seen_tables.add(t.name)

        # Add extracted tables from migrations
        for table_info in extracted_tables:
            if table_info["name"] not in seen_tables:
                all_tables.append(table_info)
                seen_tables.add(table_info["name"])

        data = {
            "entities": {
                "total": len(entities),
                "items": [
                    {
                        "id": e.id,
                        "name": e.name,
                        "module": e.module,
                        "file_path": e.file_paths[0] if e.file_paths else None,
                    }
                    for e in entities
                ],
            },
            "tables": {
                "total": len(all_tables),
                "items": all_tables,
            },
            "migrations": {
                "total": len(db_migrations),
                "items": [
                    {
                        "id": m.id,
                        "name": m.name,
                        "stereotype": m.stereotype,
                        "file_path": m.file_paths[0] if m.file_paths else None,
                    }
                    for m in db_migrations
                ],
            },
            "relationships": entity_relations,
        }

        return self._write_json("data_model.json", data)

    def _extract_tables_from_migrations(self, model: ArchitectureModel, migrations: list) -> list[dict]:
        """Extract table names from SQL migration scripts."""
        import re
        from pathlib import Path

        tables = []
        seen = set()

        for m in migrations:
            if not m.file_paths:
                continue

            file_path = Path(m.file_paths[0])
            # Try to read the SQL file
            full_path = self.output_dir.parent.parent.parent / file_path

            if not full_path.exists():
                # Try relative to model's evidence paths
                for ev_id in m.evidence_ids:
                    ev = model.evidence.get(ev_id)
                    if ev:
                        full_path = self.output_dir.parent.parent.parent / ev.get("path", "")
                        if full_path.exists():
                            break

            if full_path.exists() and full_path.suffix.lower() == ".sql":
                try:
                    content = full_path.read_text(encoding="utf-8", errors="ignore")
                    # Extract table names from CREATE TABLE, ALTER TABLE, INSERT INTO
                    table_matches = re.findall(
                        r'(?:CREATE\s+TABLE|ALTER\s+TABLE|INSERT\s+INTO)\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"\']?(\w+)[`"\']?',
                        content,
                        re.IGNORECASE,
                    )
                    for table_name in table_matches:
                        if table_name.lower() not in seen and not table_name.lower().startswith(("temp_", "tmp_")):
                            tables.append(
                                {
                                    "name": table_name,
                                    "source": "migration",
                                    "migration_file": str(file_path),
                                }
                            )
                            seen.add(table_name.lower())
                except Exception:
                    pass

        return tables


class RuntimeWriter(DimensionWriterBase):
    """Writes runtime.json - dynamic behavior."""

    def write(self, model: ArchitectureModel, endpoint_flows: list[dict] = None) -> Path:
        """Write runtime.json."""
        # Get scheduler components
        schedulers = [
            c for c in model.components.values() if "scheduler" in c.stereotype.lower() or "scheduled" in c.name.lower()
        ]

        # Get async components
        async_components = [
            c for c in model.components.values() if "async" in c.stereotype.lower() or "async" in c.name.lower()
        ]

        data = {
            "endpoint_flows": endpoint_flows or [],
            "schedulers": [
                {
                    "id": s.id,
                    "name": s.name,
                    "file_path": s.file_paths[0] if s.file_paths else None,
                }
                for s in schedulers
            ],
            "async_processors": [
                {
                    "id": a.id,
                    "name": a.name,
                }
                for a in async_components
            ],
        }

        return self._write_json("runtime.json", data)


class InfrastructureWriter(DimensionWriterBase):
    """Writes infrastructure.json - operational context."""

    def write(self, model: ArchitectureModel) -> Path:
        """Write infrastructure.json."""
        # Get infrastructure components by layer OR by stereotype
        infra_components = model.get_components_by_layer(ArchitectureLayer.INFRASTRUCTURE.value)

        # Also include infra stereotypes that might not have correct layer assigned
        infra_stereotypes = {
            "dockerfile",
            "compose_service",
            "k8s_deployment",
            "k8s_service",
            "deployment",
            "k8s-service",
            "ingress",
            "configmap",
            "helm-chart",
            "ci_pipeline",
            "gitlab-ci",
            "github-actions",
            "jenkins",
        }
        for comp in model.components.values():
            if comp.stereotype in infra_stereotypes and comp not in infra_components:
                infra_components.append(comp)

        # Categorize
        docker = [c for c in infra_components if c.stereotype in ("dockerfile", "compose_service")]
        kubernetes = [
            c
            for c in infra_components
            if c.stereotype
            in ("deployment", "k8s-service", "k8s_deployment", "k8s_service", "ingress", "configmap", "helm-chart")
        ]
        ci_cd = [
            c
            for c in infra_components
            if c.stereotype in ("ci_pipeline", "gitlab-ci", "github-actions", "jenkins", "azure-devops", "circleci")
        ]
        config = [c for c in infra_components if c.stereotype == "configuration"]

        data = {
            "docker": {
                "total": len(docker),
                "items": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "file_path": c.file_paths[0] if c.file_paths else None,
                        "stereotype": c.stereotype,
                    }
                    for c in docker
                ],
            },
            "kubernetes": {
                "total": len(kubernetes),
                "items": [{"id": c.id, "name": c.name, "stereotype": c.stereotype} for c in kubernetes],
            },
            "ci_cd": {
                "total": len(ci_cd),
                "items": [{"id": c.id, "name": c.name, "stereotype": c.stereotype} for c in ci_cd],
            },
            "configuration": {
                "total": len(config),
                "items": [{"id": c.id, "name": c.name} for c in config],
            },
        }

        return self._write_json("infrastructure.json", data)


class EvidenceWriter(DimensionWriterBase):
    """Writes evidence_map.json - traceability."""

    def write(self, model: ArchitectureModel) -> Path:
        """Write evidence_map.json."""
        # Evidence is already in dict format
        data = {
            "total": len(model.evidence),
            "evidence": model.evidence,
        }

        return self._write_json("evidence_map.json", data)


class RelationsWriter(DimensionWriterBase):
    """Writes relations.json - component dependencies."""

    def write(self, model: ArchitectureModel) -> Path:
        """Write relations.json."""
        relations = [r.to_dict() for r in model.relations]

        # Group by type
        by_type = {}
        for rel in model.relations:
            by_type[rel.type] = by_type.get(rel.type, 0) + 1

        data = {
            "total": len(relations),
            "by_type": by_type,
            "relations": relations,
        }

        return self._write_json("relations.json", data)


class DependenciesWriter(DimensionWriterBase):
    """Writes dependencies.json - external libraries and packages."""

    def write(self, model: ArchitectureModel) -> Path:
        """Write dependencies.json."""
        # Group by scope (runtime, dev, test, etc.)
        by_scope = {}
        for dep in model.dependencies:
            scope = dep.get("scope", "runtime")
            if scope not in by_scope:
                by_scope[scope] = []
            by_scope[scope].append(dep)

        # Group by group/category
        by_group = {}
        for dep in model.dependencies:
            group = dep.get("group", "unknown")
            if group not in by_group:
                by_group[group] = []
            by_group[group].append(dep)

        data = {
            "total": len(model.dependencies),
            "by_scope": {k: len(v) for k, v in by_scope.items()},
            "by_group": {k: len(v) for k, v in by_group.items()},
            "dependencies": model.dependencies,
        }

        return self._write_json("dependencies.json", data)


class WorkflowsWriter(DimensionWriterBase):
    """Writes workflows.json - state machines, BPMN, NgRx, etc."""

    def write(self, model: ArchitectureModel) -> Path:
        """Write workflows.json."""
        # Group by workflow type
        by_type = {}
        for wf in model.workflows:
            wf_type = wf.get("workflow_type", wf.get("type", "unknown"))
            if wf_type not in by_type:
                by_type[wf_type] = []
            by_type[wf_type].append(wf)

        data = {
            "total": len(model.workflows),
            "by_type": {k: len(v) for k, v in by_type.items()},
            "workflows": model.workflows,
        }

        return self._write_json("workflows.json", data)


# =============================================================================
# Unified Dimension Writer
# =============================================================================


class CanonicalModelWriter:
    """
    Writes all dimension files from a canonical architecture model.

    Output:
        knowledge/extract/
        +-- system.json
        +-- containers.json
        +-- components.json
        +-- interfaces.json
        +-- relations.json
        +-- data_model.json
        +-- runtime.json
        +-- infrastructure.json
        +-- evidence_map.json
    """

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize all writers
        self.system_writer = SystemWriter(output_dir)
        self.containers_writer = ContainersWriter(output_dir)
        self.components_writer = ComponentsWriter(output_dir)
        self.interfaces_writer = InterfacesWriter(output_dir)
        self.relations_writer = RelationsWriter(output_dir)
        self.data_model_writer = DataModelWriter(output_dir)
        self.runtime_writer = RuntimeWriter(output_dir)
        self.infrastructure_writer = InfrastructureWriter(output_dir)
        self.dependencies_writer = DependenciesWriter(output_dir)
        self.workflows_writer = WorkflowsWriter(output_dir)
        self.evidence_writer = EvidenceWriter(output_dir)

    def write_all(self, model: ArchitectureModel, endpoint_flows: list[dict] = None) -> dict[str, Path]:
        """
        Write all dimension files.

        Returns:
            Dictionary mapping dimension name to output path
        """
        logger.info("[CanonicalModelWriter] Writing dimension files...")

        paths = {
            "system": self.system_writer.write(model),
            "containers": self.containers_writer.write(model),
            "components": self.components_writer.write(model),
            "interfaces": self.interfaces_writer.write(model),
            "relations": self.relations_writer.write(model),
            "data_model": self.data_model_writer.write(model),
            "runtime": self.runtime_writer.write(model, endpoint_flows),
            "infrastructure": self.infrastructure_writer.write(model),
            "dependencies": self.dependencies_writer.write(model),
            "workflows": self.workflows_writer.write(model),
            "evidence_map": self.evidence_writer.write(model),
        }

        logger.info(f"[CanonicalModelWriter] Written {len(paths)} dimension files to {self.output_dir}")

        return paths

    def write_combined(self, model: ArchitectureModel, endpoint_flows: list[dict] = None) -> Path:
        """
        Write combined architecture_facts.json with ALL dimensions.

        This is the FINAL aggregated output containing:
        - system, containers, components, interfaces, relations
        - data_model (entities, tables, migrations)
        - runtime, infrastructure, dependencies, workflows
        - endpoint_flows, evidence
        """
        combined = {
            "system": {
                "id": "system",
                "name": model.system_name,
                "statistics": model.get_statistics(),
            },
            "containers": [c.to_dict() for c in model.containers.values()],
            "components": [c.to_dict() for c in model.components.values()],
            "interfaces": [i.to_dict() for i in model.interfaces.values()],
            "relations": [r.to_dict() for r in model.relations],
            "data_model": model.data_model or {},
            "runtime": model.runtime or [],
            "infrastructure": model.infrastructure or [],
            "tech_versions": model.tech_versions or [],
            "dependencies": model.dependencies,
            "workflows": model.workflows,
            "security_details": getattr(model, "security_details", []),
            "validation": getattr(model, "validation", []),
            "tests": getattr(model, "tests", []),
            "error_handling": getattr(model, "error_handling", []),
            "build_system": getattr(model, "build_system", []),
            "endpoint_flows": endpoint_flows or [],
            "evidence": list(model.evidence.values()),
        }

        # Write directly to output_dir (NOT archive)
        path = self.output_dir / "architecture_facts.json"

        with open(path, "w", encoding="utf-8") as f:
            json.dump(combined, f, indent=2, ensure_ascii=False)

        logger.info(f"[CanonicalModelWriter] Written: architecture_facts.json ({path.stat().st_size / 1024:.1f} KB)")

        return path
