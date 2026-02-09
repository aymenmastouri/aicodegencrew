#!/usr/bin/env python3
"""
AI Code Generation Crew - Unified CLI

Modern CLI with subcommands:
    aicodegencrew run              Run SDLC pipeline
    aicodegencrew plan             Run development planning (Phase 0+1+2+4)
    aicodegencrew index            Index repository
    aicodegencrew list             List available phases

Usage:
    python -m aicodegencrew run --preset architecture_workflow
    python -m aicodegencrew run --phases phase1_architecture_facts
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
# load_dotenv moved into main() to support --env flag

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
    output_base: Path = Path(".")

    @classmethod
    def from_env(cls, **overrides) -> "Config":
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

        # Output base directory: where knowledge/, logs/, run_report.json go
        output_base = overrides.get("output_base") or os.getenv("OUTPUT_BASE_DIR", ".")

        return cls(
            repo_path=Path(repo),
            index_mode=mode,
            config_path=overrides.get("config_path"),
            clean=overrides.get("clean", False),
            no_clean=overrides.get("no_clean", False),
            git_repo_url=git_url.strip(),
            git_branch=git_branch.strip(),
            output_base=Path(output_base),
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
    """Clean knowledge directory before running a phase."""
    from .shared.utils.logger import OUTPUT_BASE_DIR
    knowledge_dir = OUTPUT_BASE_DIR / "knowledge"
    if not knowledge_dir.exists():
        return
    
    cleaned: list[str] = []
    
    # Phase 1: Architecture
    if phase in ("all", "phase1"):
        arch_dir = knowledge_dir / "architecture"
        if arch_dir.exists():
            for f in arch_dir.glob("*.json"):
                f.unlink()
                cleaned.append(str(f))
            for f in arch_dir.glob("*.md"):
                if f.name != "README.md":
                    f.unlink()
                    cleaned.append(str(f))
            for subdir in ("analysis", "quality", "adr", "confluence", "html"):
                sub_path = arch_dir / subdir
                if sub_path.exists():
                    shutil.rmtree(sub_path)
                    cleaned.append(str(sub_path))
    
    # Phase 2: Analysis
    if phase in ("all", "phase2"):
        analysis_dir = knowledge_dir / "analysis"
        if analysis_dir.exists():
            shutil.rmtree(analysis_dir)
            cleaned.append(str(analysis_dir))
    
    # Phase 3: Development
    if phase in ("all", "phase3"):
        dev_dir = knowledge_dir / "development"
        if dev_dir.exists():
            shutil.rmtree(dev_dir)
            cleaned.append(str(dev_dir))
    
    if cleaned:
        logger.info(f"[CLEAN] Removed {len(cleaned)} items")
    
    # Recreate structure
    (knowledge_dir / "architecture" / "quality").mkdir(parents=True, exist_ok=True)
    (knowledge_dir / "analysis").mkdir(parents=True, exist_ok=True)
    (knowledge_dir / "development").mkdir(parents=True, exist_ok=True)


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

    repo_path = _resolve_repo_path(config)
    chroma_dir = Path(os.getenv("CHROMA_DIR", ".cache/.chroma"))

    logger.info("=" * 60)
    logger.info("INDEXING PIPELINE")
    logger.info("=" * 60)
    logger.info(f"Repository : {repo_path}")
    logger.info(f"INDEX_MODE : {config.index_mode}")
    logger.info(f"ChromaDB   : {chroma_dir}")
    logger.info("")

    if config.index_mode == "off":
        logger.info("[SKIP] INDEX_MODE=off - Indexing disabled")
        return 0

    force_reindex = False
    if config.index_mode == "force":
        if chroma_dir.exists():
            logger.info(f"[FORCE] Clearing cache: {chroma_dir}")
            shutil.rmtree(chroma_dir)
        force_reindex = True
    elif config.index_mode == "smart":
        logger.info("[SMART] Incremental update only")
    else:
        logger.info("[AUTO] Index if needed")

    try:
        ensure_repo_indexed(str(repo_path), force_reindex=force_reindex)
        logger.info("\n[OK] Indexing completed!")
        return 0
    except KeyboardInterrupt:
        logger.warning("\n[WARN] Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"[ERROR] Indexing failed: {e}")
        return 1


def _resolve_phases_to_run(
    orchestrator: "SDLCOrchestrator",
    preset: str | None,
    phases: list[str] | None,
) -> set[str]:
    """Resolve which phases will run based on preset or explicit phases.

    Uses phases_config.yaml as single source of truth instead of fragile
    string matching.
    """
    if phases:
        # Validate explicit phase names against config
        known_phases = set(orchestrator.config.get("phases", {}).keys())
        unknown = set(phases) - known_phases
        if unknown:
            raise ValueError(
                f"Unknown phase(s): {', '.join(sorted(unknown))}. "
                f"Valid phases: {', '.join(sorted(known_phases))}"
            )
        return set(phases)

    if preset:
        # Validate preset name against config
        preset_phases = orchestrator.get_preset_phases(preset)
        if not preset_phases:
            known_presets = list(orchestrator.config.get("presets", {}).keys())
            raise ValueError(
                f"Unknown preset: '{preset}'. "
                f"Valid presets: {', '.join(known_presets)}"
            )
        return set(preset_phases)

    # Default: all enabled phases
    return set(orchestrator.get_enabled_phases())


def _export_run_report(
    result: "PipelineResult",
    config: Config,
    planned_phases: set[str],
) -> Path | None:
    """Export run_report.json to knowledge/ directory.

    Provides the end user with a persistent record of what happened
    during the pipeline run — visible alongside the generated artifacts.
    """
    import json
    from .shared.utils.logger import RUN_ID, METRICS_LOG, CURRENT_LOG, OUTPUT_BASE_DIR

    base = config.output_base.resolve()
    report_dir = base / "knowledge"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "run_report.json"

    # Collect output files per phase (relative to output_base)
    phase_outputs = {
        "phase0_indexing": [str(base / ".cache" / ".chroma")],
        "phase1_architecture_facts": [
            str(base / "knowledge" / "architecture" / "architecture_facts.json"),
            str(base / "knowledge" / "architecture" / "evidence_map.json"),
        ],
        "phase2_architecture_analysis": [
            str(base / "knowledge" / "architecture" / "analyzed_architecture.json"),
        ],
        "phase3_architecture_synthesis": [
            str(base / "knowledge" / "architecture" / "c4"),
            str(base / "knowledge" / "architecture" / "arc42"),
        ],
        "phase4_development_planning": [
            str(base / "knowledge" / "development"),
        ],
    }

    phases_detail = []
    for pr in result.phases:
        detail = pr.to_dict()
        detail["duration_seconds"] = round(pr.duration_seconds, 2)
        # List actual output files that exist
        expected = phase_outputs.get(pr.phase_id, [])
        detail["output_files"] = [f for f in expected if Path(f).exists()]
        phases_detail.append(detail)

    report = {
        "run_id": RUN_ID,
        "timestamp": datetime.now().isoformat(),
        "status": result.status,
        "message": result.message,
        "total_duration": result.total_duration,
        "planned_phases": sorted(planned_phases),
        "environment": {
            "repo_path": str(config.repo_path),
            "index_mode": config.index_mode,
            "output_base_dir": str(base),
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


def _export_architecture_docs():
    """Copy Phase 3 architecture docs (C4 + Arc42) to export dir.

    Default: <output_base>/architecture-docs. Override with DOCS_OUTPUT_DIR in .env.
    """
    import shutil
    from .shared.utils.logger import OUTPUT_BASE_DIR

    docs_dir = os.getenv("DOCS_OUTPUT_DIR", str(OUTPUT_BASE_DIR / "architecture-docs"))
    source = OUTPUT_BASE_DIR / "knowledge" / "architecture"
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
    from .orchestrator import SDLCOrchestrator
    from .pipelines import IndexingPipeline, ArchitectureFactsPipeline
    from .crews import ArchitectureAnalysisCrew, ArchitectureSynthesisCrew
    from .shared.utils.logger import configure_output_dir

    # Set output base directory BEFORE any file I/O
    base = config.output_base.resolve()
    configure_output_dir(base)
    logger.info(f"[CONFIG] OUTPUT_BASE_DIR = {base}")

    # Resolve repo path (clone from Git URL if configured)
    repo_path = _resolve_repo_path(config)

    # Convenience: all output paths relative to output_base
    knowledge_dir = base / "knowledge"
    arch_dir = knowledge_dir / "architecture"
    dev_dir = knowledge_dir / "development"

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
        orchestrator.config["phases"]["phase0_indexing"]["enabled"] = False
    elif "phase0_indexing" in planned_phases:
        indexing_pipeline = IndexingPipeline(
            repo_path=str(repo_path),
            index_mode=config.index_mode,
        )
        orchestrator.register_phase("phase0_indexing", indexing_pipeline)

    # --- Phase 1: Architecture Facts ---
    if "phase1_architecture_facts" in planned_phases:
        if not config.no_clean:
            clean_knowledge("phase1")
        facts_pipeline = ArchitectureFactsPipeline(
            repo_path=str(repo_path),
            output_dir=str(arch_dir),
        )
        orchestrator.register_phase("phase1_architecture_facts", facts_pipeline)

    # --- Phase 2: Architecture Analysis ---
    if "phase2_architecture_analysis" in planned_phases:
        from .crews.architecture_analysis import MapReduceAnalysisCrew
        analysis_crew = MapReduceAnalysisCrew(
            facts_path=str(arch_dir / "architecture_facts.json")
        )
        orchestrator.register_phase("phase2_architecture_analysis", analysis_crew)

    # --- Phase 3: Architecture Synthesis ---
    if os.getenv("SKIP_SYNTHESIS", "").lower() in ("true", "1", "yes"):
        logger.info("[CONFIG] SKIP_SYNTHESIS=true -> Skipping Phase 3")
        orchestrator.config["phases"]["phase3_architecture_synthesis"]["enabled"] = False
    elif "phase3_architecture_synthesis" in planned_phases:
        synthesis_crew = ArchitectureSynthesisCrew(
            facts_path=str(arch_dir / "architecture_facts.json")
        )
        orchestrator.register_phase("phase3_architecture_synthesis", synthesis_crew)

    # --- Phase 4: Development Planning (Hybrid Pipeline) ---
    if "phase4_development_planning" in planned_phases:
        from .pipelines.development_planning import DevelopmentPlanningPipeline

        # Get input directory from .env (REQUIRED - no hardcoded default)
        input_dir = os.getenv("TASK_INPUT_DIR", "")
        if not input_dir:
            logger.error("[Phase4] TASK_INPUT_DIR not set in .env! Set it to the folder containing your JIRA XML files.")
            raise ValueError("TASK_INPUT_DIR not configured. Set it in your .env file (e.g. TASK_INPUT_DIR=C:\\projects\\inputs)")

        input_path = Path(input_dir)
        if not input_path.exists():
            logger.error(f"[Phase4] TASK_INPUT_DIR does not exist: {input_dir}")
            raise ValueError(f"TASK_INPUT_DIR folder not found: {input_dir}")

        input_files = sorted(input_path.glob("*"))
        # Filter out directories and hidden files
        input_files = [f for f in input_files if f.is_file() and not f.name.startswith(".")]

        facts_path = str(arch_dir / "architecture_facts.json")
        analyzed_path = str(arch_dir / "analyzed_architecture.json")

        if input_files:
            logger.info(f"[Phase4] Found {len(input_files)} input file(s) in {input_dir}")
            planning_pipeline = DevelopmentPlanningPipeline(
                input_files=[str(f) for f in input_files],
                facts_path=facts_path,
                analyzed_path=analyzed_path,
                output_dir=str(dev_dir),
                repo_path=os.getenv("PROJECT_PATH"),
            )
            orchestrator.register_phase("phase4_development_planning", planning_pipeline)
        else:
            logger.warning(f"[Phase4] No input files found in {input_dir}, skipping phase")

    # Execute
    try:
        result = orchestrator.run(preset=preset, phases=phases)

        # Always export run report (success or failure)
        _export_run_report(result, config, planned_phases)

        if result.status == "success":
            logger.info(f"\n[OK] Pipeline successful!")
            logger.info(f"Time: {result.total_duration}")

            # Export Phase 3 docs to external dir if configured
            if "phase3_architecture_synthesis" in planned_phases:
                _export_architecture_docs()

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
        "--env", dest="env_file",
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
        "--phases", nargs="+",
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
        "--clean", action="store_true",
        help="Clean knowledge directories before running",
    )
    run_parser.add_argument(
        "--no-clean", action="store_true",
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
        "--mode", "-m",
        choices=["off", "auto", "force", "smart"],
        help="Indexing mode (overrides INDEX_MODE in .env)",
    )
    index_parser.add_argument(
        "-f", "--force", action="store_true",
        help="Force re-index (same as --mode force)",
    )
    index_parser.add_argument(
        "-s", "--smart", action="store_true",
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

    # --- plan command (shortcut for run --preset planning_only) ---
    plan_parser = subparsers.add_parser(
        "plan", help="Run development planning (shortcut for: run --preset planning_only)",
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

    # --- plan (shortcut for run --preset planning_only) ---
    if args.command == "plan":
        config = Config.from_env(
            repo_path=args.repo_path,
            index_mode=args.index_mode,
            config_path=args.config,
        )
        logger.info(f"[CONFIG] INDEX_MODE = {config.index_mode}")
        return cmd_run(config, preset="planning_only")

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
