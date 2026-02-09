"""
Architecture Facts Pipeline (Phase 1)

Deterministic extraction of architecture facts from source code.
NO LLM. NO interpretation. Only facts + evidence.

This is the SINGLE SOURCE OF TRUTH for architecture.
Uses the new modular collector architecture.

Usage:
    from aicodegencrew.pipelines.architecture_facts import ArchitectureFactsPipeline
    
    pipeline = ArchitectureFactsPipeline(repo_path="/path/to/repo")
    result = pipeline.kickoff()
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

from .collectors.orchestrator import CollectorOrchestrator, DimensionResults
from .collectors.fact_adapter import DimensionResultsAdapter
from .model_builder import ArchitectureModelBuilder
from .dimension_writers import CanonicalModelWriter
from .endpoint_flow_builder import EndpointFlowBuilder
from ...shared.utils.logger import logger


class ArchitectureFactsPipeline:
    """
    Phase 1: Architecture Facts Pipeline
    
    Deterministic extraction - NO LLM!
    
    Outputs (Dimension Files):
    - knowledge/architecture/system.json
    - knowledge/architecture/containers.json
    - knowledge/architecture/components.json
    - knowledge/architecture/interfaces.json
    - knowledge/architecture/relations.json
    - knowledge/architecture/data_model.json
    - knowledge/architecture/runtime.json
    - knowledge/architecture/infrastructure.json
    - knowledge/architecture/evidence_map.json
    """
    
    def __init__(
        self,
        repo_path: str,
        output_dir: Optional[str] = None,
    ):
        """
        Initialize the Architecture Facts Pipeline.
        
        Args:
            repo_path: Path to the repository to analyze
            output_dir: Output directory (defaults to knowledge/architecture)
        """
        self.repo_path = Path(repo_path).resolve()
        self.output_dir = Path(output_dir) if output_dir else Path("knowledge/architecture")
        
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {self.repo_path}")
        
        logger.info(f"[Phase1] ArchitectureFactsPipeline initialized")
        logger.info(f"[Phase1] Repository: {self.repo_path}")
        logger.info(f"[Phase1] Output: {self.output_dir}")
    
    def _fact_to_dict(self, fact) -> Dict[str, Any]:
        """Convert a RawFact to dictionary."""
        result = {
            "name": getattr(fact, 'name', 'unknown'),
        }
        # Add all non-None attributes
        for attr in ['type', 'workflow_type', 'stereotype', 'container_hint', 'file_path',
                     'module', 'layer_hint', 'path', 'method', 'version', 'scope', 'group',
                     'states', 'transitions', 'actions',
                     'security_type', 'roles', 'class_name',
                     'validation_type', 'constraint', 'target_class', 'target_field',
                     'test_type', 'framework', 'scenarios', 'tested_component_hint',
                     'handling_type', 'exception_class', 'http_status', 'handler_method',
                     'technology', 'source_file', 'category']:
            if hasattr(fact, attr):
                val = getattr(fact, attr)
                if val is not None and val != "" and val != []:
                    result[attr] = val
        
        # Add evidence
        if hasattr(fact, 'evidence') and fact.evidence:
            result['evidence'] = [e.to_dict() if hasattr(e, 'to_dict') else e for e in fact.evidence]
        
        return result
    
    
    def _archive_and_clean_old_outputs(self) -> None:
        """Archive and clean old Phase 1 outputs before new run."""
        output_files = [
            "architecture_facts.json",
            "evidence_map.json",
            "system.json",
            "containers.json",
            "components.json",
            "interfaces.json",
            "relations.json",
            "data_model.json",
            "runtime.json",
            "infrastructure.json",
        ]
        
        existing_files = [f for f in output_files if (self.output_dir / f).exists()]
        
        if existing_files:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_dir = self.output_dir / "archive" / f"run_{timestamp}"
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            for filename in existing_files:
                src = self.output_dir / filename
                dst = archive_dir / filename
                shutil.copy2(src, dst)
                src.unlink()
            
            logger.info(f"   [OK] {len(existing_files)} old files archived to: archive/run_{timestamp}")
        else:
            logger.info("   [OK] No old outputs to clean (first run)")
    
    def kickoff(self, inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the Architecture Facts Pipeline.
        
        Args:
            inputs: Optional input parameters (for orchestrator compatibility)
        
        Returns:
            Dictionary with extraction results
        """
        logger.info("=" * 60)
        logger.info("[Phase1] Starting Architecture Facts Extraction")
        logger.info("[Phase1] Mode: DETERMINISTIC (no LLM)")
        logger.info("=" * 60)
        
        # Step 0: Archive and clean old outputs
        logger.info("[Phase1] Step 0: Archive and clean old outputs...")
        self._archive_and_clean_old_outputs()
        
        try:
            # Step 1: Run all collectors via orchestrator
            # Pass output_dir so each collector writes JSON immediately after completion
            logger.info("\n[Phase1] Step 1: Running collectors...")
            orchestrator = CollectorOrchestrator(self.repo_path, output_dir=self.output_dir)
            results: DimensionResults = orchestrator.run_all()
            
            # Step 2: Adapt raw facts to model format
            logger.info("\n[Phase1] Step 2: Adapting facts to model format...")
            adapter = DimensionResultsAdapter(self.repo_path)
            adapted = adapter.convert(results)
            
            # Step 3: Build canonical architecture model
            logger.info("\n[Phase1] Step 3: Building canonical architecture model...")
            model_builder = ArchitectureModelBuilder(system_name=results.system_name)
            
            # Add containers
            model_builder.add_containers(results.containers, {})
            
            # Add all adapted outputs
            model_builder.add_collector_output(
                components=adapted["components"],
                interfaces=adapted["interfaces"],
                relations=adapted["relations"],
                evidence=adapted["evidence"],
            )
            
            # Build the canonical model
            canonical_model = model_builder.build()
            
            # Add dimensions from DimensionResults that pass through directly
            # (these don't need normalization by the model builder)
            canonical_model.dependencies = [
                self._fact_to_dict(d) for d in results.dependencies
            ]
            canonical_model.workflows = [
                self._fact_to_dict(w) for w in results.workflows
            ]
            canonical_model.data_model = {
                "entities": [self._fact_to_dict(e) for e in results.entities],
                "tables": [self._fact_to_dict(t) for t in results.tables],
                "migrations": [self._fact_to_dict(m) for m in results.migrations],
            }
            canonical_model.runtime = [
                self._fact_to_dict(r) for r in results.runtime
            ]
            canonical_model.infrastructure = [
                self._fact_to_dict(i) for i in results.infrastructure
            ]
            canonical_model.tech_versions = [
                self._fact_to_dict(tv) for tv in getattr(results, 'tech_versions', [])
            ]
            canonical_model.security_details = [
                self._fact_to_dict(s) for s in getattr(results, 'security_details', [])
            ]
            canonical_model.validation = [
                self._fact_to_dict(v) for v in getattr(results, 'validation', [])
            ]
            canonical_model.tests = [
                self._fact_to_dict(t) for t in getattr(results, 'tests', [])
            ]
            canonical_model.error_handling = [
                self._fact_to_dict(e) for e in getattr(results, 'error_handling', [])
            ]
            
            stats = canonical_model.get_statistics()
            logger.info(f"[Phase1] Canonical model: {stats['components']} components, {stats['relations']} relations")
            logger.info(f"[Phase1] Dependencies: {stats['dependencies']}, Workflows: {stats['workflows']}")
            logger.info(f"[Phase1] Security: {stats.get('security_details', 0)}, Validation: {stats.get('validation', 0)}, Tests: {stats.get('tests', 0)}, Errors: {stats.get('error_handling', 0)}")
            
            # Step 4: Build endpoint flows
            logger.info("\n[Phase1] Step 4: Building endpoint flows...")
            flow_builder = EndpointFlowBuilder(
                components=adapted["components"],
                interfaces=adapted["interfaces"],
                relations=adapted["relations"],
                evidence=adapted["evidence"],
            )
            endpoint_flows = flow_builder.build_flows()
            logger.info(f"[Phase1] Built {len(endpoint_flows)} endpoint flows")
            
            # Step 5: Write dimension files
            logger.info("\n[Phase1] Step 5: Writing dimension files...")
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            dimension_writer = CanonicalModelWriter(self.output_dir)
            dimension_paths = dimension_writer.write_all(canonical_model, endpoint_flows)
            
            # Write combined architecture_facts.json (aggregated)
            combined_path = dimension_writer.write_combined(canonical_model, endpoint_flows)
            
            logger.info("\n" + "=" * 60)
            logger.info("[Phase1] Architecture Facts Extraction COMPLETE")
            logger.info("=" * 60)
            logger.info(f"[Phase1] System: {results.system_name}")
            logger.info(f"[Phase1] Containers: {stats['containers']}")
            logger.info(f"[Phase1] Components: {stats['components']}")
            logger.info(f"[Phase1] Interfaces: {stats['interfaces']}")
            logger.info(f"[Phase1] Relations: {stats['relations']}")
            logger.info(f"[Phase1] Evidence: {stats['evidence']}")
            logger.info(f"[Phase1] Dependencies: {stats['dependencies']}")
            logger.info(f"[Phase1] Workflows: {stats['workflows']}")
            logger.info(f"[Phase1] Entities: {len(results.entities)}")
            logger.info(f"[Phase1] Tables: {len(results.tables)}")
            logger.info(f"[Phase1] Migrations: {len(results.migrations)}")
            logger.info(f"[Phase1] Infrastructure: {len(results.infrastructure)}")
            logger.info(f"[Phase1] Output: {combined_path}")
            
            return {
                "phase": "phase1_architecture_facts",
                "status": "success",
                "dimension_paths": {k: str(v) for k, v in dimension_paths.items()},
                "statistics": {
                    **stats,
                    "entities": len(results.entities),
                    "tables": len(results.tables),
                    "migrations": len(results.migrations),
                    "infrastructure": len(results.infrastructure),
                    "endpoint_flows": len(endpoint_flows),
                },
            }
            
        except Exception as e:
            logger.error(f"[Phase1] Error: {e}", exc_info=True)
            return {
                "phase": "phase1_architecture_facts",
                "status": "failed",
                "error": str(e),
            }
