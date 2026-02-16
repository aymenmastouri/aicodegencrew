"""
Phase Output Validation
========================
Validates data contracts between SDLC phases.

Each phase has required output files with expected structure.
Validation runs before a dependent phase starts.

Usage:
    validator = PhaseOutputValidator()
    errors = validator.validate_phase("extract")
    if errors:
        raise ValueError(f"Extract phase output invalid: {errors}")
"""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .models.architecture_facts_schema import ArchitectureFacts
from .utils.logger import setup_logger

logger = setup_logger(__name__)


# =============================================================================
# Phase Output Specifications
# =============================================================================

PHASE_OUTPUT_SPECS: dict[str, dict[str, Any]] = {
    "discover": {
        "required_paths": ["knowledge/discover"],
        "description": "ChromaDB vector index",
    },
    "extract": {
        "required_paths": [
            "knowledge/extract/architecture_facts.json",
            "knowledge/extract/evidence_map.json",
        ],
        "schema": "architecture_facts",
        "min_components": 1,
        "min_containers": 1,
        "description": "Architecture facts JSON (ground truth)",
    },
    "analyze": {
        "required_paths": [
            "knowledge/analyze/analyzed_architecture.json",
        ],
        "schema": "analyzed_architecture",
        # MapReduceAnalysisCrew output (current): see `crews/architecture_analysis/mapreduce_crew.py`.
        # Legacy outputs used `architecture`/`patterns`, but the current schema is:
        #   system, macro_architecture, micro_architecture, architecture_quality, ...
        "required_keys": [
            "system",
            "macro_architecture",
            "micro_architecture",
            "architecture_quality",
            "overall_grade",
            "executive_summary",
        ],
        "description": "AI-analyzed architecture JSON (MapReduce crew output)",
    },
    "document": {
        "required_paths": [
            "knowledge/document/c4/c4-context.md",
            "knowledge/document/c4/c4-container.md",
            "knowledge/document/c4/c4-component.md",
            "knowledge/document/c4/c4-deployment.md",
        ],
        "min_file_size": 500,  # Minimum bytes per output file
        "description": "C4 + Arc42 documentation",
    },
    "plan": {
        "required_paths": [
            "knowledge/plan",
        ],
        "schema": "development_plan",
        "description": "Development plans from hybrid pipeline",
    },
    "implement": {
        "required_paths": [
            "knowledge/implement",
        ],
        "schema": "codegen_report",
        "description": "Code generation reports",
    },
}


