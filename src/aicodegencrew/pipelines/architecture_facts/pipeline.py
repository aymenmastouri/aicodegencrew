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

from pathlib import Path
from typing import Any

from ...shared.utils.logger import logger
from .collectors.fact_adapter import DimensionResultsAdapter
from .collectors.orchestrator import CollectorOrchestrator, DimensionResults
from .dimension_writers import CanonicalModelWriter
from .endpoint_flow_builder import EndpointFlowBuilder
from .model_builder import ArchitectureModelBuilder


class ArchitectureFactsPipeline:
    """
    Phase 1: Architecture Facts Pipeline

    Deterministic extraction - NO LLM!

    Outputs (Dimension Files):
    - knowledge/extract/system.json
    - knowledge/extract/containers.json
    - knowledge/extract/components.json
    - knowledge/extract/interfaces.json
    - knowledge/extract/relations.json
    - knowledge/extract/data_model.json
    - knowledge/extract/runtime.json
    - knowledge/extract/infrastructure.json
    - knowledge/extract/evidence_map.json
    """

    def __init__(
        self,
        repo_path: str,
        output_dir: str | None = None,
    ):
        """
        Initialize the Architecture Facts Pipeline.

        Args:
            repo_path: Path to the repository to analyze
            output_dir: Output directory (defaults to knowledge/extract)
        """
        self.repo_path = Path(repo_path).resolve()
        self.output_dir = Path(output_dir) if output_dir else (Path(".") / "knowledge" / "extract").resolve()

        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {self.repo_path}")

        logger.info("[Extract] ArchitectureFactsPipeline initialized")
        logger.info(f"[Extract] Repository: {self.repo_path}")
        logger.info(f"[Extract] Output: {self.output_dir}")

    def _fact_to_dict(self, fact) -> dict[str, Any]:
        """Convert a RawFact to dictionary."""
        result = {
            "name": getattr(fact, "name", "unknown"),
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
        ]:
            if hasattr(fact, attr):
                val = getattr(fact, attr)
                if val is not None and val != "" and val != []:
                    result[attr] = val

        # Add evidence
        if hasattr(fact, "evidence") and fact.evidence:
            result["evidence"] = [e.to_dict() if hasattr(e, "to_dict") else e for e in fact.evidence]

        return result

    def _clean_old_outputs(self) -> None:
        """Delete old Phase 1 outputs before new run."""
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

        deleted = 0
        for filename in output_files:
            f = self.output_dir / filename
            if f.exists():
                f.unlink()
                deleted += 1

        if deleted:
            logger.info(f"   [OK] {deleted} old files deleted")
        else:
            logger.info("   [OK] No old outputs to clean (first run)")

    def kickoff(self, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Execute the Architecture Facts Pipeline.

        Args:
            inputs: Optional input parameters (for orchestrator compatibility)

        Returns:
            Dictionary with extraction results
        """
        logger.info("[Extract] Mode: DETERMINISTIC (no LLM)")

        # Step 0: Clean old outputs
        logger.info("[Extract] Step 0: Clean old outputs...")
        self._clean_old_outputs()

        try:
            # Step 1: Run all collectors via orchestrator
            # Pass output_dir so each collector writes JSON immediately after completion
            logger.info("\n[Extract] Step 1: Running collectors...")
            orchestrator = CollectorOrchestrator(self.repo_path, output_dir=self.output_dir)
            results: DimensionResults = orchestrator.run_all()

            # Step 2: Adapt raw facts to model format
            logger.info("\n[Extract] Step 2: Adapting facts to model format...")
            adapter = DimensionResultsAdapter(self.repo_path)
            adapted = adapter.convert(results)

            # Step 3: Build canonical architecture model
            logger.info("\n[Extract] Step 3: Building canonical architecture model...")
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
            canonical_model.dependencies = [self._fact_to_dict(d) for d in results.dependencies]
            canonical_model.workflows = [self._fact_to_dict(w) for w in results.workflows]
            canonical_model.data_model = {
                "entities": [self._fact_to_dict(e) for e in results.entities],
                "tables": [self._fact_to_dict(t) for t in results.tables],
                "migrations": [self._fact_to_dict(m) for m in results.migrations],
            }
            canonical_model.runtime = [self._fact_to_dict(r) for r in results.runtime]
            canonical_model.infrastructure = [self._fact_to_dict(i) for i in results.infrastructure]
            canonical_model.tech_versions = [self._fact_to_dict(tv) for tv in getattr(results, "tech_versions", [])]
            canonical_model.security_details = [self._fact_to_dict(s) for s in getattr(results, "security_details", [])]
            canonical_model.validation = [self._fact_to_dict(v) for v in getattr(results, "validation", [])]
            canonical_model.tests = [self._fact_to_dict(t) for t in getattr(results, "tests", [])]
            canonical_model.error_handling = [self._fact_to_dict(e) for e in getattr(results, "error_handling", [])]
            canonical_model.build_system = [self._fact_to_dict(b) for b in getattr(results, "build_system", [])]

            stats = canonical_model.get_statistics()
            logger.info(f"[Extract] Canonical model: {stats['components']} components, {stats['relations']} relations")
            logger.info(f"[Extract] Dependencies: {stats['dependencies']}, Workflows: {stats['workflows']}")
            logger.info(
                f"[Extract] Security: {stats.get('security_details', 0)}, Validation: {stats.get('validation', 0)}, Tests: {stats.get('tests', 0)}, Errors: {stats.get('error_handling', 0)}"
            )

            # Step 4: Build endpoint flows
            logger.info("\n[Extract] Step 4: Building endpoint flows...")
            flow_builder = EndpointFlowBuilder(
                components=adapted["components"],
                interfaces=adapted["interfaces"],
                relations=adapted["relations"],
                evidence=adapted["evidence"],
            )
            endpoint_flows = flow_builder.build_flows()
            logger.info(f"[Extract] Built {len(endpoint_flows)} endpoint flows")

            # Step 5: Write dimension files
            logger.info("\n[Extract] Step 5: Writing dimension files...")
            self.output_dir.mkdir(parents=True, exist_ok=True)

            dimension_writer = CanonicalModelWriter(self.output_dir)
            dimension_paths = dimension_writer.write_all(canonical_model, endpoint_flows)

            # Write combined architecture_facts.json (aggregated)
            combined_path = dimension_writer.write_combined(canonical_model, endpoint_flows)

            logger.info(f"[Extract] System: {results.system_name}")
            logger.info(f"[Extract] Containers: {stats['containers']}")
            logger.info(f"[Extract] Components: {stats['components']}")
            logger.info(f"[Extract] Interfaces: {stats['interfaces']}")
            logger.info(f"[Extract] Relations: {stats['relations']}")
            logger.info(f"[Extract] Evidence: {stats['evidence']}")
            logger.info(f"[Extract] Dependencies: {stats['dependencies']}")
            logger.info(f"[Extract] Workflows: {stats['workflows']}")
            logger.info(f"[Extract] Entities: {len(results.entities)}")
            logger.info(f"[Extract] Tables: {len(results.tables)}")
            logger.info(f"[Extract] Migrations: {len(results.migrations)}")
            logger.info(f"[Extract] Infrastructure: {len(results.infrastructure)}")
            logger.info(f"[Extract] Output: {combined_path}")

            return {
                "phase": "extract",
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
            logger.error(f"[Extract] Error: {e}", exc_info=True)
            return {
                "phase": "extract",
                "status": "failed",
                "error": str(e),
            }
