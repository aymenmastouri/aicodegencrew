"""Tests for CLI (cli.py) and Orchestrator (orchestrator.py).

All tests run without LLM, network, or real file I/O.
Uses pytest fixtures: tmp_path, monkeypatch, and unittest.mock.
"""

import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from aicodegencrew.cli import Config, clean_knowledge, create_parser, _resolve_phases_to_run
from aicodegencrew.orchestrator import (
    PipelineResult,
    PhaseResult,
    SDLCOrchestrator,
)


# =============================================================================
# Fixtures
# =============================================================================

MINIMAL_PHASES_CONFIG = {
    "phases": {
        "phase0_indexing": {
            "enabled": True,
            "name": "Repository Indexing",
            "order": 0,
            "required": True,
        },
        "phase1_architecture_facts": {
            "enabled": True,
            "name": "Architecture Facts Extraction",
            "order": 1,
            "required": True,
            "dependencies": ["phase0_indexing"],
        },
        "phase2_architecture_analysis": {
            "enabled": True,
            "name": "Architecture Analysis",
            "order": 2,
            "required": True,
            "dependencies": ["phase1_architecture_facts"],
        },
        "phase3_architecture_synthesis": {
            "enabled": True,
            "name": "Architecture Synthesis",
            "order": 3,
            "required": False,
            "dependencies": ["phase2_architecture_analysis"],
        },
        "phase4_development_planning": {
            "enabled": True,
            "name": "Development Planning",
            "order": 4,
            "required": False,
            "dependencies": ["phase2_architecture_analysis"],
        },
    },
    "presets": {
        "indexing_only": ["phase0_indexing"],
        "facts_only": ["phase0_indexing", "phase1_architecture_facts"],
        "analysis_only": [
            "phase0_indexing",
            "phase1_architecture_facts",
            "phase2_architecture_analysis",
        ],
        "architecture_workflow": [
            "phase0_indexing",
            "phase1_architecture_facts",
            "phase2_architecture_analysis",
            "phase3_architecture_synthesis",
        ],
        "planning_only": [
            "phase0_indexing",
            "phase1_architecture_facts",
            "phase2_architecture_analysis",
            "phase4_development_planning",
        ],
    },
    "execution": {
        "mode": "architecture_workflow",
        "stop_on_error": True,
    },
}


@pytest.fixture
def config_yaml(tmp_path: Path) -> Path:
    """Write a minimal phases_config.yaml into tmp_path and return its path."""
    cfg_file = tmp_path / "phases_config.yaml"
    cfg_file.write_text(yaml.dump(MINIMAL_PHASES_CONFIG), encoding="utf-8")
    return cfg_file


@pytest.fixture
def orchestrator(config_yaml: Path) -> SDLCOrchestrator:
    """Create an SDLCOrchestrator backed by the minimal config fixture."""
    return SDLCOrchestrator(config_path=str(config_yaml))


# =============================================================================
# CLI: create_parser()
# =============================================================================

class TestCreateParser:
    """Tests for create_parser()."""

    def test_returns_argument_parser(self):
        parser = create_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_parser_prog_name(self):
        parser = create_parser()
        assert parser.prog == "aicodegencrew"


# =============================================================================
# CLI: Argument parsing
# =============================================================================

