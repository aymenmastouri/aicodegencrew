"""
Collector Orchestrator - Runs all collectors and aggregates results.

This is the central point that:
1. Runs all dimension collectors
2. Aggregates their outputs
3. Returns combined facts organized by dimension

Flow:
    SystemCollector     -> system facts
    ContainerCollector  -> container facts
    ComponentCollector  -> (runs specialists) -> component facts
    InterfaceCollector  -> (runs specialists) -> interface facts
    DataModelCollector  -> entity/table facts
    RuntimeCollector    -> scheduler/async facts
    InfrastructureCollector -> docker/k8s/ci facts
    EvidenceCollector   -> aggregates all evidence
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ....shared.utils.logger import logger
from .base import RawEvidence, RawFact
from .build_system_collector import BuildSystemCollector
from .component_collector import ComponentCollector
from .container_collector import ContainerCollector
from .data_model_collector import DataModelCollector
from .dependency_collector import DependencyCollector
from .error_handling_collector import ErrorHandlingCollector
from .evidence_collector import EvidenceCollector
from .infrastructure_collector import InfrastructureCollector
from .interface_collector import InterfaceCollector
from .runtime_collector import RuntimeCollector
from .security_detail_collector import SecurityDetailCollector
from .system_collector import SystemCollector
from .techstack_version_collector import TechStackVersionCollector
from .test_collector import TestCollector
from .validation_collector import ValidationCollector
from .workflow_collector import WorkflowCollector


@dataclass
class DimensionResults:
    """Results from all collectors organized by dimension."""

    # System level
    system_name: str = ""
    subsystems: list[dict] = field(default_factory=list)

    # Containers
    containers: list[dict] = field(default_factory=list)

    # Components (from all specialists)
    components: list[RawFact] = field(default_factory=list)

    # Interfaces (REST, routes, messages, etc.)
    interfaces: list[RawFact] = field(default_factory=list)

    # Data model (entities, tables)
    entities: list[RawFact] = field(default_factory=list)
    tables: list[RawFact] = field(default_factory=list)
    migrations: list[RawFact] = field(default_factory=list)

    # Runtime (schedulers, async, events)
    runtime: list[RawFact] = field(default_factory=list)

    # Infrastructure (docker, k8s, ci/cd)
    infrastructure: list[RawFact] = field(default_factory=list)

    # Dependencies (external libraries/packages)
    dependencies: list[RawFact] = field(default_factory=list)

    # Workflows (state machines, BPMN, NgRx, etc.)
    workflows: list[RawFact] = field(default_factory=list)

    # Technology versions (for upgrade planning)
    tech_versions: list[RawFact] = field(default_factory=list)

    # Security details (method-level security, CSRF, CORS)
    security_details: list[RawFact] = field(default_factory=list)

    # Validation rules (Bean Validation, custom validators)
    validation: list[RawFact] = field(default_factory=list)

    # Tests (unit, integration, e2e, cucumber)
    tests: list[RawFact] = field(default_factory=list)

    # Error handling (exception handlers, advice, custom exceptions)
    error_handling: list[RawFact] = field(default_factory=list)

    # Build system (Gradle, Maven, npm, Angular)
    build_system: list[RawFact] = field(default_factory=list)

    # All relations (hints for model builder)
    relation_hints: list[dict] = field(default_factory=list)

    # Evidence map
    evidence: dict[str, RawEvidence] = field(default_factory=dict)

    def get_statistics(self) -> dict[str, int]:
        """Get counts for all dimensions."""
        return {
            "subsystems": len(self.subsystems),
            "containers": len(self.containers),
            "components": len(self.components),
            "interfaces": len(self.interfaces),
            "entities": len(self.entities),
            "tables": len(self.tables),
            "migrations": len(self.migrations),
            "runtime_facts": len(self.runtime),
            "infrastructure_facts": len(self.infrastructure),
            "dependencies": len(self.dependencies),
            "workflows": len(self.workflows),
            "tech_versions": len(self.tech_versions),
            "security_details": len(self.security_details),
            "validation": len(self.validation),
            "tests": len(self.tests),
            "error_handling": len(self.error_handling),
            "build_system_facts": len(self.build_system),
            "relation_hints": len(self.relation_hints),
            "evidence_items": len(self.evidence),
        }


class CollectorOrchestrator:
    """
    Orchestrates all collectors to extract architecture facts.

    This replaces the scattered collector calls in the old pipeline.
    Each collector is run once, results are aggregated by dimension.

    Can optionally write JSON files after each collector step for robustness.
    """

    def __init__(self, repo_path: Path, output_dir: Path = None):
        """
        Initialize the orchestrator.

        Args:
            repo_path: Path to the repository to analyze
            output_dir: Optional directory to write JSON files to (for incremental output)
        """
        self.repo_path = Path(repo_path).resolve()
        self.output_dir = Path(output_dir) if output_dir else None

        # Results accumulator
        self.results = DimensionResults()

        # Evidence aggregator
        self.evidence_collector = EvidenceCollector(self.repo_path)

        # Load repo manifest from Discover phase (if available)
        self.repo_manifest = self._load_repo_manifest()

        # Create output dir if specified
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)

    def _load_repo_manifest(self) -> dict | None:
        """Load repo_manifest.json from Discover phase (best-effort).

        Provides framework/module hints to skip re-scanning when available.
        """
        from ....shared.paths import DISCOVER_MANIFEST

        manifest_path = Path(DISCOVER_MANIFEST)
        if not manifest_path.exists():
            return None

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            frameworks = manifest.get("frameworks", [])
            modules = manifest.get("modules", [])
            logger.info(f"[Orchestrator] Loaded repo manifest: {len(frameworks)} frameworks, {len(modules)} modules")
            return manifest
        except Exception as e:
            logger.debug(f"[Orchestrator] Could not load repo manifest: {e}")
            return None

    def _write_json(self, filename: str, data: Any) -> None:
        """Write JSON file to output directory if configured."""
        if not self.output_dir:
            return

        filepath = self.output_dir / filename
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"  [OK] Wrote {filepath.name}")
        except Exception as e:
            logger.warning(f"  [WARN] Failed to write {filepath}: {e}")

    def _fact_to_dict(self, fact: RawFact) -> dict:
        """Convert a RawFact to dictionary."""
        result = {
            "name": fact.name,
        }
        # Add all non-None attributes
        for attr in [
            "type",
            "workflow_type",
            "stereotype",
            "container_hint",
            "file_path",
            "module",
            "layer_hint",
            "path",
            "method",
            "version",
            "scope",
            "group",
            "states",
            "transitions",
            "actions",
            "security_type",
            "roles",
            "class_name",
            "validation_type",
            "constraint",
            "target_class",
            "target_field",
            "test_type",
            "framework",
            "scenarios",
            "tested_component_hint",
            "handling_type",
            "exception_class",
            "http_status",
            "handler_method",
            "technology",
            "source_file",
            "category",
            "build_tool",
            "module_path",
            "tasks",
            "source_dirs",
            "plugins",
            "wrapper_path",
            "parent_module",
            "build_file",
            "properties",
        ]:
            if hasattr(fact, attr):
                val = getattr(fact, attr)
                if val is not None and val != "" and val != []:
                    result[attr] = val

        # Add evidence
        if hasattr(fact, "evidence") and fact.evidence:
            result["evidence"] = [e.to_dict() for e in fact.evidence]

        return result

    def _is_enabled(self, collector_id: str, collector_config: dict[str, bool] | None) -> bool:
        """Check if a collector is enabled in the config."""
        if collector_config is None:
            return True
        return collector_config.get(collector_id, True)

    def run_all(self, collector_config: dict[str, bool] | None = None) -> DimensionResults:
        """
        Run all collectors and return aggregated results.

        Args:
            collector_config: Optional dict mapping collector_id -> enabled.
                If None, all collectors run. Core collectors (steps 1-3, 15)
                always run regardless of config.

        Order matters:
        1. System - gets system name
        2. Container - detects deployable units
        3. Component - runs specialists based on detected containers
        4. Interface - REST/routes/messages
        5. DataModel - entities/tables
        6. Runtime - schedulers/async
        7. Infrastructure - docker/k8s/ci
        8. Dependencies - external libraries/packages
        9. Workflows - state machines/BPMN/NgRx
        10-14. Tech versions, security, validation, tests, error handling
        15. Build system - Gradle/Maven/npm/Angular build files
        16. Evidence - final aggregation
        """
        logger.info("[CollectorOrchestrator] Starting architecture extraction...")

        # 1. System facts (core — always runs)
        logger.info("[CollectorOrchestrator] Step 1/16: System facts...")
        self._run_system_collector()

        # 2. Container detection (core — always runs)
        logger.info("[CollectorOrchestrator] Step 2/16: Container detection...")
        self._run_container_collector()

        # 3. Component extraction (core — always runs)
        logger.info("[CollectorOrchestrator] Step 3/16: Component extraction...")
        self._run_component_collector()

        # 4. Interface extraction
        if self._is_enabled("interfaces", collector_config):
            logger.info("[CollectorOrchestrator] Step 4/16: Interface extraction...")
            self._run_interface_collector()
        else:
            logger.info("[CollectorOrchestrator] Step 4/16: Skipping interfaces (disabled)")

        # 5. Data model extraction
        if self._is_enabled("data_model", collector_config):
            logger.info("[CollectorOrchestrator] Step 5/16: Data model extraction...")
            self._run_data_model_collector()
        else:
            logger.info("[CollectorOrchestrator] Step 5/16: Skipping data_model (disabled)")

        # 6. Runtime extraction
        if self._is_enabled("runtime", collector_config):
            logger.info("[CollectorOrchestrator] Step 6/16: Runtime extraction...")
            self._run_runtime_collector()
        else:
            logger.info("[CollectorOrchestrator] Step 6/16: Skipping runtime (disabled)")

        # 7. Infrastructure extraction
        if self._is_enabled("infrastructure", collector_config):
            logger.info("[CollectorOrchestrator] Step 7/16: Infrastructure extraction...")
            self._run_infrastructure_collector()
        else:
            logger.info("[CollectorOrchestrator] Step 7/16: Skipping infrastructure (disabled)")

        # 8. Dependencies extraction
        if self._is_enabled("dependencies", collector_config):
            logger.info("[CollectorOrchestrator] Step 8/16: Dependencies extraction...")
            self._run_dependency_collector()
        else:
            logger.info("[CollectorOrchestrator] Step 8/16: Skipping dependencies (disabled)")

        # 9. Workflows extraction
        if self._is_enabled("workflows", collector_config):
            logger.info("[CollectorOrchestrator] Step 9/16: Workflows extraction...")
            self._run_workflow_collector()
        else:
            logger.info("[CollectorOrchestrator] Step 9/16: Skipping workflows (disabled)")

        # 10. Technology versions extraction
        if self._is_enabled("tech_versions", collector_config):
            logger.info("[CollectorOrchestrator] Step 10/16: Technology versions extraction...")
            self._run_techstack_version_collector()
        else:
            logger.info("[CollectorOrchestrator] Step 10/16: Skipping tech_versions (disabled)")

        # 11. Security details extraction
        if self._is_enabled("security_details", collector_config):
            logger.info("[CollectorOrchestrator] Step 11/16: Security details extraction...")
            self._run_security_detail_collector()
        else:
            logger.info("[CollectorOrchestrator] Step 11/16: Skipping security_details (disabled)")

        # 12. Validation rules extraction
        if self._is_enabled("validation", collector_config):
            logger.info("[CollectorOrchestrator] Step 12/16: Validation rules extraction...")
            self._run_validation_collector()
        else:
            logger.info("[CollectorOrchestrator] Step 12/16: Skipping validation (disabled)")

        # 13. Tests extraction
        if self._is_enabled("tests", collector_config):
            logger.info("[CollectorOrchestrator] Step 13/16: Tests extraction...")
            self._run_test_collector()
        else:
            logger.info("[CollectorOrchestrator] Step 13/16: Skipping tests (disabled)")

        # 14. Error handling extraction
        if self._is_enabled("error_handling", collector_config):
            logger.info("[CollectorOrchestrator] Step 14/16: Error handling extraction...")
            self._run_error_handling_collector()
        else:
            logger.info("[CollectorOrchestrator] Step 14/16: Skipping error_handling (disabled)")

        # 15. Build system extraction
        if self._is_enabled("build_system", collector_config):
            logger.info("[CollectorOrchestrator] Step 15/16: Build system extraction...")
            self._run_build_system_collector()
        else:
            logger.info("[CollectorOrchestrator] Step 15/16: Skipping build_system (disabled)")

        # 16. Evidence aggregation (core — always runs)
        logger.info("[CollectorOrchestrator] Step 16/16: Evidence aggregation...")
        self._aggregate_evidence()

        # Log statistics
        stats = self.results.get_statistics()
        logger.info("[CollectorOrchestrator] Extraction complete:")
        for key, value in stats.items():
            if value > 0:
                logger.info(f"  - {key}: {value}")

        # Write combined architecture_facts.json (raw collector output)
        self._write_combined_facts()

        return self.results

    def _run_system_collector(self) -> None:
        """Run SystemCollector to get system name and subsystems."""
        from .system_collector import RawSubsystem, RawSystemInfo

        collector = SystemCollector(self.repo_path)
        output = collector.collect()

        # Extract system name from facts
        for fact in output.facts:
            if isinstance(fact, RawSystemInfo):
                self.results.system_name = fact.name
            elif isinstance(fact, RawSubsystem):
                self.results.subsystems.append(
                    {
                        "name": fact.name,
                        "type": fact.type,
                        "root_path": fact.root_path,
                    }
                )

        # Add evidence
        self.evidence_collector.add_from_output(output)

        # Add relation hints
        self.results.relation_hints.extend([r.to_dict() for r in output.relations])

        if not self.results.system_name:
            self.results.system_name = self.repo_path.name

        # Write system.json
        self._write_json(
            "system.json",
            {
                "name": self.results.system_name,
                "version": None,
                "description": None,
                "contexts": [s["name"] for s in self.results.subsystems],
            },
        )

    def _run_container_collector(self) -> None:
        """Run ContainerCollector to detect deployable units."""
        collector = ContainerCollector(self.repo_path)
        output = collector.collect()

        # Convert RawContainer facts to dicts
        for fact in output.facts:
            container_dict = {
                "name": fact.name,
                "type": getattr(fact, "type", "unknown"),
                "technology": getattr(fact, "technology", ""),
                "category": getattr(fact, "category", "unknown"),
                "root_path": str(getattr(fact, "root_path", "")),
                "metadata": getattr(fact, "metadata", {}),
            }
            self.results.containers.append(container_dict)

        # Add evidence
        self.evidence_collector.add_from_output(output)

        logger.info(f"  Detected {len(self.results.containers)} containers")

        # Write containers.json
        containers_out = [
            {
                "id": c["name"],
                "name": c["name"],
                "type": c["type"],
                "technology": c["technology"],
                "path": c["root_path"],
                "category": c["category"],
            }
            for c in self.results.containers
        ]
        self._write_json("containers.json", containers_out)

    def _run_component_collector(self) -> None:
        """
        Run ComponentCollector with detected container context.

        ComponentCollector internally runs specialists:
        - Spring: RestCollector, ServiceCollector, RepositoryCollector
        - Angular: ModuleCollector, ComponentCollector, ServiceCollector
        """
        # Pass container info directly (containers already has the right format)
        collector = ComponentCollector(self.repo_path, self.results.containers)
        output = collector.collect()

        # Add components
        self.results.components.extend(output.facts)

        # Add relation hints
        self.results.relation_hints.extend([r.to_dict() for r in output.relations])

        # Add evidence
        self.evidence_collector.add_from_output(output)

        logger.info(f"  Extracted {len(output.facts)} components")

        # Write components.json
        components_out = [self._fact_to_dict(c) for c in self.results.components]
        self._write_json("components.json", components_out)

    def _run_interface_collector(self) -> None:
        """Run InterfaceCollector for REST, routes, messages."""
        # Pass container info to interface collector
        collector = InterfaceCollector(self.repo_path, self.results.containers)
        output = collector.collect()

        # Add interfaces
        self.results.interfaces.extend(output.facts)

        # Add relation hints
        self.results.relation_hints.extend([r.to_dict() for r in output.relations])

        # Add evidence
        self.evidence_collector.add_from_output(output)

        logger.info(f"  Extracted {len(output.facts)} interfaces")

        # Write interfaces.json
        interfaces_out = [self._fact_to_dict(i) for i in self.results.interfaces]
        self._write_json("interfaces.json", interfaces_out)

    def _run_data_model_collector(self) -> None:
        """Run DataModelCollector for entities, tables, migrations."""
        collector = DataModelCollector(self.repo_path)
        output = collector.collect()

        # Separate into entities, tables, migrations
        for fact in output.facts:
            fact_type = getattr(fact, "fact_type", "entity")

            if fact_type == "jpa_entity" or fact_type == "entity":
                self.results.entities.append(fact)
            elif fact_type == "table":
                self.results.tables.append(fact)
            elif fact_type == "migration":
                self.results.migrations.append(fact)
            else:
                # Default to entity
                self.results.entities.append(fact)

        # Add relation hints (entity relationships)
        self.results.relation_hints.extend([r.to_dict() for r in output.relations])

        # Add evidence
        self.evidence_collector.add_from_output(output)

        logger.info(f"  Extracted {len(self.results.entities)} entities, {len(self.results.tables)} tables")

        # Write data_model.json
        data_model_out = {
            "entities": [self._fact_to_dict(e) for e in self.results.entities],
            "tables": [self._fact_to_dict(t) for t in self.results.tables],
            "migrations": [self._fact_to_dict(m) for m in self.results.migrations],
        }
        self._write_json("data_model.json", data_model_out)

    def _run_runtime_collector(self) -> None:
        """Run RuntimeCollector for schedulers, async, events."""
        collector = RuntimeCollector(self.repo_path)
        output = collector.collect()

        # Add runtime facts
        self.results.runtime.extend(output.facts)

        # Add relation hints
        self.results.relation_hints.extend([r.to_dict() for r in output.relations])

        # Add evidence
        self.evidence_collector.add_from_output(output)

        logger.info(f"  Extracted {len(output.facts)} runtime facts")

        # Write runtime.json
        runtime_out = [self._fact_to_dict(r) for r in self.results.runtime]
        self._write_json("runtime.json", runtime_out)

    def _run_infrastructure_collector(self) -> None:
        """Run InfrastructureCollector for docker, k8s, ci/cd."""
        collector = InfrastructureCollector(self.repo_path)
        output = collector.collect()

        # Add infrastructure facts
        self.results.infrastructure.extend(output.facts)

        # Also detect containers from infrastructure
        for fact in output.facts:
            fact_type = getattr(fact, "fact_type", "")

            # Compose services become containers
            if fact_type == "compose_service":
                existing_names = [c.get("name") for c in self.results.containers]
                if fact.name not in existing_names:
                    self.results.containers.append(
                        {
                            "name": fact.name,
                            "technology": getattr(fact, "image", "docker"),
                            "category": "database"
                            if "db" in fact.name.lower() or "postgres" in str(getattr(fact, "image", "")).lower()
                            else "backend",
                            "root_path": "",
                            "description": f"Docker service: {fact.name}",
                            "config_files": [],
                        }
                    )

        # Add relation hints
        self.results.relation_hints.extend([r.to_dict() for r in output.relations])

        # Add evidence
        self.evidence_collector.add_from_output(output)

        logger.info(f"  Extracted {len(output.facts)} infrastructure facts")

        # Write infrastructure.json
        infra_out = [self._fact_to_dict(i) for i in self.results.infrastructure]
        self._write_json("infrastructure.json", infra_out)

    def _run_dependency_collector(self) -> None:
        """Run DependencyCollector for external libraries/packages."""
        collector = DependencyCollector(self.repo_path)
        output = collector.collect()

        # Add dependency facts
        self.results.dependencies.extend(output.facts)

        # Add relation hints (dependencies create relations)
        self.results.relation_hints.extend([r.to_dict() for r in output.relations])

        # Add evidence
        self.evidence_collector.add_from_output(output)

        logger.info(f"  Extracted {len(output.facts)} dependencies")

        # Write dependencies.json
        deps_out = [self._fact_to_dict(d) for d in self.results.dependencies]
        self._write_json("dependencies.json", deps_out)

    def _run_workflow_collector(self) -> None:
        """Run WorkflowCollector for state machines, BPMN, NgRx, etc."""
        collector = WorkflowCollector(self.repo_path)
        output = collector.collect()

        # Add workflow facts
        self.results.workflows.extend(output.facts)

        # Add relation hints
        self.results.relation_hints.extend([r.to_dict() for r in output.relations])

        # Add evidence
        self.evidence_collector.add_from_output(output)

        logger.info(f"  Extracted {len(output.facts)} workflows")

        # Write workflows.json
        workflows_out = [self._fact_to_dict(w) for w in self.results.workflows]
        self._write_json("workflows.json", workflows_out)

    def _run_techstack_version_collector(self) -> None:
        """Run TechStackVersionCollector for technology versions (upgrade planning)."""
        collector = TechStackVersionCollector(self.repo_path)
        output = collector.collect()

        # Add tech version facts
        self.results.tech_versions.extend(output.facts)

        # Add evidence
        self.evidence_collector.add_from_output(output)

        logger.info(f"  Extracted {len(output.facts)} technology versions")

        # Write tech_versions.json
        versions_out = []
        for fact in self.results.tech_versions:
            versions_out.append(
                {
                    "technology": getattr(fact, "technology", fact.name),
                    "version": getattr(fact, "version", ""),
                    "category": getattr(fact, "category", ""),
                    "source_file": getattr(fact, "source_file", ""),
                }
            )
        self._write_json("tech_versions.json", versions_out)

    def _run_security_detail_collector(self) -> None:
        """Run SecurityDetailCollector for method-level security, CSRF, CORS."""
        collector = SecurityDetailCollector(self.repo_path)
        output = collector.collect()

        self.results.security_details.extend(output.facts)
        self.results.relation_hints.extend([r.to_dict() for r in output.relations])
        self.evidence_collector.add_from_output(output)

        logger.info(f"  Extracted {len(output.facts)} security details")

        details_out = [self._fact_to_dict(s) for s in self.results.security_details]
        self._write_json("security_details.json", details_out)

    def _run_validation_collector(self) -> None:
        """Run ValidationCollector for Bean Validation, custom validators."""
        collector = ValidationCollector(self.repo_path)
        output = collector.collect()

        self.results.validation.extend(output.facts)
        self.results.relation_hints.extend([r.to_dict() for r in output.relations])
        self.evidence_collector.add_from_output(output)

        logger.info(f"  Extracted {len(output.facts)} validation rules")

        validation_out = [self._fact_to_dict(v) for v in self.results.validation]
        self._write_json("validation.json", validation_out)

    def _run_test_collector(self) -> None:
        """Run TestCollector for unit, integration, e2e tests."""
        collector = TestCollector(self.repo_path)
        output = collector.collect()

        self.results.tests.extend(output.facts)
        self.results.relation_hints.extend([r.to_dict() for r in output.relations])
        self.evidence_collector.add_from_output(output)

        logger.info(f"  Extracted {len(output.facts)} test facts")

        tests_out = [self._fact_to_dict(t) for t in self.results.tests]
        self._write_json("tests.json", tests_out)

    def _run_error_handling_collector(self) -> None:
        """Run ErrorHandlingCollector for exception handlers, advice, custom exceptions."""
        collector = ErrorHandlingCollector(self.repo_path)
        output = collector.collect()

        self.results.error_handling.extend(output.facts)
        self.results.relation_hints.extend([r.to_dict() for r in output.relations])
        self.evidence_collector.add_from_output(output)

        logger.info(f"  Extracted {len(output.facts)} error handling facts")

        error_out = [self._fact_to_dict(e) for e in self.results.error_handling]
        self._write_json("error_handling.json", error_out)

    def _run_build_system_collector(self) -> None:
        """Run BuildSystemCollector for Gradle, Maven, npm, Angular build files."""
        collector = BuildSystemCollector(self.repo_path)
        output = collector.collect()

        self.results.build_system.extend(output.facts)
        self.results.relation_hints.extend([r.to_dict() for r in output.relations])
        self.evidence_collector.add_from_output(output)

        logger.info(f"  Extracted {len(output.facts)} build system facts")

        build_out = [self._fact_to_dict(b) for b in self.results.build_system]
        self._write_json("build_system.json", build_out)

    def _aggregate_evidence(self) -> None:
        """Build final evidence map."""
        self.results.evidence = self.evidence_collector.build_evidence_map()
        logger.info(f"  Aggregated {len(self.results.evidence)} evidence items")

        # Write evidence_map.json
        evidence_out = {k: v.to_dict() if hasattr(v, "to_dict") else v for k, v in self.results.evidence.items()}
        self._write_json("evidence_map.json", evidence_out)

        # Write relations.json
        self._write_json("relations.json", self.results.relation_hints)

    def _write_combined_facts(self) -> None:
        """Write combined architecture_facts.json with all collected data."""
        if not self.output_dir:
            return

        # Build combined structure
        combined = {
            "system": {
                "name": self.results.system_name,
                "subsystems": self.results.subsystems,
            },
            "containers": [
                {
                    "id": c["name"],
                    "name": c["name"],
                    "type": c.get("type", "unknown"),
                    "technology": c.get("technology", ""),
                    "path": c.get("root_path", ""),
                    "category": c.get("category", "unknown"),
                }
                for c in self.results.containers
            ],
            "components": [self._fact_to_dict(c) for c in self.results.components],
            "interfaces": [self._fact_to_dict(i) for i in self.results.interfaces],
            "relations": self.results.relation_hints,
            "data_model": {
                "entities": [self._fact_to_dict(e) for e in self.results.entities],
                "tables": [self._fact_to_dict(t) for t in self.results.tables],
                "migrations": [self._fact_to_dict(m) for m in self.results.migrations],
            },
            "runtime": [self._fact_to_dict(r) for r in self.results.runtime],
            "infrastructure": [self._fact_to_dict(i) for i in self.results.infrastructure],
            "dependencies": [self._fact_to_dict(d) for d in self.results.dependencies],
            "workflows": [self._fact_to_dict(w) for w in self.results.workflows],
            "tech_versions": [
                {
                    "technology": getattr(v, "technology", v.name),
                    "version": getattr(v, "version", ""),
                    "category": getattr(v, "category", ""),
                    "source_file": getattr(v, "source_file", ""),
                }
                for v in self.results.tech_versions
            ],
            "security_details": [self._fact_to_dict(s) for s in self.results.security_details],
            "validation": [self._fact_to_dict(v) for v in self.results.validation],
            "tests": [self._fact_to_dict(t) for t in self.results.tests],
            "error_handling": [self._fact_to_dict(e) for e in self.results.error_handling],
            "build_system": [self._fact_to_dict(b) for b in self.results.build_system],
            "evidence": {k: v.to_dict() if hasattr(v, "to_dict") else v for k, v in self.results.evidence.items()},
            "statistics": self.results.get_statistics(),
        }

        self._write_json("architecture_facts.json", combined)
        logger.info("[CollectorOrchestrator] Wrote architecture_facts.json (combined)")
