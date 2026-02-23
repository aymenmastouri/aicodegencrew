#!/usr/bin/env python3
"""
AI Code Generation Crew - Unified CLI

Modern CLI with subcommands:
    aicodegencrew run              Run SDLC pipeline
    aicodegencrew plan             Run development planning
    aicodegencrew index            Index repository
    aicodegencrew list             List available phases

Usage:
    python -m aicodegencrew run --preset document
    python -m aicodegencrew run --phases extract
    python -m aicodegencrew --env /path/to/.env plan
    python -m aicodegencrew index --force
    python -m aicodegencrew list
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
import warnings
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .orchestrator import PipelineResult, SDLCOrchestrator

# Suppress noisy warnings from dependencies
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic")
warnings.filterwarnings("ignore", message=".*Pydantic.*")
warnings.filterwarnings("ignore", message=".*LangChain.*")

from dotenv import load_dotenv

from .phase_registry import PHASES, get_cleanup_targets

# load_dotenv moved into main() to support --env flag
from .pipeline_contract import build_pipeline_contract
from .shared.utils.logger import logger

# =============================================================================
# Configuration
# =============================================================================


@dataclass(frozen=True)
class Config:
    """Immutable CLI configuration."""

    repo_path: Path
    index_mode: str
    config_path: str | None
    clean: bool
    no_clean: bool
    git_repo_url: str
    git_branch: str
    dry_run: bool = False
    task_id: str | None = None

    @classmethod
    def from_env(cls, **overrides) -> Config:
        """Create config from environment with optional overrides."""
        repo = overrides.get("repo_path") or os.getenv("PROJECT_PATH") or os.getenv("REPO_PATH", ".")
        mode = overrides.get("index_mode") or os.getenv("INDEX_MODE", "auto")

        # Validate index_mode
        valid_modes = ("off", "auto", "force", "smart")
        mode = mode.lower().strip()
        if mode not in valid_modes:
            logger.warning(f"[WARN] Unknown INDEX_MODE '{mode}', defaulting to 'auto'")
            mode = "auto"

        # Git repo URL: CLI override > env > empty (disabled)
        git_url = overrides.get("git_repo_url") or os.getenv("GIT_REPO_URL", "")
        git_branch = overrides.get("git_branch") or os.getenv("GIT_BRANCH", "")

        return cls(
            repo_path=Path(repo),
            index_mode=mode,
            config_path=overrides.get("config_path"),
            clean=overrides.get("clean", False),
            no_clean=overrides.get("no_clean", False),
            git_repo_url=git_url.strip(),
            git_branch=git_branch.strip(),
            dry_run=overrides.get("dry_run", False),
            task_id=overrides.get("task_id"),
        )


# =============================================================================
# Logging Setup
# =============================================================================


def setup_logging() -> None:
    """Configure logging for CrewAI and dependencies."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    logging.getLogger().setLevel(getattr(logging, log_level))

    # Quiet noisy loggers
    for noisy in ("httpx", "httpcore", "chromadb", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    for very_noisy in ("litellm", "LiteLLM"):
        logging.getLogger(very_noisy).setLevel(logging.ERROR)

    # Keep our logs visible
    logging.getLogger("crewai").setLevel(logging.INFO)
    logging.getLogger("aicodegencrew").setLevel(getattr(logging, log_level))

    logger.info(f"[CONFIG] LOG_LEVEL = {log_level}")


# =============================================================================
# Knowledge Directory Management
# =============================================================================


def clean_knowledge(phase: str = "all") -> None:
    """Clean knowledge directory before running a phase.

    Args:
        phase: Phase ID or "all". Cleans relative to CWD.
    """
    base = Path(".")

    cleaned: list[str] = []

    phases_to_clean = list(PHASES) if phase == "all" else [phase]
    for pid in phases_to_clean:
        for rel in get_cleanup_targets(pid):
            target = base / rel
            if target.exists():
                shutil.rmtree(target)
                cleaned.append(str(target))

    if cleaned:
        logger.info(f"[CLEAN] Removed {len(cleaned)} items")


# =============================================================================
# Git Repository Resolution
# =============================================================================


def _resolve_repo_path(config: Config) -> Path:
    """Resolve the effective repository path.

    If GIT_REPO_URL is set, clone/pull the repo and return the local clone path.
    Otherwise, return config.repo_path as-is (backward-compatible).
    """
    if not config.git_repo_url:
        return config.repo_path

    from .shared.utils.git_repo_manager import GitRepoManager

    manager = GitRepoManager(
        repo_url=config.git_repo_url,
        branch=config.git_branch,
    )
    return manager.ensure_repo()


# =============================================================================
# Commands
# =============================================================================


def cmd_list(config: Config) -> int:
    """List all available phases."""
    from .orchestrator import SDLCOrchestrator

    orchestrator = SDLCOrchestrator(config_path=config.config_path)

    print("\n" + "=" * 60)
    print("Available SDLC Phases")
    print("=" * 60)
    print(f"\n[CONFIG] INDEX_MODE = {config.index_mode}\n")

    phases_config = orchestrator.config.get("phases", {})
    for phase_id, phase_cfg in sorted(phases_config.items(), key=lambda x: x[1].get("order", 999)):
        enabled = "[ON]" if phase_cfg.get("enabled", False) else "[OFF]"
        required = " (REQUIRED)" if phase_cfg.get("required", False) else ""
        name = phase_cfg.get("name", phase_id)
        order = phase_cfg.get("order", "?")

        print(f"{enabled} Phase {order}: {name}{required}")
        print(f"       ID: {phase_id}")

    print("\n" + "=" * 60)
    print("\nPresets:")
    for preset_name in orchestrator.config.get("presets", {}):
        print(f"  --preset {preset_name}")
    print()

    return 0


def cmd_index(config: Config) -> int:
    """Run indexing pipeline only."""
    from .pipelines.indexing import ensure_repo_indexed
    from .shared.paths import get_chroma_dir
    from .shared.project_context import derive_project_slug, set_active_project

    repo_path = _resolve_repo_path(config)
    project_slug = derive_project_slug(repo_path)
    chroma_dir = Path(get_chroma_dir(project_slug))

    logger.info("=" * 60)
    logger.info("INDEXING PIPELINE")
    logger.info("=" * 60)
    logger.info(f"Repository : {repo_path}")
    logger.info(f"Project    : {project_slug}")
    logger.info(f"INDEX_MODE : {config.index_mode}")
    logger.info(f"ChromaDB   : {chroma_dir}")
    logger.info("")

    if config.index_mode == "off":
        logger.info("[SKIP] INDEX_MODE=off - Indexing disabled")
        return 0

    force_reindex = False
    if config.index_mode == "force":
        force_reindex = True
    elif config.index_mode == "smart":
        logger.info("[SMART] Incremental update only")
    else:
        logger.info("[AUTO] Index if needed")

    try:
        ensure_repo_indexed(str(repo_path), force_reindex=force_reindex)
        set_active_project(project_slug, str(repo_path))
        logger.info("\n[OK] Indexing completed!")
        return 0
    except KeyboardInterrupt:
        logger.warning("\n[WARN] Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"[ERROR] Indexing failed: {e}")
        return 1


def _resolve_phases_to_run(
    orchestrator: SDLCOrchestrator,
    preset: str | None,
    phases: list[str] | None,
) -> set[str]:
    """Resolve which phases will run based on preset or explicit phases.

    Uses phases_config.yaml as single source of truth instead of fragile
    string matching.
    """
    contract = build_pipeline_contract(orchestrator.config, config_path=orchestrator.config_path)

    if phases:
        # Validate explicit phase names against config
        known_phases = set(contract.get_phase_ids())
        unknown = set(contract.get_unknown_phases(phases))
        if unknown:
            raise ValueError(
                f"Unknown phase(s): {', '.join(sorted(unknown))}. Valid phases: {', '.join(sorted(known_phases))}"
            )
        return set(phases)

    if preset:
        # Validate preset name against config
        preset_phases = contract.get_preset_phases(preset)
        if not preset_phases:
            known_presets = contract.get_preset_names()
            raise ValueError(f"Unknown preset: '{preset}'. Valid presets: {', '.join(known_presets)}")
        return set(preset_phases)

    # Default: all enabled phases
    return set(contract.get_enabled_phases())


def _export_run_report(
    result: PipelineResult,
    config: Config,
    planned_phases: set[str],
    knowledge_dir: Path | None = None,
) -> Path | None:
    """Export run_report.json to knowledge/ directory.

    Provides the end user with a persistent record of what happened
    during the pipeline run — visible alongside the generated artifacts.
    """
    import json

    from .shared.utils.logger import CURRENT_LOG, METRICS_LOG, RUN_ID

    report_dir = knowledge_dir or Path("knowledge")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "run_report.json"
    base = report_dir.parent  # repo_path

    phases_detail = []
    for pr in result.phases:
        detail = pr.to_dict()
        detail["duration_seconds"] = round(pr.duration_seconds, 2)
        # List actual output files from registry cleanup targets
        expected = [str(base / rel) for rel in get_cleanup_targets(pr.phase_id)]
        detail["output_files"] = [f for f in expected if Path(f).exists()]
        phases_detail.append(detail)

    from .pipeline_contract import compute_run_outcome

    phase_statuses = [pr.status for pr in result.phases]
    run_outcome = (
        compute_run_outcome(iter(phase_statuses))
        if phase_statuses
        else ("success" if result.status == "completed" else "failed")
    )

    report = {
        "run_id": RUN_ID,
        "timestamp": datetime.now().isoformat(),
        "status": result.status,
        "run_outcome": run_outcome,
        "message": result.message,
        "total_duration": result.total_duration,
        "planned_phases": sorted(planned_phases),
        "environment": {
            "repo_path": str(config.repo_path),
            "index_mode": config.index_mode,
            "git_repo_url": config.git_repo_url or None,
        },
        "phases": phases_detail,
        "output_summary": {
            "knowledge_dir": str(report_dir),
            "log_file": str(CURRENT_LOG),
            "metrics_file": str(METRICS_LOG),
        },
    }

    try:
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"[REPORT] Run report exported: {report_path}")
        return report_path
    except Exception as e:
        logger.warning(f"[REPORT] Failed to write run report: {e}")
        return None


def _export_architecture_docs(knowledge_dir: Path | None = None):
    """Copy Phase 3 architecture docs (C4 + Arc42) to export dir.

    Default: <output_base>/architecture-docs. Override with DOCS_OUTPUT_DIR in .env.
    """
    import shutil

    docs_dir = os.getenv("DOCS_OUTPUT_DIR", "architecture-docs")
    source = (knowledge_dir or Path("knowledge")) / "document"
    target = Path(docs_dir)

    # Only copy the deliverable subdirectories (c4, arc42)
    copied = 0
    for subdir in ["c4", "arc42"]:
        src = source / subdir
        if not src.exists():
            continue
        dst = target / subdir
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        file_count = len(list(dst.rglob("*")))
        copied += file_count
        logger.info(f"[EXPORT] {subdir}/ -> {dst} ({file_count} files)")

    if copied:
        logger.info(f"[EXPORT] Architecture docs exported to: {target} ({copied} files total)")

        # Convert to additional formats (Confluence, AsciiDoc, HTML)
        from .shared.utils.confluence_converter import DocumentConverter

        converter = DocumentConverter()
        formats = ["confluence", "adoc", "html"]
        lang = os.getenv("ARC42_LANGUAGE", "en")
        count = converter.convert_directory(target, formats, lang=lang)
        logger.info(f"[EXPORT] Multi-format conversion: {count} files ({', '.join(formats)})")
    else:
        logger.warning("[EXPORT] No Phase 3 output found to export")


def cmd_run(config: Config, preset: str | None = None, phases: list[str] | None = None) -> int:
    """Run SDLC pipeline."""
    from .crews import ArchitectureSynthesisCrew
    from .orchestrator import SDLCOrchestrator
    from .pipelines import ArchitectureFactsPipeline, IndexingPipeline
    from .shared.paths import KNOWLEDGE_DIR, get_chroma_dir
    from .shared.project_context import derive_project_slug, set_active_project

    # Resolve repo path (clone from Git URL if configured)
    repo_path = _resolve_repo_path(config)

    # Multi-project: derive slug and resolve chroma subfolder
    project_slug = derive_project_slug(repo_path)
    set_active_project(project_slug, str(repo_path))

    # Knowledge paths: relative to project root (CWD), NOT target repo
    knowledge_dir = KNOWLEDGE_DIR
    chroma_dir = get_chroma_dir(project_slug)
    phase1_dir = knowledge_dir / "extract"
    phase2_dir = knowledge_dir / "analyze"
    phase4_dir = knowledge_dir / "plan"

    # Clean if requested
    if config.clean:
        clean_knowledge("all")

    # Initialize orchestrator
    orchestrator = SDLCOrchestrator(config_path=config.config_path)

    # Resolve which phases will run (strict validation)
    try:
        planned_phases = _resolve_phases_to_run(orchestrator, preset, phases)
    except ValueError as e:
        logger.error(f"\n[ERROR] {e}")
        return 1

    logger.info(f"[CONFIG] Planned phases: {sorted(planned_phases)}")

    # --- Phase 0: Indexing ---
    if config.index_mode == "off":
        logger.info("[CONFIG] INDEX_MODE=off -> Skipping Phase 0")
        orchestrator.config["phases"]["discover"]["enabled"] = False
    elif "discover" in planned_phases:
        indexing_pipeline = IndexingPipeline(
            repo_path=str(repo_path),
            index_mode=config.index_mode,
        )
        orchestrator.register_phase("discover", indexing_pipeline)

    # --- Extract: Architecture Facts ---
    if "extract" in planned_phases:
        if not config.no_clean:
            clean_knowledge("extract")
        facts_pipeline = ArchitectureFactsPipeline(
            repo_path=str(repo_path),
            output_dir=str(phase1_dir),
        )
        orchestrator.register_phase("extract", facts_pipeline)

    # --- Analyze: Architecture Analysis ---
    if "analyze" in planned_phases:
        from .crews.architecture_analysis import MapReduceAnalysisCrew

        analysis_crew = MapReduceAnalysisCrew(
            facts_path=str(phase1_dir / "architecture_facts.json"),
            chroma_dir=chroma_dir,
            output_dir=str(phase2_dir),
        )
        orchestrator.register_phase("analyze", analysis_crew)

    # --- Document: Architecture Synthesis ---
    if os.getenv("SKIP_SYNTHESIS", "").lower() in ("true", "1", "yes"):
        logger.info("[CONFIG] SKIP_SYNTHESIS=true -> Skipping Document phase")
        orchestrator.config["phases"]["document"]["enabled"] = False
    elif "document" in planned_phases:
        synthesis_crew = ArchitectureSynthesisCrew(
            facts_path=str(phase1_dir / "architecture_facts.json"),
            analyzed_path=str(phase2_dir / "analyzed_architecture.json"),
            output_dir=str(knowledge_dir / "document"),
            chroma_dir=chroma_dir,
        )
        orchestrator.register_phase("document", synthesis_crew)

    # --- Triage: Issue Triage (deterministic + LLM synthesis) ---
    if "triage" in planned_phases:
        from .crews.triage import TriageCrew
        from .crews.triage.schemas import TriageRequest

        triage_input_dir = Path(os.getenv("TASK_INPUT_DIR", str(knowledge_dir.parent / "inputs" / "tasks")))
        triage_files = sorted(triage_input_dir.glob("*")) if triage_input_dir.exists() else []
        triage_files = [f for f in triage_files if f.is_file() and not f.name.startswith(".")]

        # Collect supplementary files (same as plan phase)
        triage_supplementary: dict[str, list[str]] = {}
        for env_key, category in [
            ("REQUIREMENTS_DIR", "requirements"),
            ("LOGS_DIR", "logs"),
            ("REFERENCE_DIR", "reference"),
        ]:
            dir_path = os.getenv(env_key, "").strip()
            if dir_path and Path(dir_path).is_dir():
                cat_files = sorted(Path(dir_path).glob("*"))
                cat_files = [f for f in cat_files if f.is_file() and not f.name.startswith(".")]
                if cat_files:
                    triage_supplementary[category] = [str(f) for f in cat_files]

        if triage_files:
            logger.info("[Triage] Found %d task file(s) to triage", len(triage_files))
            _triage_crew = TriageCrew(knowledge_dir=str(knowledge_dir), chroma_dir=chroma_dir)
            _triage_requests = [
                TriageRequest(
                    issue_id=f.stem,
                    task_file=str(f),
                    supplementary_files=triage_supplementary,
                )
                for f in triage_files
            ]

            class _TriageRunner:
                def __init__(self, crew, requests):
                    self._crew = crew
                    self._requests = requests

                def kickoff(self, inputs=None):
                    results = []
                    for req in self._requests:
                        try:
                            r = self._crew.run(req)
                            results.append(r)
                        except Exception as exc:
                            logger.error("[Triage] Failed to triage %s: %s", req.issue_id, exc)
                            results.append({"status": "failed", "issue_id": req.issue_id, "error": str(exc)})
                    success_count = sum(1 for r in results if r.get("status") in ("success", "partial"))
                    status = "success" if success_count == len(results) else ("partial" if success_count else "failed")
                    return {"status": status, "phase": "triage", "triaged": success_count, "total": len(results)}

            orchestrator.register_phase("triage", _TriageRunner(_triage_crew, _triage_requests))
        else:
            logger.info("[Triage] No task files found in %s — skipping", triage_input_dir)

            class _NoopTriage:
                def kickoff(self, inputs=None):
                    return {"status": "skipped", "phase": "triage", "message": "No task files to triage"}

            orchestrator.register_phase("triage", _NoopTriage())

    # --- Plan: Development Planning (Hybrid Pipeline) ---
    if "plan" in planned_phases:
        from .hybrid.development_planning import DevelopmentPlanningPipeline

        if not config.no_clean:
            clean_knowledge("plan")

        # Get input directory from .env (REQUIRED - no hardcoded default)
        input_dir = os.getenv("TASK_INPUT_DIR", "")
        if not input_dir:
            logger.error(
                "[Phase4] TASK_INPUT_DIR not set in .env! Set it to the folder containing your JIRA XML files."
            )
            raise ValueError(
                "TASK_INPUT_DIR not configured. Set it in your .env file (e.g. TASK_INPUT_DIR=C:\\projects\\inputs)"
            )

        input_path = Path(input_dir)
        if not input_path.exists():
            logger.error(f"[Phase4] TASK_INPUT_DIR does not exist: {input_dir}")
            raise ValueError(f"TASK_INPUT_DIR folder not found: {input_dir}")

        input_files = sorted(input_path.glob("*"))
        # Filter out directories and hidden files
        input_files = [f for f in input_files if f.is_file() and not f.name.startswith(".")]

        facts_path = str(phase1_dir / "architecture_facts.json")
        analyzed_path = str(phase2_dir / "analyzed_architecture.json")

        # Collect supplementary files from REQUIREMENTS_DIR, LOGS_DIR, REFERENCE_DIR
        supplementary_files = {}
        for env_key, category in [
            ("REQUIREMENTS_DIR", "requirements"),
            ("LOGS_DIR", "logs"),
            ("REFERENCE_DIR", "reference"),
        ]:
            dir_path = os.getenv(env_key, "").strip()
            if dir_path and Path(dir_path).is_dir():
                cat_files = sorted(Path(dir_path).glob("*"))
                cat_files = [f for f in cat_files if f.is_file() and not f.name.startswith(".")]
                if cat_files:
                    supplementary_files[category] = [str(f) for f in cat_files]
                    logger.info(f"[Phase4] Found {len(cat_files)} {category} file(s) in {dir_path}")

        if input_files:
            logger.info(f"[Phase4] Found {len(input_files)} task file(s) in {input_dir}")
            planning_pipeline = DevelopmentPlanningPipeline(
                input_files=[str(f) for f in input_files],
                facts_path=facts_path,
                analyzed_path=analyzed_path,
                output_dir=str(phase4_dir),
                chroma_dir=chroma_dir,
                repo_path=os.getenv("PROJECT_PATH"),
                supplementary_files=supplementary_files,
            )
            orchestrator.register_phase("plan", planning_pipeline)
        else:
            logger.info(f"[Plan] No task files in {input_dir} — nothing to plan")

            class _NoopPlan:
                def kickoff(self, inputs=None):
                    logger.info("[Plan] Nothing to do — no task files found")
                    # No tasks means no artifacts by design. Report as skipped so
                    # dashboard/status cards do not show a misleading "ready" phase.
                    return {"status": "skipped", "message": f"No task files in {input_dir}"}

            orchestrator.register_phase("plan", _NoopPlan())

    # --- Implement: Code Generation (Hierarchical CrewAI Team) ---
    if "implement" in planned_phases:
        from .hybrid.code_generation import ImplementCrew

        codegen_dry_run = getattr(config, "dry_run", False)

        implement_crew = ImplementCrew(
            repo_path=str(repo_path),
            facts_path=str(phase1_dir / "architecture_facts.json"),
            plans_dir=str(phase4_dir),
            output_dir=str(knowledge_dir / "implement"),
            task_input_dir=os.getenv("TASK_INPUT_DIR", ""),
            build_verify=os.getenv("CODEGEN_BUILD_VERIFY", "true").lower() not in ("false", "0", "no"),
            dry_run=codegen_dry_run,
        )
        orchestrator.register_phase("implement", implement_crew)

    # --- Verify: Test Generation (Phase 6) ---
    if "verify" in planned_phases:
        from .crews.testing import TestingCrew

        testing_crew = TestingCrew(
            repo_path=str(repo_path),
            implement_dir=str(knowledge_dir / "implement"),
            output_dir=str(knowledge_dir / "verify"),
            dry_run=getattr(config, "dry_run", False),
        )
        orchestrator.register_phase("verify", testing_crew)

    # --- Deliver: Review & Consistency Guard (Phase 7) ---
    if "deliver" in planned_phases:
        from .crews.review import ReviewCrew

        review_crew = ReviewCrew(
            knowledge_dir=str(knowledge_dir),
        )
        orchestrator.register_phase("deliver", review_crew)

    # Execute
    try:
        result = orchestrator.run(preset=preset, phases=phases)

        # Always export run report (success or failure)
        _export_run_report(result, config, planned_phases, knowledge_dir=knowledge_dir)

        if result.status == "success":
            logger.info("\n[OK] Pipeline successful!")
            logger.info(f"Time: {result.total_duration}")

            # Export Phase 3 docs to external dir if configured
            if "document" in planned_phases:
                _export_architecture_docs(knowledge_dir=knowledge_dir)

            return 0
        else:
            logger.error(f"\n[ERROR] Pipeline failed: {result.message}")
            return 1

    except KeyboardInterrupt:
        logger.info("\n[WARN] Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"\n[ERROR] Unexpected error: {e}", exc_info=True)
        return 1


# =============================================================================
# Argument Parsing
# =============================================================================


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="aicodegencrew",
        description="AI Code Generation Crew - SDLC Automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--env",
        dest="env_file",
        help="Path to .env configuration file (default: .env in current directory)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- run command ---
    run_parser = subparsers.add_parser("run", help="Run SDLC pipeline")
    run_parser.add_argument(
        "--preset",
        help="Run a preset combination of phases (see 'list' command for available presets)",
    )
    run_parser.add_argument(
        "--phases",
        nargs="+",
        help="Explicit list of phases to run",
    )
    run_parser.add_argument(
        "--repo-path",
        help="Path to repository (default: PROJECT_PATH from .env)",
    )
    run_parser.add_argument(
        "--index-mode",
        choices=["off", "auto", "force", "smart"],
        help="Override INDEX_MODE from .env",
    )
    run_parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean knowledge directories before running",
    )
    run_parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Skip auto-cleaning",
    )
    run_parser.add_argument(
        "--config",
        help="Path to phases_config.yaml",
    )
    run_parser.add_argument(
        "--git-url",
        help="Git repository URL (overrides GIT_REPO_URL in .env)",
    )
    run_parser.add_argument(
        "--branch",
        help="Git branch (overrides GIT_BRANCH in .env, empty=auto-detect)",
    )

    # --- index command ---
    index_parser = subparsers.add_parser("index", help="Index repository")
    index_parser.add_argument(
        "--mode",
        "-m",
        choices=["off", "auto", "force", "smart"],
        help="Indexing mode (overrides INDEX_MODE in .env)",
    )
    index_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force re-index (same as --mode force)",
    )
    index_parser.add_argument(
        "-s",
        "--smart",
        action="store_true",
        help="Smart incremental (same as --mode smart)",
    )
    index_parser.add_argument(
        "--repo",
        help="Repository path (default: PROJECT_PATH from .env)",
    )
    index_parser.add_argument(
        "--git-url",
        help="Git repository URL (overrides GIT_REPO_URL in .env)",
    )
    index_parser.add_argument(
        "--branch",
        help="Git branch (overrides GIT_BRANCH in .env, empty=auto-detect)",
    )

    # --- list command ---
    list_parser = subparsers.add_parser("list", help="List available phases")
    list_parser.add_argument(
        "--config",
        help="Path to phases_config.yaml",
    )

    # --- plan command (shortcut for run --preset plan) ---
    plan_parser = subparsers.add_parser(
        "plan",
        help="Run development planning (shortcut for: run --preset plan)",
    )
    plan_parser.add_argument(
        "--repo-path",
        help="Path to repository (default: PROJECT_PATH from .env)",
    )
    plan_parser.add_argument(
        "--index-mode",
        choices=["off", "auto", "force", "smart"],
        help="Override INDEX_MODE from .env",
    )
    plan_parser.add_argument(
        "--config",
        help="Path to phases_config.yaml",
    )

    # --- codegen command (shortcut for run --preset develop) ---
    codegen_parser = subparsers.add_parser(
        "codegen",
        help="Run code generation (shortcut for: run --preset develop)",
    )
    codegen_parser.add_argument(
        "--repo-path",
        help="Path to repository (default: PROJECT_PATH from .env)",
    )
    codegen_parser.add_argument(
        "--task-id",
        help="Process a single task ID (skip all others)",
    )
    codegen_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview mode: run stages 1-4 but skip file writes and git operations",
    )
    codegen_parser.add_argument(
        "--index-mode",
        choices=["off", "auto", "force", "smart"],
        help="Override INDEX_MODE from .env",
    )
    codegen_parser.add_argument(
        "--config",
        help="Path to phases_config.yaml",
    )

    return parser