class TestArgumentParsing:
    """Tests for parsing various CLI commands."""

    def test_run_with_preset(self):
        parser = create_parser()
        args = parser.parse_args(["run", "--preset", "architecture_workflow"])
        assert args.command == "run"
        assert args.preset == "architecture_workflow"
        assert args.phases is None

    def test_run_with_explicit_phases(self):
        parser = create_parser()
        args = parser.parse_args(
            ["run", "--phases", "phase0_indexing", "phase1_architecture_facts"]
        )
        assert args.command == "run"
        assert args.phases == ["phase0_indexing", "phase1_architecture_facts"]
        assert args.preset is None

    def test_run_with_clean_flag(self):
        parser = create_parser()
        args = parser.parse_args(["run", "--clean", "--preset", "facts_only"])
        assert args.clean is True
        assert args.no_clean is False

    def test_run_with_no_clean_flag(self):
        parser = create_parser()
        args = parser.parse_args(["run", "--no-clean", "--preset", "facts_only"])
        assert args.no_clean is True
        assert args.clean is False

    def test_run_with_index_mode(self):
        parser = create_parser()
        args = parser.parse_args(["run", "--index-mode", "force"])
        assert args.index_mode == "force"

    def test_plan_command(self):
        """Parsing 'plan' produces correct args (shortcut for run --preset planning_only)."""
        parser = create_parser()
        args = parser.parse_args(["plan"])
        assert args.command == "plan"

    def test_plan_command_with_repo_path(self):
        parser = create_parser()
        args = parser.parse_args(["plan", "--repo-path", "/some/repo"])
        assert args.command == "plan"
        assert args.repo_path == "/some/repo"

    def test_index_force(self):
        """Parsing 'index --force' produces correct args."""
        parser = create_parser()
        args = parser.parse_args(["index", "--force"])
        assert args.command == "index"
        assert args.force is True

    def test_index_smart(self):
        parser = create_parser()
        args = parser.parse_args(["index", "--smart"])
        assert args.command == "index"
        assert args.smart is True

    def test_index_with_mode(self):
        parser = create_parser()
        args = parser.parse_args(["index", "--mode", "smart"])
        assert args.command == "index"
        assert args.mode == "smart"

    def test_index_with_repo(self):
        parser = create_parser()
        args = parser.parse_args(["index", "--repo", "/my/repo"])
        assert args.command == "index"
        assert args.repo == "/my/repo"

    def test_list_command(self):
        """Parsing 'list' produces correct args."""
        parser = create_parser()
        args = parser.parse_args(["list"])
        assert args.command == "list"

    def test_env_flag_global(self):
        parser = create_parser()
        args = parser.parse_args(["--env", "/path/to/.env", "list"])
        assert args.env_file == "/path/to/.env"
        assert args.command == "list"

    def test_no_command(self):
        parser = create_parser()
        args = parser.parse_args([])
        assert args.command is None


# =============================================================================
# CLI: Config.from_env()
# =============================================================================

class TestConfigFromEnv:
    """Tests for Config.from_env()."""

    def test_creates_config_from_env_vars(self, monkeypatch):
        monkeypatch.setenv("PROJECT_PATH", "/my/project")
        monkeypatch.setenv("INDEX_MODE", "smart")
        monkeypatch.setenv("GIT_REPO_URL", "https://github.com/org/repo.git")
        monkeypatch.setenv("GIT_BRANCH", "develop")

        config = Config.from_env()

        assert config.repo_path == Path("/my/project")
        assert config.index_mode == "smart"
        assert config.git_repo_url == "https://github.com/org/repo.git"
        assert config.git_branch == "develop"

    def test_uses_defaults_when_env_vars_not_set(self, monkeypatch):
        monkeypatch.delenv("PROJECT_PATH", raising=False)
        monkeypatch.delenv("REPO_PATH", raising=False)
        monkeypatch.delenv("INDEX_MODE", raising=False)
        monkeypatch.delenv("GIT_REPO_URL", raising=False)
        monkeypatch.delenv("GIT_BRANCH", raising=False)

        config = Config.from_env()

        assert config.repo_path == Path(".")
        assert config.index_mode == "auto"
        assert config.git_repo_url == ""
        assert config.git_branch == ""
        assert config.clean is False
        assert config.no_clean is False
        assert config.config_path is None

    def test_overrides_take_precedence(self, monkeypatch):
        monkeypatch.setenv("PROJECT_PATH", "/env/path")
        monkeypatch.setenv("INDEX_MODE", "smart")

        config = Config.from_env(repo_path="/override/path", index_mode="force")

        assert config.repo_path == Path("/override/path")
        assert config.index_mode == "force"

    def test_invalid_index_mode_defaults_to_auto(self, monkeypatch):
        monkeypatch.delenv("INDEX_MODE", raising=False)
        config = Config.from_env(index_mode="INVALID_MODE")
        assert config.index_mode == "auto"

    def test_repo_path_fallback_to_repo_path_env(self, monkeypatch):
        monkeypatch.delenv("PROJECT_PATH", raising=False)
        monkeypatch.setenv("REPO_PATH", "/fallback/repo")

        config = Config.from_env()
        assert config.repo_path == Path("/fallback/repo")

    def test_frozen_dataclass(self, monkeypatch):
        monkeypatch.delenv("PROJECT_PATH", raising=False)
        monkeypatch.delenv("INDEX_MODE", raising=False)
        config = Config.from_env()
        with pytest.raises(AttributeError):
            config.index_mode = "force"  # type: ignore[misc]

    def test_config_path_override(self):
        config = Config.from_env(config_path="/custom/config.yaml")
        assert config.config_path == "/custom/config.yaml"

    def test_clean_and_no_clean_overrides(self):
        config = Config.from_env(clean=True, no_clean=True)
        assert config.clean is True
        assert config.no_clean is True


