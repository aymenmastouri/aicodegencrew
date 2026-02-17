"""Task-type strategy interface and registry.

Each task type can register custom behavior for 3 pipeline hooks:
1. enrich_plan     — validate feasibility, add context to plan
2. pre_execute     — deterministic steps before LLM code generation
3. enrich_verification — rich reporting after build-fix loop
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# ── Result types (shared by all strategies) ──────────────────────────────


@dataclass
class PlanEnrichment:
    """Additional context added to a plan by a strategy."""

    compatibility_checks: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    additional_context: dict = field(default_factory=dict)  # injected into LLM prompt


@dataclass
class PreExecutionStep:
    """Result of a single deterministic pre-execution step."""

    step_type: str  # "schematic" | "config_change" | "version_bump" | "codemod" | "scaffold"
    rule_id: str  # identifier for what triggered this step
    description: str
    success: bool = False
    modified_files: list[str] = field(default_factory=list)
    error: str = ""
    output: str = ""


@dataclass
class PreExecutionResult:
    """Aggregated result of all pre-execution steps."""

    steps: list[PreExecutionStep] = field(default_factory=list)
    total_files_modified: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class ErrorCluster:
    """A group of build errors sharing a pattern/root cause."""

    pattern: str
    error_code: str = ""
    count: int = 0
    files: list[str] = field(default_factory=list)
    suggested_fix: str = ""
    root_cause: str = ""


@dataclass
class VerificationEnrichment:
    """Rich verification data produced by a strategy."""

    error_clusters: list[ErrorCluster] = field(default_factory=list)
    deprecation_warnings: list[dict] = field(default_factory=list)
    task_specific: dict = field(default_factory=dict)
    pre_execution_summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_clusters": [
                {
                    "pattern": c.pattern,
                    "error_code": c.error_code,
                    "count": c.count,
                    "files": c.files,
                    "suggested_fix": c.suggested_fix,
                    "root_cause": c.root_cause,
                }
                for c in self.error_clusters
            ],
            "deprecation_warnings": self.deprecation_warnings,
            "task_specific": self.task_specific,
            "pre_execution_summary": self.pre_execution_summary,
        }


# ── Strategy interface ───────────────────────────────────────────────────


class TaskTypeStrategy(ABC):
    """Base class for task-type-specific pipeline behavior."""

    @abstractmethod
    def enrich_plan(
        self,
        plan_data: dict,  # raw plan dict (pre-CodegenPlanInput)
        facts: dict,  # architecture_facts
    ) -> PlanEnrichment:
        """Validate feasibility and add task-type-specific context."""
        ...

    @abstractmethod
    def pre_execute(
        self,
        plan: Any,  # CodegenPlanInput
        staging: dict[str, dict],  # shared staging dict
        repo_path: str,
        dry_run: bool = False,
    ) -> PreExecutionResult:
        """Execute deterministic steps before LLM code generation."""
        ...

    @abstractmethod
    def enrich_verification(
        self,
        build_result: Any,  # BuildVerificationResult
        staging: dict[str, dict],
        plan: Any,  # CodegenPlanInput
        raw_build_outputs: list[str],
        pre_execution_result: PreExecutionResult | None = None,
    ) -> VerificationEnrichment:
        """Build rich verification report after build-fix loop."""
        ...

    # ── Shared utilities (reusable by all strategies) ────────────────────

    def _cluster_errors(self, build_result: Any) -> list[ErrorCluster]:
        """Group build errors by pattern. Reusable by all strategies."""
        if build_result is None:
            return []

        container_results = getattr(build_result, "container_results", [])
        if not container_results:
            return []

        # Collect all error lines from failed containers
        error_lines: list[tuple[str, str]] = []  # (file, message)
        for cr in container_results:
            if cr.success:
                continue
            summary = getattr(cr, "error_summary", "") or ""
            for segment in summary.split(";"):
                segment = segment.strip()
                if not segment:
                    continue
                # Parse "file_path:line message" format
                match = re.match(r"(.+?\.(?:java|ts|html|scss|xml|json|kt)):\d+\s+(.*)", segment)
                if match:
                    error_lines.append((match.group(1).strip(), match.group(2).strip()))
                else:
                    error_lines.append(("unknown", segment))

        if not error_lines:
            return []

        # Cluster by message pattern (first 60 chars as key)
        clusters: dict[str, ErrorCluster] = {}
        for file_path, message in error_lines:
            # Normalize: strip file-specific parts, keep error pattern
            pattern_key = re.sub(r"'[^']*'", "'...'", message)[:60]
            if pattern_key not in clusters:
                clusters[pattern_key] = ErrorCluster(pattern=pattern_key)
            cluster = clusters[pattern_key]
            cluster.count += 1
            if file_path not in cluster.files:
                cluster.files.append(file_path)

        return sorted(clusters.values(), key=lambda c: c.count, reverse=True)


# ── Registry ─────────────────────────────────────────────────────────────

_STRATEGY_REGISTRY: dict[str, type[TaskTypeStrategy]] = {}


def register_strategy(task_type: str):
    """Decorator to register a strategy class for a task type."""

    def decorator(cls: type[TaskTypeStrategy]):
        _STRATEGY_REGISTRY[task_type] = cls
        return cls

    return decorator


def get_strategy(task_type: str) -> TaskTypeStrategy:
    """Get strategy instance for a task type. Falls back to DefaultStrategy."""
    cls = _STRATEGY_REGISTRY.get(task_type)
    if cls is None:
        cls = _STRATEGY_REGISTRY.get("_default", DefaultStrategy)
    return cls()


# ── Default (no-op) strategy ─────────────────────────────────────────────


@register_strategy("_default")
@register_strategy("feature")
@register_strategy("bugfix")
class DefaultStrategy(TaskTypeStrategy):
    """No-op strategy for task types without special handling."""

    def enrich_plan(self, plan_data, facts) -> PlanEnrichment:
        return PlanEnrichment()

    def pre_execute(self, plan, staging, repo_path, dry_run=False) -> PreExecutionResult:
        return PreExecutionResult()

    def enrich_verification(
        self, build_result, staging, plan, raw_build_outputs,
        pre_execution_result=None,
    ) -> VerificationEnrichment:
        # Error clustering is universal — applies to ALL task types
        return VerificationEnrichment(
            error_clusters=self._cluster_errors(build_result),
        )