# =============================================================================
# Main Entry Point
# =============================================================================


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # Load .env from --env flag or default location
    env_file = getattr(args, "env_file", None)
    if env_file:
        env_path = Path(env_file)
        if not env_path.exists():
            print(f"ERROR: .env file not found: {env_file}")
            return 1
        load_dotenv(env_path, override=True)
        logger.info(f"[CONFIG] Loaded .env from: {env_path}")
    else:
        load_dotenv(override=True)

    setup_logging()

    # No command -> show help
    if not args.command:
        parser.print_help()
        return 0

    # --- list ---
    if args.command == "list":
        config = Config.from_env(config_path=getattr(args, "config", None))
        return cmd_list(config)

    # --- index ---
    if args.command == "index":
        # Determine mode: CLI flags > --mode > .env
        if args.force:
            mode = "force"
        elif args.smart:
            mode = "smart"
        else:
            mode = args.mode

        config = Config.from_env(
            repo_path=args.repo,
            index_mode=mode,
            git_repo_url=args.git_url,
            git_branch=args.branch,
        )
        logger.info(f"[CONFIG] INDEX_MODE = {config.index_mode}")
        return cmd_index(config)

    # --- run ---
    if args.command == "run":
        config = Config.from_env(
            repo_path=args.repo_path,
            index_mode=args.index_mode,
            config_path=args.config,
            clean=args.clean,
            no_clean=args.no_clean,
            git_repo_url=args.git_url,
            git_branch=args.branch,
        )
        logger.info(f"[CONFIG] INDEX_MODE = {config.index_mode}")
        return cmd_run(config, preset=args.preset, phases=args.phases)

    # --- plan (shortcut for run --preset plan) ---
    if args.command == "plan":
        config = Config.from_env(
            repo_path=args.repo_path,
            index_mode=args.index_mode,
            config_path=args.config,
        )
        logger.info(f"[CONFIG] INDEX_MODE = {config.index_mode}")
        return cmd_run(config, preset="plan")

    # --- codegen (shortcut for run --preset develop) ---
    if args.command == "codegen":
        config = Config.from_env(
            repo_path=args.repo_path,
            index_mode=args.index_mode,
            config_path=args.config,
            dry_run=args.dry_run,
            task_id=args.task_id,
        )
        logger.info(f"[CONFIG] INDEX_MODE = {config.index_mode}")
        return cmd_run(config, preset="develop")

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