# =============================================================================
# CLI: _resolve_phases_to_run()
# =============================================================================

class TestResolvePhasesToRun:
    """Tests for _resolve_phases_to_run()."""

    def test_valid_preset_returns_correct_phases(self, orchestrator):
        result = _resolve_phases_to_run(orchestrator, preset="architecture_workflow", phases=None)
        assert result == {
            "phase0_indexing",
            "phase1_architecture_facts",
            "phase2_architecture_analysis",
            "phase3_architecture_synthesis",
        }

    def test_indexing_only_preset(self, orchestrator):
        result = _resolve_phases_to_run(orchestrator, preset="indexing_only", phases=None)
        assert result == {"phase0_indexing"}

    def test_explicit_phases_override_preset(self, orchestrator):
        result = _resolve_phases_to_run(
            orchestrator,
            preset="architecture_workflow",
            phases=["phase0_indexing"],
        )
        # Explicit phases take precedence
        assert result == {"phase0_indexing"}

    def test_unknown_preset_raises_value_error(self, orchestrator):
        with pytest.raises(ValueError, match="Unknown preset"):
            _resolve_phases_to_run(orchestrator, preset="nonexistent_preset", phases=None)

    def test_unknown_phase_raises_value_error(self, orchestrator):
        with pytest.raises(ValueError, match="Unknown phase"):
            _resolve_phases_to_run(orchestrator, preset=None, phases=["phase99_bogus"])

    def test_no_preset_no_phases_returns_all_enabled(self, orchestrator):
        result = _resolve_phases_to_run(orchestrator, preset=None, phases=None)
        # All 5 phases in our minimal config are enabled
        assert "phase0_indexing" in result
        assert "phase1_architecture_facts" in result
        assert "phase2_architecture_analysis" in result
        assert "phase3_architecture_synthesis" in result
        assert "phase4_development_planning" in result

    def test_planning_only_preset(self, orchestrator):
        result = _resolve_phases_to_run(orchestrator, preset="planning_only", phases=None)
        assert result == {
            "phase0_indexing",
            "phase1_architecture_facts",
            "phase2_architecture_analysis",
            "phase4_development_planning",
        }


# =============================================================================
# CLI: clean_knowledge()
# =============================================================================

