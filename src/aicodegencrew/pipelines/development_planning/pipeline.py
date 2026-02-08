"""
Development Planning Pipeline (Phase 4)

HYBRID ARCHITECTURE:
- Stages 1-3: Deterministic (parsing, RAG, pattern matching)
- Stage 4: LLM (plan generation)
- Stage 5: Deterministic (validation)

Total Duration: 18-40 seconds
LLM Calls: 1 (only in Stage 4)
Success Rate: 95%+ (deterministic stages don't fail)
"""

import json
import time
from pathlib import Path
from typing import Dict, Any

from .stages import (
    InputParserStage,
    ComponentDiscoveryStage,
    PatternMatcherStage,
    PlanGeneratorStage,
    ValidatorStage,
)
from .schemas import ImplementationPlan
from ...shared.utils.logger import setup_logger, log_metric, step_start, step_done, step_fail

logger = setup_logger(__name__)


class DevelopmentPlanningPipeline:
    """
    Phase 4: Development Planning Pipeline.

    Hybrid architecture with 5 stages:
    1. Input Parser (deterministic)
    2. Component Discovery (RAG + scoring)
    3. Pattern Matcher (TF-IDF + rules)
    4. Plan Generator (LLM)
    5. Validator (Pydantic)
    """

    def __init__(
        self,
        input_file: str,
        facts_path: str = "knowledge/architecture/architecture_facts.json",
        analyzed_path: str = "knowledge/architecture/analyzed_architecture.json",
        output_dir: str = "knowledge/development",
        chroma_dir: str = None,
    ):
        """
        Initialize development planning pipeline.

        Args:
            input_file: Task input file (JIRA XML, DOCX, Excel, log)
            facts_path: Path to architecture_facts.json (Phase 1)
            analyzed_path: Path to analyzed_architecture.json (Phase 2)
            output_dir: Output directory for plans
            chroma_dir: ChromaDB directory (Phase 0)
        """
        self.input_file = input_file
        self.facts_path = Path(facts_path)
        self.analyzed_path = Path(analyzed_path)
        self.output_dir = Path(output_dir)
        self.chroma_dir = chroma_dir

        # Ensure output dir exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load architecture data
        self.facts = self._load_json(self.facts_path)
        self.analyzed_architecture = self._load_json(self.analyzed_path)

        # Create stages
        self.stage1 = InputParserStage()
        self.stage2 = ComponentDiscoveryStage(
            facts=self.facts,
            chroma_dir=self.chroma_dir,
        )
        self.stage3 = PatternMatcherStage(facts=self.facts)
        self.stage4 = PlanGeneratorStage(analyzed_architecture=self.analyzed_architecture)
        self.stage5 = ValidatorStage(analyzed_architecture=self.analyzed_architecture)

    def kickoff(self, inputs: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute pipeline (Orchestrator-compatible interface).

        Args:
            inputs: Optional inputs (not used, input_file from __init__)

        Returns:
            Dict with status, output_file, metrics
        """
        return self.run()

    def run(self) -> Dict[str, Any]:
        """
        Run all 5 stages sequentially.

        Returns:
            Dict with status, output_file, duration, metrics
        """
        start_time = time.time()

        logger.info("=" * 80)
        logger.info("[Phase4] Development Planning Pipeline - HYBRID ARCHITECTURE")
        logger.info(f"[Phase4] Input: {self.input_file}")
        logger.info("=" * 80)

        try:
            # Stage 1: Input Parser
            step_start("Stage 1: Input Parser")
            stage1_start = time.time()
            task = self.stage1.run(self.input_file)
            stage1_duration = time.time() - stage1_start
            step_done("Stage 1: Input Parser", duration=stage1_duration)

            log_metric("stage_complete", {
                "phase": "phase4_development_planning",
                "stage": "stage1_input_parser",
                "duration_seconds": stage1_duration,
                "task_id": task.task_id,
            })

            # Stage 2: Component Discovery
            step_start("Stage 2: Component Discovery (RAG + Scoring)")
            stage2_start = time.time()
            discovery_result = self.stage2.run(task, top_k=10)
            stage2_duration = time.time() - stage2_start
            step_done("Stage 2: Component Discovery", duration=stage2_duration)

            log_metric("stage_complete", {
                "phase": "phase4_development_planning",
                "stage": "stage2_component_discovery",
                "duration_seconds": stage2_duration,
                "components_found": len(discovery_result["affected_components"]),
            })

            # Stage 3: Pattern Matching
            step_start("Stage 3: Pattern Matching (TF-IDF + Rules)")
            stage3_start = time.time()
            pattern_result = self.stage3.run(
                task,
                discovery_result["affected_components"],
                top_k=5,
            )
            stage3_duration = time.time() - stage3_start
            step_done("Stage 3: Pattern Matching", duration=stage3_duration)

            log_metric("stage_complete", {
                "phase": "phase4_development_planning",
                "stage": "stage3_pattern_matcher",
                "duration_seconds": stage3_duration,
                "test_patterns": len(pattern_result["test_patterns"]),
                "security_patterns": len(pattern_result["security_patterns"]),
                "validation_patterns": len(pattern_result["validation_patterns"]),
                "error_patterns": len(pattern_result["error_patterns"]),
            })

            # Stage 4: Plan Generation (LLM)
            step_start("Stage 4: Plan Generation (LLM Call)")
            stage4_start = time.time()
            plan = self.stage4.run(task, discovery_result, pattern_result)
            stage4_duration = time.time() - stage4_start
            step_done("Stage 4: Plan Generation", duration=stage4_duration)

            log_metric("stage_complete", {
                "phase": "phase4_development_planning",
                "stage": "stage4_plan_generator",
                "duration_seconds": stage4_duration,
                "llm_call": True,
            })

            # Stage 5: Validation
            step_start("Stage 5: Validation")
            stage5_start = time.time()
            validation = self.stage5.run(plan)
            stage5_duration = time.time() - stage5_start

            if not validation.is_valid:
                step_fail("Stage 5: Validation")
                logger.error(f"[Phase4] Validation failed:")
                for error in validation.errors:
                    logger.error(f"  - {error}")
                for field in validation.missing_fields:
                    logger.error(f"  - Missing: {field}")
                raise ValueError(f"Plan validation failed: {validation.errors}")

            if validation.warnings:
                logger.warning(f"[Phase4] Validation warnings:")
                for warning in validation.warnings:
                    logger.warning(f"  - {warning}")

            step_done("Stage 5: Validation", duration=stage5_duration)

            log_metric("stage_complete", {
                "phase": "phase4_development_planning",
                "stage": "stage5_validator",
                "duration_seconds": stage5_duration,
                "is_valid": validation.is_valid,
                "warnings": len(validation.warnings),
            })

            # Write plan to file
            output_file = self.output_dir / f"{task.task_id}_plan.json"
            self._write_plan(plan, output_file)

            total_duration = time.time() - start_time

            logger.info("=" * 80)
            logger.info(f"[Phase4] ✅ Pipeline completed successfully")
            logger.info(f"[Phase4] Task ID: {task.task_id}")
            logger.info(f"[Phase4] Output: {output_file}")
            logger.info(f"[Phase4] Total Duration: {total_duration:.2f}s")
            logger.info(f"[Phase4]   Stage 1 (Input Parser): {stage1_duration:.2f}s")
            logger.info(f"[Phase4]   Stage 2 (Component Discovery): {stage2_duration:.2f}s")
            logger.info(f"[Phase4]   Stage 3 (Pattern Matching): {stage3_duration:.2f}s")
            logger.info(f"[Phase4]   Stage 4 (Plan Generation - LLM): {stage4_duration:.2f}s")
            logger.info(f"[Phase4]   Stage 5 (Validation): {stage5_duration:.2f}s")
            logger.info("=" * 80)

            log_metric("phase_complete", {
                "phase": "phase4_development_planning",
                "status": "success",
                "duration_seconds": total_duration,
                "task_id": task.task_id,
                "output_file": str(output_file),
                "components_found": len(discovery_result["affected_components"]),
                "test_patterns_found": len(pattern_result["test_patterns"]),
            })

            return {
                "status": "completed",
                "task_id": task.task_id,
                "output_file": str(output_file),
                "duration_seconds": total_duration,
                "metrics": {
                    "stage1_duration": stage1_duration,
                    "stage2_duration": stage2_duration,
                    "stage3_duration": stage3_duration,
                    "stage4_duration": stage4_duration,
                    "stage5_duration": stage5_duration,
                    "components_found": len(discovery_result["affected_components"]),
                    "test_patterns": len(pattern_result["test_patterns"]),
                    "security_patterns": len(pattern_result["security_patterns"]),
                    "validation_warnings": len(validation.warnings),
                },
            }

        except Exception as e:
            total_duration = time.time() - start_time
            logger.error(f"[Phase4] Pipeline failed: {e}", exc_info=True)

            log_metric("phase_failed", {
                "phase": "phase4_development_planning",
                "error": str(e),
                "duration_seconds": total_duration,
            })

            raise

    def _load_json(self, path: Path) -> dict:
        """Load JSON file."""
        if not path.exists():
            logger.warning(f"[Phase4] File not found: {path}, using empty dict")
            return {}

        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[Phase4] Failed to load {path}: {e}")
            return {}

    def _write_plan(self, plan: ImplementationPlan, output_file: Path):
        """Write plan to JSON file."""
        try:
            plan_dict = plan.dict()

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(plan_dict, f, indent=2, ensure_ascii=False)

            logger.info(f"[Phase4] Plan written to: {output_file}")

        except Exception as e:
            logger.error(f"[Phase4] Failed to write plan: {e}")
            raise
