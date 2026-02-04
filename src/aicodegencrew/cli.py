#!/usr/bin/env python3
"""
AI Code Generation Crew - Unified CLI

Modern CLI with subcommands:
    aicodegencrew run              Run SDLC pipeline
    aicodegencrew index            Index repository
    aicodegencrew list             List available phases

Usage:
    python -m aicodegencrew run --preset architecture_workflow
    python -m aicodegencrew run --phases phase1_architecture_facts
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
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .orchestrator import SDLCOrchestrator

# Suppress noisy warnings from dependencies
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic")
warnings.filterwarnings("ignore", message=".*Pydantic.*")
warnings.filterwarnings("ignore", message=".*LangChain.*")

from dotenv import load_dotenv
load_dotenv(override=True)

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
        
        return cls(
            repo_path=Path(repo),
            index_mode=mode,
            config_path=overrides.get("config_path"),
            clean=overrides.get("clean", False),
            no_clean=overrides.get("no_clean", False),
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
    knowledge_dir = Path("knowledge")
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
    
    chroma_dir = Path(os.getenv("CHROMA_DIR", ".cache/.chroma"))
    
    logger.info("=" * 60)
    logger.info("INDEXING PIPELINE")
    logger.info("=" * 60)
    logger.info(f"Repository : {config.repo_path}")
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
        ensure_repo_indexed(str(config.repo_path), force_reindex=force_reindex)
        logger.info("\n[OK] Indexing completed!")
        return 0
    except KeyboardInterrupt:
        logger.warning("\n[WARN] Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"[ERROR] Indexing failed: {e}")
        return 1


def cmd_run(config: Config, preset: str | None = None, phases: list[str] | None = None) -> int:
    """Run SDLC pipeline."""
    from .orchestrator import SDLCOrchestrator
    from .pipelines import IndexingPipeline, ArchitectureFactsPipeline
    from .crews import ArchitectureAnalysisCrew, ArchitectureSynthesisCrew
    
    # Clean if requested
    if config.clean:
        clean_knowledge("all")
    
    # Initialize orchestrator
    orchestrator = SDLCOrchestrator(config_path=config.config_path)
    
    # --- Phase 0: Indexing ---
    if config.index_mode == "off":
        logger.info("[CONFIG] INDEX_MODE=off -> Skipping Phase 0")
        orchestrator.config["phases"]["phase0_indexing"]["enabled"] = False
        orchestrator.context["phases"]["phase0_indexing"] = {
            "phase": "phase0_indexing",
            "status": "success",
            "message": "Skipped (INDEX_MODE=off)",
        }
        orchestrator.context["knowledge"]["phase0_indexing"] = {
            "status": "success",
            "message": "Using existing index",
        }
    else:
        indexing_pipeline = IndexingPipeline(
            repo_path=str(config.repo_path),
            index_mode=config.index_mode,
        )
        orchestrator.register_phase("phase0_indexing", indexing_pipeline)
    
    # Store shared context
    orchestrator.context["shared"]["repo_path"] = str(config.repo_path)
    orchestrator.context["shared"]["repo_name"] = config.repo_path.name
    orchestrator.context["shared"]["output_dir"] = "./knowledge/architecture"
    
    # --- Phase 1: Architecture Facts ---
    phases_to_run = phases or []
    preset_str = preset or ""
    
    will_run_phase1 = (
        "phase1_architecture_facts" in phases_to_run
        or "facts" in preset_str
        or "architecture" in preset_str
        or "planning" in preset_str
        or (not phases_to_run and not preset_str)
    )
    
    if will_run_phase1 and not config.no_clean:
        clean_knowledge("phase1")
    
    facts_pipeline = ArchitectureFactsPipeline(
        repo_path=str(config.repo_path),
        output_dir="./knowledge/architecture",
    )
    orchestrator.register_phase("phase1_architecture_facts", facts_pipeline)
    
    # --- Phase 2: Architecture Analysis (NEW!) ---
    will_run_analysis = (
        "phase2_architecture_analysis" in phases_to_run
        or "analysis_only" in preset_str
        or "architecture_workflow" in preset_str
        or "planning" in preset_str
        or (not phases_to_run and not preset_str)
    )
    
    if will_run_analysis:
        # Use MapReduce for large repos (auto-fallback to standard for small repos)
        from .crews.architecture_analysis import MapReduceAnalysisCrew
        analysis_crew = MapReduceAnalysisCrew(
            facts_path="./knowledge/architecture/architecture_facts.json"
        )
        orchestrator.register_phase("phase2_architecture_analysis", analysis_crew)
    
    # --- Phase 3: Architecture Synthesis ---
    will_run_synthesis = (
        "phase3_architecture_synthesis" in phases_to_run
        or "architecture_workflow" in preset_str
        or "planning" in preset_str
        or (not phases_to_run and not preset_str)
    )
    
    if will_run_synthesis:
        synthesis_crew = ArchitectureSynthesisCrew(
            facts_path="./knowledge/architecture/architecture_facts.json"
            # Note: analyzed_path is auto-derived from facts_path in crew.py
        )
        orchestrator.register_phase("phase3_architecture_synthesis", synthesis_crew)
    
    # Execute
    try:
        result = orchestrator.run(preset=preset, phases=phases)
        
        if result.status == "success":
            logger.info(f"\n[OK] Pipeline successful!")
            logger.info(f"Time: {result.total_duration}")
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
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # --- run command ---
    run_parser = subparsers.add_parser("run", help="Run SDLC pipeline")
    run_parser.add_argument(
        "--preset",
        choices=["indexing_only", "facts_only", "analysis_only", "architecture_workflow", "architecture_full", "planning_workflow"],
        help="Run a preset combination of phases",
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
    
    # --- list command ---
    list_parser = subparsers.add_parser("list", help="List available phases")
    list_parser.add_argument(
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
        )
        logger.info(f"[CONFIG] INDEX_MODE = {config.index_mode}")
        return cmd_run(config, preset=args.preset, phases=args.phases)
    
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