class TestCleanKnowledge:
    """Tests for clean_knowledge()."""

    def test_removes_phase1_artifacts(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        # Set up a fake knowledge directory
        arch_dir = tmp_path / "knowledge" / "architecture"
        arch_dir.mkdir(parents=True)
        (arch_dir / "architecture_facts.json").write_text("{}")
        (arch_dir / "evidence_map.json").write_text("{}")
        (arch_dir / "some_file.md").write_text("# Doc")
        (arch_dir / "README.md").write_text("# Readme")  # Should NOT be deleted
        analysis_subdir = arch_dir / "analysis"
        analysis_subdir.mkdir()
        (analysis_subdir / "some_analysis.json").write_text("{}")

        clean_knowledge("phase1")

        # JSON files should be removed
        assert not (arch_dir / "architecture_facts.json").exists()
        assert not (arch_dir / "evidence_map.json").exists()
        # .md files removed except README.md
        assert not (arch_dir / "some_file.md").exists()
        assert (arch_dir / "README.md").exists()
        # analysis subdir should be removed
        assert not analysis_subdir.exists()

    def test_removes_phase2_artifacts(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        analysis_dir = tmp_path / "knowledge" / "analysis"
        analysis_dir.mkdir(parents=True)
        (analysis_dir / "data.json").write_text("{}")

        clean_knowledge("phase2")

        # The directory is removed and then recreated empty by clean_knowledge()
        assert not (analysis_dir / "data.json").exists()

    def test_removes_phase3_artifacts(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        dev_dir = tmp_path / "knowledge" / "development"
        dev_dir.mkdir(parents=True)
        (dev_dir / "plan.json").write_text("{}")

        clean_knowledge("phase3")

        # The directory is removed and then recreated empty by clean_knowledge()
        assert not (dev_dir / "plan.json").exists()

    def test_clean_all(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        # Create dirs for all phases
        (tmp_path / "knowledge" / "architecture" / "analysis").mkdir(parents=True)
        (tmp_path / "knowledge" / "analysis").mkdir(parents=True)
        (tmp_path / "knowledge" / "development").mkdir(parents=True)
        (tmp_path / "knowledge" / "architecture" / "facts.json").write_text("{}")

        clean_knowledge("all")

        # Subdirs recreated but content removed
        assert not (tmp_path / "knowledge" / "architecture" / "facts.json").exists()
        # Structure is recreated
        assert (tmp_path / "knowledge" / "architecture" / "quality").is_dir()
        assert (tmp_path / "knowledge" / "analysis").is_dir()
        assert (tmp_path / "knowledge" / "development").is_dir()

    def test_noop_when_knowledge_dir_missing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # Should not raise even if knowledge/ does not exist
        clean_knowledge("all")

    def test_recreates_directory_structure(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "knowledge").mkdir()

        clean_knowledge("all")

        assert (tmp_path / "knowledge" / "architecture" / "quality").is_dir()
        assert (tmp_path / "knowledge" / "analysis").is_dir()
        assert (tmp_path / "knowledge" / "development").is_dir()


# =============================================================================
# Orchestrator: SDLCOrchestrator initialization
# =============================================================================

class TestOrchestratorInit:
    """Tests for SDLCOrchestrator construction and config loading."""

    def test_loads_config_from_yaml(self, config_yaml):
        orch = SDLCOrchestrator(config_path=str(config_yaml))
        assert "phases" in orch.config
        assert "presets" in orch.config
        assert "phase0_indexing" in orch.config["phases"]

    def test_missing_config_falls_back_to_default(self, tmp_path):
        missing = str(tmp_path / "nonexistent.yaml")
        orch = SDLCOrchestrator(config_path=missing)
        # Falls back to _default_config()
        assert "phases" in orch.config
        assert "phase0_indexing" in orch.config["phases"]

    def test_empty_yaml_falls_back_to_empty_dict(self, tmp_path):
        empty_cfg = tmp_path / "empty.yaml"
        empty_cfg.write_text("", encoding="utf-8")
        orch = SDLCOrchestrator(config_path=str(empty_cfg))
        # yaml.safe_load("") returns None -> code returns {}
        assert orch.config == {}


# =============================================================================
# Orchestrator: register()
# =============================================================================

class TestOrchestratorRegister:
    """Tests for register() and register_phase()."""

    def test_register_returns_self_for_chaining(self, orchestrator):
        mock_pipeline = MagicMock()
        result = orchestrator.register("phase0_indexing", mock_pipeline)
        assert result is orchestrator

    def test_register_stores_executable(self, orchestrator):
        mock_pipeline = MagicMock()
        orchestrator.register("phase0_indexing", mock_pipeline)
        assert orchestrator.phases["phase0_indexing"] is mock_pipeline

    def test_chaining_multiple_registers(self, orchestrator):
        mock_a = MagicMock()
        mock_b = MagicMock()
        orchestrator.register("phase0_indexing", mock_a).register(
            "phase1_architecture_facts", mock_b
        )
        assert "phase0_indexing" in orchestrator.phases
        assert "phase1_architecture_facts" in orchestrator.phases

    def test_register_phase_is_alias(self, orchestrator):
        mock_pipeline = MagicMock()
        result = orchestrator.register_phase("phase0_indexing", mock_pipeline)
        assert result is orchestrator
        assert orchestrator.phases["phase0_indexing"] is mock_pipeline


# =============================================================================
# Orchestrator: get_presets()
# =============================================================================

class TestOrchestratorGetPresets:
    """Tests for get_presets()."""

    def test_returns_known_presets(self, orchestrator):
        presets = orchestrator.get_presets()
        assert "indexing_only" in presets
        assert "facts_only" in presets
        assert "analysis_only" in presets
        assert "architecture_workflow" in presets
        assert "planning_only" in presets

    def test_returns_list(self, orchestrator):
        presets = orchestrator.get_presets()
        assert isinstance(presets, list)


# =============================================================================
# Orchestrator: get_preset_phases()
# =============================================================================

class TestOrchestratorGetPresetPhases:
    """Tests for get_preset_phases()."""

    def test_architecture_workflow_returns_four_phases(self, orchestrator):
        phases = orchestrator.get_preset_phases("architecture_workflow")
        assert len(phases) == 4
        assert phases == [
            "phase0_indexing",
            "phase1_architecture_facts",
            "phase2_architecture_analysis",
            "phase3_architecture_synthesis",
        ]

    def test_indexing_only_returns_one_phase(self, orchestrator):
        phases = orchestrator.get_preset_phases("indexing_only")
        assert phases == ["phase0_indexing"]

    def test_unknown_preset_returns_empty_list(self, orchestrator):
        phases = orchestrator.get_preset_phases("nonexistent")
        assert phases == []

    def test_planning_only_returns_four_phases(self, orchestrator):
        phases = orchestrator.get_preset_phases("planning_only")
        assert len(phases) == 4
        assert "phase4_development_planning" in phases
        assert "phase3_architecture_synthesis" not in phases


# =============================================================================
# Orchestrator: get_enabled_phases()
# =============================================================================

class TestOrchestratorGetEnabledPhases:
    """Tests for get_enabled_phases()."""

    def test_returns_enabled_phases_in_order(self, orchestrator):
        enabled = orchestrator.get_enabled_phases()
        assert isinstance(enabled, list)
        # All 5 phases in our minimal config are enabled
        assert len(enabled) == 5
        assert enabled[0] == "phase0_indexing"
        assert enabled[1] == "phase1_architecture_facts"
        assert enabled[2] == "phase2_architecture_analysis"
        assert enabled[3] == "phase3_architecture_synthesis"
        assert enabled[4] == "phase4_development_planning"

    def test_disabled_phases_excluded(self, tmp_path):
        config = MINIMAL_PHASES_CONFIG.copy()
        config = {
            **MINIMAL_PHASES_CONFIG,
            "phases": {
                **MINIMAL_PHASES_CONFIG["phases"],
                "phase3_architecture_synthesis": {
                    **MINIMAL_PHASES_CONFIG["phases"]["phase3_architecture_synthesis"],
                    "enabled": False,
                },
            },
        }
        cfg_file = tmp_path / "cfg.yaml"
        cfg_file.write_text(yaml.dump(config), encoding="utf-8")
        orch = SDLCOrchestrator(config_path=str(cfg_file))

        enabled = orch.get_enabled_phases()
        assert "phase3_architecture_synthesis" not in enabled
        assert "phase0_indexing" in enabled


# =============================================================================
# Orchestrator: is_phase_enabled()
# =============================================================================

class TestOrchestratorIsPhaseEnabled:
    """Tests for is_phase_enabled()."""

    def test_enabled_phase_returns_true(self, orchestrator):
        assert orchestrator.is_phase_enabled("phase0_indexing") is True

    def test_all_minimal_config_phases_enabled(self, orchestrator):
        for phase_id in MINIMAL_PHASES_CONFIG["phases"]:
            assert orchestrator.is_phase_enabled(phase_id) is True

    def test_unknown_phase_returns_false(self, orchestrator):
        assert orchestrator.is_phase_enabled("phase99_nonexistent") is False

    def test_disabled_phase_returns_false(self, tmp_path):
        config = {
            "phases": {
                "phase0_indexing": {"enabled": False, "order": 0},
            },
            "presets": {},
        }
        cfg_file = tmp_path / "cfg.yaml"
        cfg_file.write_text(yaml.dump(config), encoding="utf-8")
        orch = SDLCOrchestrator(config_path=str(cfg_file))

        assert orch.is_phase_enabled("phase0_indexing") is False


# =============================================================================
# Orchestrator: _outputs_exist()
# =============================================================================

class TestOutputsExist:
    """Tests for _outputs_exist()."""

    def test_missing_files_returns_false(self, orchestrator, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # No files exist under tmp_path
        assert orchestrator._outputs_exist("phase1_architecture_facts") is False

    def test_phase0_requires_chroma_dir(self, orchestrator, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert orchestrator._outputs_exist("phase0_indexing") is False

        (tmp_path / ".cache" / ".chroma").mkdir(parents=True)
        assert orchestrator._outputs_exist("phase0_indexing") is True

    def test_phase1_requires_both_files(self, orchestrator, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        arch_dir = tmp_path / "knowledge" / "architecture"
        arch_dir.mkdir(parents=True)
        (arch_dir / "architecture_facts.json").write_text("{}")
        # Only one file -- still False
        assert orchestrator._outputs_exist("phase1_architecture_facts") is False

        (arch_dir / "evidence_map.json").write_text("{}")
        assert orchestrator._outputs_exist("phase1_architecture_facts") is True

    def test_phase2_requires_analyzed_json(self, orchestrator, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        arch_dir = tmp_path / "knowledge" / "architecture"
        arch_dir.mkdir(parents=True)
        assert orchestrator._outputs_exist("phase2_architecture_analysis") is False

        (arch_dir / "analyzed_architecture.json").write_text("{}")
        assert orchestrator._outputs_exist("phase2_architecture_analysis") is True

    def test_phase3_requires_c4_context_md(self, orchestrator, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        c4_dir = tmp_path / "knowledge" / "architecture" / "c4"
        c4_dir.mkdir(parents=True)
        assert orchestrator._outputs_exist("phase3_architecture_synthesis") is False

        (c4_dir / "c4-context.md").write_text("# C4 Context")
        assert orchestrator._outputs_exist("phase3_architecture_synthesis") is True

    def test_unknown_phase_returns_false(self, orchestrator, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert orchestrator._outputs_exist("phase99_unknown") is False


# =============================================================================
# Orchestrator: PhaseResult dataclass
# =============================================================================

class TestPhaseResult:
    """Tests for PhaseResult serialization and helpers."""

    def test_is_success(self):
        r = PhaseResult(phase_id="phase0", status="success")
        assert r.is_success() is True

    def test_is_not_success(self):
        r = PhaseResult(phase_id="phase0", status="failed", message="boom")
        assert r.is_success() is False

    def test_to_dict(self):
        r = PhaseResult(
            phase_id="phase1_architecture_facts",
            status="success",
            message="Completed",
            duration_seconds=12.345,
        )
        d = r.to_dict()
        assert d["phase"] == "phase1_architecture_facts"
        assert d["status"] == "success"
        assert d["message"] == "Completed"
        assert d["duration"] == "12.35s"

    def test_to_dict_zero_duration(self):
        r = PhaseResult(phase_id="phase0", status="skipped")
        d = r.to_dict()
        assert d["duration"] == "0.00s"

    def test_default_values(self):
        r = PhaseResult(phase_id="p", status="success")
        assert r.message == ""
        assert r.output is None
        assert r.duration_seconds == 0.0

    def test_serialization_roundtrip_via_json(self):
        r = PhaseResult(
            phase_id="phase2",
            status="failed",
            message="Timeout",
            duration_seconds=60.0,
        )
        serialized = json.dumps(r.to_dict())
        loaded = json.loads(serialized)
        assert loaded["phase"] == "phase2"
        assert loaded["status"] == "failed"


# =============================================================================
# Orchestrator: PipelineResult dataclass
# =============================================================================

class TestPipelineResult:
    """Tests for PipelineResult serialization."""

    def test_to_dict_empty_phases(self):
        pr = PipelineResult(
            status="success",
            message="All done",
            total_duration="0:01:30",
        )
        d = pr.to_dict()
        assert d["status"] == "success"
        assert d["message"] == "All done"
        assert d["phases"] == []
        assert d["total_duration"] == "0:01:30"

    def test_to_dict_with_phases(self):
        phase_results = [
            PhaseResult(phase_id="phase0", status="success", duration_seconds=5.0),
            PhaseResult(phase_id="phase1", status="failed", message="Error", duration_seconds=10.0),
        ]
        pr = PipelineResult(
            status="failed",
            message="Phase phase1 failed",
            phases=phase_results,
            total_duration="0:00:15",
        )
        d = pr.to_dict()
        assert len(d["phases"]) == 2
        assert d["phases"][0]["status"] == "success"
        assert d["phases"][1]["status"] == "failed"
        assert d["phases"][1]["message"] == "Error"

    def test_default_values(self):
        pr = PipelineResult(status="success", message="OK")
        assert pr.phases == []
        assert pr.total_duration == ""

    def test_serialization_roundtrip_via_json(self):
        phase_results = [
            PhaseResult(phase_id="phase0", status="success", duration_seconds=2.5),
        ]
        pr = PipelineResult(
            status="success",
            message="Done",
            phases=phase_results,
            total_duration="0:00:02",
        )
        serialized = json.dumps(pr.to_dict())
        loaded = json.loads(serialized)
        assert loaded["status"] == "success"
        assert len(loaded["phases"]) == 1
        assert loaded["phases"][0]["phase"] == "phase0"


# =============================================================================
# Orchestrator: context property (backward compatibility)
# =============================================================================

class TestOrchestratorContext:
    """Tests for the backward-compat context property."""

    def test_context_empty_before_run(self, orchestrator):
        ctx = orchestrator.context
        assert ctx["phases"] == {}
        assert ctx["knowledge"] == {}
        assert ctx["shared"] == {}

    def test_context_populated_after_results(self, orchestrator):
        orchestrator.results["phase0_indexing"] = PhaseResult(
            phase_id="phase0_indexing",
            status="success",
            output={"indexed": 100},
        )
        ctx = orchestrator.context
        assert "phase0_indexing" in ctx["phases"]
        assert ctx["phases"]["phase0_indexing"]["status"] == "success"
        assert ctx["phases"]["phase0_indexing"]["output"] == {"indexed": 100}


# =============================================================================
# Orchestrator: get_phase_config()
# =============================================================================

class TestOrchestratorGetPhaseConfig:
    """Tests for get_phase_config()."""

    def test_returns_config_dict(self, orchestrator):
        cfg = orchestrator.get_phase_config("phase0_indexing")
        assert cfg["enabled"] is True
        assert cfg["name"] == "Repository Indexing"
        assert cfg["order"] == 0

    def test_unknown_phase_returns_empty_dict(self, orchestrator):
        cfg = orchestrator.get_phase_config("phase99_nonexistent")
        assert cfg == {}


# =============================================================================
# Integration: Orchestrator uses real config file from project
# =============================================================================

class TestOrchestratorWithRealConfig:
    """Verify the orchestrator works against the actual project config."""

    REAL_CONFIG = r"c:\projects\aicodegencrew\config\phases_config.yaml"

    @pytest.fixture
    def real_orchestrator(self):
        return SDLCOrchestrator(config_path=self.REAL_CONFIG)

    def test_real_config_loads_all_phases(self, real_orchestrator):
        phases = real_orchestrator.config.get("phases", {})
        assert "phase0_indexing" in phases
        assert "phase1_architecture_facts" in phases
        assert "phase2_architecture_analysis" in phases
        assert "phase3_architecture_synthesis" in phases
        assert "phase4_development_planning" in phases

    def test_real_config_architecture_workflow_has_4_phases(self, real_orchestrator):
        phases = real_orchestrator.get_preset_phases("architecture_workflow")
        assert len(phases) == 4

    def test_real_config_presets_match_expected(self, real_orchestrator):
        presets = real_orchestrator.get_presets()
        assert "indexing_only" in presets
        assert "facts_only" in presets
        assert "analysis_only" in presets
        assert "architecture_workflow" in presets
        assert "planning_only" in presets
        assert "architecture_full" in presets
        assert "full_pipeline" in presets

    def test_real_config_enabled_phases_are_ordered(self, real_orchestrator):
        enabled = real_orchestrator.get_enabled_phases()
        # Check ordering by extracting phase numbers
        orders = []
        for phase_id in enabled:
            cfg = real_orchestrator.get_phase_config(phase_id)
            orders.append(cfg.get("order", 999))
        assert orders == sorted(orders), "Enabled phases must be sorted by order"


# =============================================================================
# Orchestrator: run() with mocked executables
# =============================================================================

class TestOrchestratorRun:
    """Tests for the run() method with mock executables (no LLM)."""

    def test_run_with_no_registered_phases_returns_failed(self, orchestrator):
        result = orchestrator.run(preset="indexing_only")
        assert result.status == "failed"
        assert "No phases to run" in result.message

    def test_run_executes_registered_phase(self, orchestrator):
        # Use spec to avoid MagicMock auto-creating .run(), .crew(), etc.
        # _invoke_executable checks hasattr(run), hasattr(crew) before kickoff.
        mock_pipeline = MagicMock(spec=["kickoff"])
        mock_pipeline.kickoff.return_value = {"status": "ok"}

        orchestrator.register("phase0_indexing", mock_pipeline)

        # Patch archive_knowledge and _git_commit_after_phase to avoid side effects
        with patch.object(orchestrator, "archive_knowledge"), \
             patch.object(orchestrator, "_git_commit_after_phase"):
            result = orchestrator.run(phases=["phase0_indexing"])

        assert result.status == "success"
        mock_pipeline.kickoff.assert_called_once()

    def test_run_stops_on_error(self, orchestrator):
        # Use spec=["kickoff"] so _invoke_executable hits the kickoff path
        failing = MagicMock(spec=["kickoff"])
        failing.kickoff.side_effect = RuntimeError("Kaboom")

        succeeding = MagicMock(spec=["kickoff"])
        succeeding.kickoff.return_value = {"status": "ok"}

        orchestrator.register("phase0_indexing", failing)
        orchestrator.register("phase1_architecture_facts", succeeding)

        with patch.object(orchestrator, "archive_knowledge"), \
             patch.object(orchestrator, "_git_commit_after_phase"), \
             patch.object(orchestrator, "_check_dependencies", return_value=True):
            result = orchestrator.run(
                phases=["phase0_indexing", "phase1_architecture_facts"],
                stop_on_error=True,
            )

        assert result.status == "failed"
        # Phase 1 should NOT have been called because phase 0 failed
        succeeding.kickoff.assert_not_called()
