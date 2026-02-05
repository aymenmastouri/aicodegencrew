"""
Collector Orchestrator - Runs all collectors and aggregates results.

This is the central point that:
1. Runs all dimension collectors
2. Aggregates their outputs
3. Returns combined facts organized by dimension

Flow:
    SystemCollector     → system facts
    ContainerCollector  → container facts
    ComponentCollector  → (runs specialists) → component facts
    InterfaceCollector  → (runs specialists) → interface facts
    DataModelCollector  → entity/table facts
    RuntimeCollector    → scheduler/async facts
    InfrastructureCollector → docker/k8s/ci facts
    EvidenceCollector   → aggregates all evidence
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
import json

from .base import CollectorOutput, RawFact, RawEvidence
from .system_collector import SystemCollector
from .container_collector import ContainerCollector
from .component_collector import ComponentCollector
from .interface_collector import InterfaceCollector
from .data_model_collector import DataModelCollector
from .runtime_collector import RuntimeCollector
from .infrastructure_collector import InfrastructureCollector
from .dependency_collector import DependencyCollector
from .workflow_collector import WorkflowCollector
from .evidence_collector import EvidenceCollector

from ....shared.utils.logger import logger


@dataclass
class DimensionResults:
    """Results from all collectors organized by dimension."""
    
    # System level
    system_name: str = ""
    subsystems: List[Dict] = field(default_factory=list)
    
    # Containers
    containers: List[Dict] = field(default_factory=list)
    
    # Components (from all specialists)
    components: List[RawFact] = field(default_factory=list)
    
    # Interfaces (REST, routes, messages, etc.)
    interfaces: List[RawFact] = field(default_factory=list)
    
    # Data model (entities, tables)
    entities: List[RawFact] = field(default_factory=list)
    tables: List[RawFact] = field(default_factory=list)
    migrations: List[RawFact] = field(default_factory=list)
    
    # Runtime (schedulers, async, events)
    runtime: List[RawFact] = field(default_factory=list)
    
    # Infrastructure (docker, k8s, ci/cd)
    infrastructure: List[RawFact] = field(default_factory=list)
    
    # Dependencies (external libraries/packages)
    dependencies: List[RawFact] = field(default_factory=list)
    
    # Workflows (state machines, BPMN, NgRx, etc.)
    workflows: List[RawFact] = field(default_factory=list)
    
    # All relations (hints for model builder)
    relation_hints: List[Dict] = field(default_factory=list)
    
    # Evidence map
    evidence: Dict[str, RawEvidence] = field(default_factory=dict)
    
    def get_statistics(self) -> Dict[str, int]:
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
        
        # Create output dir if specified
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _write_json(self, filename: str, data: Any) -> None:
        """Write JSON file to output directory if configured."""
        if not self.output_dir:
            return
        
        filepath = self.output_dir / filename
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"  [OK] Wrote {filepath.name}")
        except Exception as e:
            logger.warning(f"  [WARN] Failed to write {filepath}: {e}")
    
    def _fact_to_dict(self, fact: RawFact) -> Dict:
        """Convert a RawFact to dictionary."""
        result = {
            "name": fact.name,
        }
        # Add all non-None attributes
        for attr in ['type', 'workflow_type', 'stereotype', 'container_hint', 'file_path', 
                     'module', 'layer_hint', 'path', 'method', 'version', 'scope', 'group',
                     'states', 'transitions', 'actions']:
            if hasattr(fact, attr):
                val = getattr(fact, attr)
                if val is not None and val != "" and val != []:
                    result[attr] = val
        
        # Add evidence
        if hasattr(fact, 'evidence') and fact.evidence:
            result['evidence'] = [e.to_dict() for e in fact.evidence]
        
        return result
    
    def run_all(self) -> DimensionResults:
        """
        Run all collectors and return aggregated results.
        
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
        10. Evidence - final aggregation
        """
        logger.info("[CollectorOrchestrator] Starting architecture extraction...")
        
        # 1. System facts
        logger.info("[CollectorOrchestrator] Step 1/10: System facts...")
        self._run_system_collector()
        
        # 2. Container detection
        logger.info("[CollectorOrchestrator] Step 2/10: Container detection...")
        self._run_container_collector()
        
        # 3. Component extraction (includes specialists)
        logger.info("[CollectorOrchestrator] Step 3/10: Component extraction...")
        self._run_component_collector()
        
        # 4. Interface extraction
        logger.info("[CollectorOrchestrator] Step 4/10: Interface extraction...")
        self._run_interface_collector()
        
        # 5. Data model extraction
        logger.info("[CollectorOrchestrator] Step 5/10: Data model extraction...")
        self._run_data_model_collector()
        
        # 6. Runtime extraction
        logger.info("[CollectorOrchestrator] Step 6/10: Runtime extraction...")
        self._run_runtime_collector()
        
        # 7. Infrastructure extraction
        logger.info("[CollectorOrchestrator] Step 7/10: Infrastructure extraction...")
        self._run_infrastructure_collector()
        
        # 8. Dependencies extraction
        logger.info("[CollectorOrchestrator] Step 8/10: Dependencies extraction...")
        self._run_dependency_collector()
        
        # 9. Workflows extraction
        logger.info("[CollectorOrchestrator] Step 9/10: Workflows extraction...")
        self._run_workflow_collector()
        
        # 10. Evidence aggregation
        logger.info("[CollectorOrchestrator] Step 10/10: Evidence aggregation...")
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
        from .system_collector import RawSystemInfo, RawSubsystem
        
        collector = SystemCollector(self.repo_path)
        output = collector.collect()
        
        # Extract system name from facts
        for fact in output.facts:
            if isinstance(fact, RawSystemInfo):
                self.results.system_name = fact.name
            elif isinstance(fact, RawSubsystem):
                self.results.subsystems.append({
                    "name": fact.name,
                    "type": fact.type,
                    "root_path": fact.root_path,
                })
        
        # Add evidence
        self.evidence_collector.add_from_output(output)
        
        # Add relation hints
        self.results.relation_hints.extend([r.to_dict() for r in output.relations])
        
        if not self.results.system_name:
            self.results.system_name = self.repo_path.name
        
        # Write system.json
        self._write_json("system.json", {
            "name": self.results.system_name,
            "version": None,
            "description": None,
            "contexts": [s["name"] for s in self.results.subsystems]
        })
    
    def _run_container_collector(self) -> None:
        """Run ContainerCollector to detect deployable units."""
        collector = ContainerCollector(self.repo_path)
        output = collector.collect()
        
        # Convert RawContainer facts to dicts
        for fact in output.facts:
            container_dict = {
                "name": fact.name,
                "type": getattr(fact, 'type', 'unknown'),
                "technology": getattr(fact, 'technology', ''),
                "category": getattr(fact, 'category', 'unknown'),
                "root_path": str(getattr(fact, 'root_path', '')),
                "metadata": getattr(fact, 'metadata', {}),
            }
            self.results.containers.append(container_dict)
        
        # Add evidence
        self.evidence_collector.add_from_output(output)
        
        logger.info(f"  Detected {len(self.results.containers)} containers")
        
        # Write containers.json
        containers_out = [{
            "id": c["name"],
            "name": c["name"],
            "type": c["type"],
            "technology": c["technology"],
            "path": c["root_path"],
            "category": c["category"]
        } for c in self.results.containers]
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
            fact_type = getattr(fact, 'fact_type', 'entity')
            
            if fact_type == 'jpa_entity' or fact_type == 'entity':
                self.results.entities.append(fact)
            elif fact_type == 'table':
                self.results.tables.append(fact)
            elif fact_type == 'migration':
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
            "migrations": [self._fact_to_dict(m) for m in self.results.migrations]
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
            fact_type = getattr(fact, 'fact_type', '')
            
            # Compose services become containers
            if fact_type == 'compose_service':
                existing_names = [c.get("name") for c in self.results.containers]
                if fact.name not in existing_names:
                    self.results.containers.append({
                        "name": fact.name,
                        "technology": getattr(fact, 'image', "docker"),
                        "category": "database" if "db" in fact.name.lower() or "postgres" in str(getattr(fact, 'image', '')).lower() else "backend",
                        "root_path": "",
                        "description": f"Docker service: {fact.name}",
                        "config_files": [],
                    })
        
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

    def _aggregate_evidence(self) -> None:
        """Build final evidence map."""
        self.results.evidence = self.evidence_collector.build_evidence_map()
        logger.info(f"  Aggregated {len(self.results.evidence)} evidence items")
        
        # Write evidence_map.json
        evidence_out = {k: v.to_dict() if hasattr(v, 'to_dict') else v for k, v in self.results.evidence.items()}
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
            "containers": [{
                "id": c["name"],
                "name": c["name"],
                "type": c.get("type", "unknown"),
                "technology": c.get("technology", ""),
                "path": c.get("root_path", ""),
                "category": c.get("category", "unknown"),
            } for c in self.results.containers],
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
            "evidence": {k: v.to_dict() if hasattr(v, 'to_dict') else v for k, v in self.results.evidence.items()},
            "statistics": self.results.get_statistics(),
        }
        
        self._write_json("architecture_facts.json", combined)
        logger.info(f"[CollectorOrchestrator] Wrote architecture_facts.json (combined)")