class PhaseOutputValidator:
    """Validates phase output files and data contracts."""

    def __init__(self):
        """Initialize. All paths are relative to CWD (project root)."""
        self._base = Path(".")

    def validate_phase(self, phase_id: str) -> list[str]:
        """
        Validate outputs for a completed phase.

        Returns list of error messages (empty = valid).
        """
        spec = PHASE_OUTPUT_SPECS.get(phase_id)
        if not spec:
            return []  # No spec defined = nothing to validate

        errors = []

        # 1. Check required files exist
        for path_str in spec.get("required_paths", []):
            path = self._base / path_str
            if not path.exists():
                errors.append(f"Missing output: {path_str}")
            elif path.is_file() and path.stat().st_size == 0:
                errors.append(f"Empty output: {path_str}")

        if errors:
            return errors  # Can't validate content without files

        # 2. Schema validation
        schema_type = spec.get("schema")
        if schema_type == "architecture_facts":
            errors.extend(self._validate_facts(spec))
        elif schema_type == "analyzed_architecture":
            errors.extend(self._validate_analysis(spec))
        elif schema_type == "development_plan":
            errors.extend(self._validate_development_plans(spec))
        elif schema_type == "codegen_report":
            errors.extend(self._validate_codegen_reports(spec))

        # 3. Minimum file size check
        min_size = spec.get("min_file_size", 0)
        if min_size:
            for path_str in spec.get("required_paths", []):
                path = Path(path_str)
                if path.is_file() and path.stat().st_size < min_size:
                    errors.append(f"Output too small: {path_str} ({path.stat().st_size} bytes, min {min_size})")

        return errors

    def validate_dependency(self, phase_id: str) -> list[str]:
        """
        Validate that a phase's dependencies are satisfied.

        This is called BEFORE a phase starts to ensure input data is valid.
        """
        from ..orchestrator import SDLCOrchestrator

        # Load config to find dependencies
        orchestrator = SDLCOrchestrator()
        phase_config = orchestrator.get_phase_config(phase_id)
        dependencies = phase_config.get("dependencies", [])

        all_errors = []
        for dep_id in dependencies:
            errors = self.validate_phase(dep_id)
            if errors:
                all_errors.append(f"Dependency {dep_id} invalid:")
                all_errors.extend(f"  - {e}" for e in errors)

        return all_errors

    # -------------------------------------------------------------------------
    # Schema-specific validators
    # -------------------------------------------------------------------------

    def _validate_facts(self, spec: dict) -> list[str]:
        """Validate architecture_facts.json against Pydantic schema."""
        errors = []
        facts_path = self._base / "knowledge/extract/architecture_facts.json"

        try:
            with open(facts_path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return [f"Invalid JSON in {facts_path}: {e}"]

        # Pydantic validation
        try:
            facts = ArchitectureFacts(**data)
        except ValidationError as e:
            return [f"Schema validation failed: {e.error_count()} errors"]

        # Content validation
        min_comp = spec.get("min_components", 0)
        if len(facts.components) < min_comp:
            errors.append(f"Too few components: {len(facts.components)} (min {min_comp})")

        min_cont = spec.get("min_containers", 0)
        if len(facts.containers) < min_cont:
            errors.append(f"Too few containers: {len(facts.containers)} (min {min_cont})")

        # Evidence cross-reference
        evidence_path = self._base / "knowledge/extract/evidence_map.json"
        if evidence_path.exists():
            try:
                with open(evidence_path, encoding="utf-8") as f:
                    evidence_data = json.load(f)
                ev_errors = facts.validate_evidence(evidence_data)
                if ev_errors:
                    errors.append(f"Evidence validation: {len(ev_errors)} broken references")
            except Exception:
                pass

        return errors

    def _validate_analysis(self, spec: dict) -> list[str]:
        """Validate analyzed_architecture.json structure."""
        errors = []
        analysis_path = self._base / "knowledge/analyze/analyzed_architecture.json"

        try:
            with open(analysis_path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return [f"Invalid JSON in {analysis_path}: {e}"]

        # Check required top-level keys
        for key in spec.get("required_keys", []):
            if key not in data:
                errors.append(f"Missing key '{key}' in analysis output")

        return errors

    def _validate_development_plans(self, spec: dict) -> list[str]:
        """Validate development plan JSON files."""
        errors = []
        plans_dir = self._base / "knowledge/plan"

        if not plans_dir.is_dir():
            return []  # Directory existence already checked

        plan_files = list(plans_dir.glob("*_plan.json"))
        if not plan_files:
            errors.append("No plan files (*_plan.json) in knowledge/plan/")
            return errors

        required_keys = {"task_id", "understanding", "development_plan"}
        plan_required_keys = {"affected_components", "implementation_steps"}

        for plan_file in plan_files:
            try:
                with open(plan_file, encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON in {plan_file.name}: {e}")
                continue

            missing = required_keys - set(data.keys())
            if missing:
                errors.append(f"{plan_file.name}: missing top-level keys: {missing}")

            dev_plan = data.get("development_plan", {})
            if isinstance(dev_plan, dict):
                plan_missing = plan_required_keys - set(dev_plan.keys())
                if plan_missing:
                    errors.append(f"{plan_file.name}: development_plan missing keys: {plan_missing}")

        return errors

    def _validate_codegen_reports(self, spec: dict) -> list[str]:
        """Validate code generation report JSON files."""
        errors = []
        reports_dir = self._base / "knowledge/implement"

        if not reports_dir.is_dir():
            return []  # Directory existence already checked

        report_files = list(reports_dir.glob("*_report.json"))
        if not report_files:
            # Codegen may not have produced reports yet — not an error for dependency check
            return []

        required_keys = {"task_id", "status"}

        for report_file in report_files:
            try:
                with open(report_file, encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON in {report_file.name}: {e}")
                continue

            missing = required_keys - set(data.keys())
            if missing:
                errors.append(f"{report_file.name}: missing keys: {missing}")

        return errors
