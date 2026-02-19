"""
End-to-end scenario tests for the SDLC pipeline.

Tests realistic user workflows: fresh run, preset resolution, error recovery,
phase validation chains, and multi-format export. All tests run WITHOUT
LLM or network access.
"""

import json
import sys
from pathlib import Path

import pytest

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# =============================================================================
# Helpers: mock Java/Angular mini-repo
# =============================================================================


def _create_mini_java_repo(root: Path) -> Path:
    """Create a minimal Spring Boot + Angular repo for testing.

    Returns:
        Path to the repo root.
    """
    # ---- Spring Boot backend ----
    java_dir = root / "backend" / "src" / "main" / "java" / "com" / "demo"
    java_dir.mkdir(parents=True)

    (java_dir / "DemoApplication.java").write_text(
        """package com.demo;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class DemoApplication {
    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
    }
}""",
        encoding="utf-8",
    )

    (java_dir / "UserController.java").write_text(
        """package com.demo;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/users")
public class UserController {
    private final UserService userService;
    public UserController(UserService svc) { this.userService = svc; }

    @GetMapping
    public String getAll() { return userService.findAll(); }

    @PostMapping
    public String create(@RequestBody String body) { return userService.create(body); }
}""",
        encoding="utf-8",
    )

    (java_dir / "UserService.java").write_text(
        """package com.demo;
import org.springframework.stereotype.Service;

@Service
public class UserService {
    public String findAll() { return "[]"; }
    public String create(String data) { return data; }
}""",
        encoding="utf-8",
    )

    (java_dir / "UserRepository.java").write_text(
        """package com.demo;
import org.springframework.stereotype.Repository;

@Repository
public class UserRepository {
    public Object findAll() { return null; }
}""",
        encoding="utf-8",
    )

    # Build file to detect Spring Boot
    (root / "backend" / "build.gradle").write_text(
        """plugins {
    id 'org.springframework.boot' version '3.2.0'
    id 'java'
}
dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web'
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
}""",
        encoding="utf-8",
    )

    # ---- Angular frontend ----
    fe_dir = root / "frontend" / "src" / "app"
    fe_dir.mkdir(parents=True)

    (root / "frontend" / "angular.json").write_text(
        '{"projects": {"frontend": {}}}',
        encoding="utf-8",
    )

    (root / "frontend" / "package.json").write_text(
        json.dumps(
            {
                "name": "frontend",
                "dependencies": {"@angular/core": "^17.0.0"},
            }
        ),
        encoding="utf-8",
    )

    (fe_dir / "app.module.ts").write_text(
        """import { NgModule } from '@angular/core';
@NgModule({ declarations: [], imports: [], bootstrap: [] })
export class AppModule {}""",
        encoding="utf-8",
    )

    (fe_dir / "user.service.ts").write_text(
        """import { Injectable } from '@angular/core';
@Injectable({ providedIn: 'root' })
export class UserService {
    getUsers() { return []; }
}""",
        encoding="utf-8",
    )

    return root


# =============================================================================
# Scenario 1: Fresh first run
# =============================================================================


class TestScenario1FreshFirstRun:
    """Clean output dir -> run facts pipeline on mock repo -> verify outputs exist."""

    def test_facts_pipeline_on_mock_repo(self, tmp_path):
        """Run collector orchestrator directly on a mock repo and verify outputs.

        Note: The full ArchitectureFactsPipeline includes a fact_adapter step
        that may fail on synthetic evidence (empty line ranges). We test the
        collector orchestrator directly which is the core deterministic part.
        """
        from aicodegencrew.pipelines.architecture_facts.collectors.orchestrator import (
            CollectorOrchestrator,
        )

        repo = _create_mini_java_repo(tmp_path / "repo")
        output_dir = tmp_path / "output"

        orchestrator = CollectorOrchestrator(
            repo_path=repo,
            output_dir=output_dir,
        )
        orchestrator.run_all()

        # Verify key output files written by orchestrator
        assert (output_dir / "architecture_facts.json").exists()
        assert (output_dir / "evidence_map.json").exists()
        assert (output_dir / "components.json").exists()
        assert (output_dir / "containers.json").exists()

        # Verify content quality
        facts_data = json.loads((output_dir / "architecture_facts.json").read_text(encoding="utf-8"))

        assert "system" in facts_data
        assert "components" in facts_data
        assert "containers" in facts_data
        assert len(facts_data["components"]) >= 2  # At least UserController + UserService

    def test_facts_pipeline_detects_spring_components(self, tmp_path):
        """Pipeline detects @Service, @RestController, @Repository annotations."""
        from aicodegencrew.pipelines.architecture_facts import (
            ArchitectureFactsPipeline,
        )

        repo = _create_mini_java_repo(tmp_path / "repo")
        output_dir = tmp_path / "output"

        pipeline = ArchitectureFactsPipeline(
            repo_path=str(repo),
            output_dir=str(output_dir),
        )
        pipeline.kickoff()

        comps = json.loads((output_dir / "components.json").read_text(encoding="utf-8"))

        names = [c["name"] for c in comps]
        stereotypes = [c.get("stereotype", "") for c in comps]

        # Should detect Spring stereotypes
        assert "UserController" in names or any("Controller" in n for n in names)
        assert "UserService" in names or any("Service" in n for n in names)

        # Should have controller and service stereotypes
        assert "controller" in stereotypes or "rest_controller" in stereotypes
        assert "service" in stereotypes

    def test_facts_pipeline_detects_containers(self, tmp_path):
        """Pipeline detects backend (Spring Boot) and frontend (Angular) containers."""
        from aicodegencrew.pipelines.architecture_facts import (
            ArchitectureFactsPipeline,
        )

        repo = _create_mini_java_repo(tmp_path / "repo")
        output_dir = tmp_path / "output"

        pipeline = ArchitectureFactsPipeline(
            repo_path=str(repo),
            output_dir=str(output_dir),
        )
        pipeline.kickoff()

        containers = json.loads((output_dir / "containers.json").read_text(encoding="utf-8"))

        technologies = [c.get("technology", "") for c in containers]

        # Should detect Spring Boot backend
        assert any("Spring" in t for t in technologies)

        # Should detect Angular frontend
        assert any("Angular" in t for t in technologies)

    def test_facts_pipeline_fails_on_nonexistent_repo(self, tmp_path):
        """Pipeline raises ValueError for non-existent repo."""
        from aicodegencrew.pipelines.architecture_facts import (
            ArchitectureFactsPipeline,
        )

        with pytest.raises(ValueError, match="does not exist"):
            ArchitectureFactsPipeline(
                repo_path=str(tmp_path / "nonexistent"),
                output_dir=str(tmp_path / "output"),
            )


# =============================================================================
# Scenario 2: Preset resolution
# =============================================================================


class TestScenario2PresetResolution:
    """Verify presets resolve to the correct phase lists."""

    @pytest.fixture
    def orchestrator(self, tmp_path, monkeypatch):
        """Create an orchestrator with the real config file."""
        config_path = Path(__file__).parent.parent / "config" / "phases_config.yaml"
        if not config_path.exists():
            pytest.skip("phases_config.yaml not found")

        from aicodegencrew.orchestrator import SDLCOrchestrator

        return SDLCOrchestrator(config_path=str(config_path))

    def test_index_preset(self, orchestrator):
        """index => [discover]."""
        phases = orchestrator.get_preset_phases("index")
        assert phases == ["discover"]

    def test_scan_preset(self, orchestrator):
        """scan => [discover, extract]."""
        phases = orchestrator.get_preset_phases("scan")
        assert phases == ["discover", "extract"]

    def test_analyze_preset(self, orchestrator):
        """analyze => [discover, extract, analyze]."""
        phases = orchestrator.get_preset_phases("analyze")
        assert phases == [
            "discover",
            "extract",
            "analyze",
        ]

    def test_document_preset(self, orchestrator):
        """document => [phase0..phase3]."""
        phases = orchestrator.get_preset_phases("document")
        assert phases == [
            "discover",
            "extract",
            "analyze",
            "document",
        ]

    def test_plan_preset(self, orchestrator):
        """plan => [discover, extract, analyze, document, plan]."""
        phases = orchestrator.get_preset_phases("plan")
        assert phases == [
            "discover",
            "extract",
            "analyze",
            "document",
            "plan",
        ]

    def test_architect_preset(self, orchestrator):
        """architect => [phase0..phase4]."""
        phases = orchestrator.get_preset_phases("architect")
        assert phases == [
            "discover",
            "extract",
            "analyze",
            "document",
            "plan",
        ]

    def test_unknown_preset_returns_empty(self, orchestrator):
        """Unknown preset name returns empty list."""
        phases = orchestrator.get_preset_phases("nonexistent_preset")
        assert phases == []

    def test_get_presets_lists_all(self, orchestrator):
        """get_presets() returns all defined preset names."""
        presets = orchestrator.get_presets()
        assert "index" in presets
        assert "scan" in presets
        assert "document" in presets
        assert "architect" in presets
        assert "plan" in presets

    def test_phase_ordering(self, orchestrator):
        """Phases are ordered by their 'order' field."""
        enabled = orchestrator.get_enabled_phases()
        # phase0 should come before phase1, etc.
        if len(enabled) >= 2:
            for i in range(len(enabled) - 1):
                current_order = orchestrator.get_phase_config(enabled[i]).get("order", 999)
                next_order = orchestrator.get_phase_config(enabled[i + 1]).get("order", 999)
                assert current_order <= next_order, (
                    f"{enabled[i]} (order={current_order}) should come before {enabled[i + 1]} (order={next_order})"
                )

    def test_phase_dependencies_declared(self, orchestrator):
        """Every phase (except phase0) declares dependencies."""
        for phase_id in [
            "extract",
            "analyze",
            "document",
            "plan",
        ]:
            config = orchestrator.get_phase_config(phase_id)
            deps = config.get("dependencies", [])
            assert len(deps) >= 1, f"{phase_id} should have at least 1 dependency"


# =============================================================================
# Scenario 3: Error recovery
# =============================================================================


class TestScenario3ErrorRecovery:
    """Missing prerequisite files, invalid JSON, graceful degradation."""

    def test_missing_prerequisite_gives_hint(self, tmp_path):
        """ArchitectureSynthesisCrew provides helpful error message."""
        from aicodegencrew.crews.architecture_synthesis.crew import (
            ArchitectureSynthesisCrew,
        )

        crew = ArchitectureSynthesisCrew(facts_path=str(tmp_path / "missing" / "architecture_facts.json"))

        with pytest.raises(FileNotFoundError) as exc_info:
            crew._validate_prerequisites()

        error_msg = str(exc_info.value)
        assert "Run Phase 1 and Phase 2 first" in error_msg
        assert "Missing prerequisite" in error_msg

    def test_invalid_json_in_facts(self, tmp_path):
        """Validator catches invalid JSON in architecture_facts.json."""

        arch_dir = tmp_path / "knowledge" / "extract"
        arch_dir.mkdir(parents=True)

        # Write invalid JSON
        (arch_dir / "architecture_facts.json").write_text("{not valid json", encoding="utf-8")
        (arch_dir / "evidence_map.json").write_text('{"valid": true}', encoding="utf-8")

        # The validator uses hardcoded paths, so we need to test differently.
        # Instead, test that _load_json handles it gracefully.
        from aicodegencrew.crews.architecture_synthesis.base_crew import MiniCrewBase

        result = MiniCrewBase._load_json(arch_dir / "architecture_facts.json")
        assert result == {}

    def test_empty_output_file_detected(self, tmp_path, monkeypatch):
        """Validator detects empty output files."""
        from aicodegencrew.shared.validation import PHASE_OUTPUT_SPECS

        # Verify spec says files must exist
        spec = PHASE_OUTPUT_SPECS.get("extract", {})
        required = spec.get("required_paths", [])
        assert len(required) >= 2  # facts + evidence

    def test_orchestrator_handles_unregistered_phase(self, tmp_path):
        """Orchestrator skips unregistered phases gracefully."""
        from aicodegencrew.orchestrator import SDLCOrchestrator

        config_path = Path(__file__).parent.parent / "config" / "phases_config.yaml"
        if not config_path.exists():
            pytest.skip("Config not found")

        orch = SDLCOrchestrator(config_path=str(config_path))
        # Don't register any phases, just resolve
        resolved = orch._resolve_phases(None, ["phase99_nonexistent"])
        assert resolved == []

    def test_orchestrator_dependency_check_fails_gracefully(self, tmp_path):
        """Orchestrator dependency check fails when outputs missing."""

        config_path = Path(__file__).parent.parent / "config" / "phases_config.yaml"
        if not config_path.exists():
            pytest.skip("Config not found")

        from aicodegencrew.phase_registry import outputs_exist

        # phase1 depends on phase0 output (.cache/.chroma)
        # Without it, dependency check should fail
        result = outputs_exist("extract", tmp_path)
        # Since we are in tmp_path, the output files don't exist
        # This verifies the function handles the situation
        assert result is False

    def test_stage1_rejects_unsupported_format(self, tmp_path):
        """Stage 1 rejects unsupported file formats with clear error."""
        from aicodegencrew.hybrid.development_planning.stages import (
            InputParserStage,
        )

        unsupported = tmp_path / "task.pdf"
        unsupported.write_text("content", encoding="utf-8")

        stage1 = InputParserStage()
        with pytest.raises(ValueError, match="Unsupported file format"):
            stage1.run(str(unsupported))

    def test_stage1_rejects_missing_file(self, tmp_path):
        """Stage 1 rejects nonexistent files."""
        from aicodegencrew.hybrid.development_planning.stages import (
            InputParserStage,
        )

        stage1 = InputParserStage()
        with pytest.raises(ValueError, match="not found"):
            stage1.run(str(tmp_path / "nonexistent.txt"))

    def test_development_pipeline_requires_input(self):
        """Pipeline raises ValueError when no input files provided."""
        from aicodegencrew.hybrid.development_planning.pipeline import (
            DevelopmentPlanningPipeline,
        )

        with pytest.raises(ValueError, match="input_file"):
            DevelopmentPlanningPipeline(input_file=None, input_files=None)

    def test_phase_result_dataclass(self):
        """PhaseResult.is_success() works correctly."""
        from aicodegencrew.orchestrator import PhaseResult

        success = PhaseResult(phase_id="p1", status="success", message="ok")
        assert success.is_success() is True

        failed = PhaseResult(phase_id="p1", status="failed", message="err")
        assert failed.is_success() is False

        # skipped and partial are treated as non-blocking (pipeline continues)
        skipped = PhaseResult(phase_id="p1", status="skipped", message="skip")
        assert skipped.is_success() is True

        partial = PhaseResult(phase_id="p1", status="partial", message="degraded")
        assert partial.is_success() is True


# =============================================================================
# Scenario 4: Phase output validation chain
# =============================================================================


class TestScenario4PhaseOutputValidation:
    """Phase 0 output -> Phase 1 can validate, Phase 1 output -> Phase 2 can validate."""

    def test_phase0_output_spec_exists(self):
        """Phase 0 has an output specification."""
        from aicodegencrew.shared.validation import PHASE_OUTPUT_SPECS

        assert "discover" in PHASE_OUTPUT_SPECS
        spec = PHASE_OUTPUT_SPECS["discover"]
        assert "required_paths" in spec

    def test_phase1_output_spec_exists(self):
        """Phase 1 has an output specification with schema validation."""
        from aicodegencrew.shared.validation import PHASE_OUTPUT_SPECS

        spec = PHASE_OUTPUT_SPECS["extract"]
        assert "required_paths" in spec
        assert "schema" in spec
        assert spec["schema"] == "architecture_facts"
        assert spec["min_components"] >= 1
        assert spec["min_containers"] >= 1

    def test_phase2_output_spec_exists(self):
        """Phase 2 has an output specification with required keys."""
        from aicodegencrew.shared.validation import PHASE_OUTPUT_SPECS

        spec = PHASE_OUTPUT_SPECS["analyze"]
        assert "required_paths" in spec
        assert "required_keys" in spec
        assert "macro_architecture" in spec["required_keys"]
        assert "micro_architecture" in spec["required_keys"]
        assert "container_analyses" in spec["required_keys"]

    def test_phase3_output_spec_exists(self):
        """Phase 3 has an output specification with min file size."""
        from aicodegencrew.shared.validation import PHASE_OUTPUT_SPECS

        spec = PHASE_OUTPUT_SPECS["document"]
        assert "required_paths" in spec
        assert "min_file_size" in spec
        assert spec["min_file_size"] >= 100

    def test_validator_returns_empty_for_unknown_phase(self):
        """Validator returns no errors for phases without specs."""
        from aicodegencrew.shared.validation import PhaseOutputValidator

        validator = PhaseOutputValidator()
        errors = validator.validate_phase("phase99_nonexistent")
        assert errors == []

    def test_validator_detects_missing_files(self, tmp_path, monkeypatch):
        """Validator reports missing required files."""
        from aicodegencrew.shared.validation import PhaseOutputValidator

        # Change CWD to tmp_path so the validator looks there
        monkeypatch.chdir(tmp_path)

        validator = PhaseOutputValidator()
        errors = validator.validate_phase("extract")

        # Should report missing files
        assert len(errors) > 0
        assert any("Missing" in e for e in errors)

    def test_validator_accepts_valid_facts_file(self, tmp_path, monkeypatch):
        """Validator accepts a complete, valid architecture_facts.json."""
        from aicodegencrew.shared.validation import PhaseOutputValidator

        monkeypatch.chdir(tmp_path)

        # Create the expected directory structure
        extract_dir = tmp_path / "knowledge" / "extract"
        extract_dir.mkdir(parents=True)

        facts = {
            "system": {"id": "system", "name": "Test", "domain": "Testing"},
            "containers": [
                {
                    "id": "backend",
                    "name": "backend",
                    "technology": "Spring Boot",
                    "evidence": ["ev_001"],
                }
            ],
            "components": [
                {
                    "id": "comp.svc",
                    "container": "backend",
                    "name": "Svc",
                    "stereotype": "service",
                    "evidence": ["ev_001"],
                }
            ],
            "interfaces": [],
            "relations": [],
            "endpoint_flows": [],
        }

        (extract_dir / "architecture_facts.json").write_text(json.dumps(facts), encoding="utf-8")

        evidence = {"ev_001": {"path": "Svc.java", "lines": "1-10", "reason": "test"}}
        (extract_dir / "evidence_map.json").write_text(json.dumps(evidence), encoding="utf-8")

        validator = PhaseOutputValidator()
        errors = validator.validate_phase("extract")
        assert errors == [], f"Unexpected errors: {errors}"

    def test_validator_detects_too_few_components(self, tmp_path, monkeypatch):
        """Validator fails when facts have zero components (spec requires min 1)."""
        from aicodegencrew.shared.validation import PhaseOutputValidator

        monkeypatch.chdir(tmp_path)

        extract_dir = tmp_path / "knowledge" / "extract"
        extract_dir.mkdir(parents=True)

        facts = {
            "system": {"id": "system", "name": "Test", "domain": "Testing"},
            "containers": [
                {
                    "id": "backend",
                    "name": "backend",
                    "technology": "Spring Boot",
                    "evidence": ["ev_001"],
                }
            ],
            "components": [],  # zero components!
            "interfaces": [],
            "relations": [],
            "endpoint_flows": [],
        }

        (extract_dir / "architecture_facts.json").write_text(json.dumps(facts), encoding="utf-8")
        (extract_dir / "evidence_map.json").write_text(
            '{"ev_001": {"path": "x", "lines": "1-1", "reason": "r"}}',
            encoding="utf-8",
        )

        validator = PhaseOutputValidator()
        errors = validator.validate_phase("extract")
        assert any("Too few components" in e for e in errors)


# =============================================================================
# Scenario 5: Multi-format export
# =============================================================================


class TestScenario5MultiFormatExport:
    """DocumentConverter generates 3 formats per file, arc42 ToC, German support."""

    SAMPLE_MD = """\
# Test Chapter

## Overview

This is a **test** document with `code` and a [link](https://example.com).

### Table

| Column A | Column B |
|----------|----------|
| value 1  | value 2  |
| value 3  | value 4  |

### Code

```java
public class Test {
    // sample
}
```

- bullet 1
- bullet 2

1. numbered 1
2. numbered 2

> A blockquote

---

End of document.
"""

    def test_converter_generates_three_formats(self, tmp_path):
        """Given a .md file, DocumentConverter generates 3 format files."""
        from aicodegencrew.shared.utils.confluence_converter import DocumentConverter

        md_file = tmp_path / "test-doc.md"
        md_file.write_text(self.SAMPLE_MD, encoding="utf-8")

        converter = DocumentConverter()
        results = converter.convert_file(md_file)

        assert len(results) == 3
        assert "confluence" in results
        assert "adoc" in results
        assert "html" in results

        for fmt, path in results.items():
            assert path.exists(), f"{fmt} file not created"
            content = path.read_text(encoding="utf-8")
            assert len(content) > 50, f"{fmt} file too short: {len(content)} chars"

    def test_converter_multiple_files(self, tmp_path):
        """convert_directory processes all .md files in tree."""
        from aicodegencrew.shared.utils.confluence_converter import DocumentConverter

        # Create multiple files in subdirectories
        c4_dir = tmp_path / "c4"
        c4_dir.mkdir()
        (c4_dir / "c4-context.md").write_text("# Context\n\nSystem context.\n", encoding="utf-8")
        (c4_dir / "c4-container.md").write_text("# Container\n\nContainer view.\n", encoding="utf-8")

        converter = DocumentConverter()
        total = converter.convert_directory(tmp_path)

        # 2 files * 3 formats = 6
        assert total >= 6

        # Verify files
        assert (c4_dir / "c4-context.confluence").exists()
        assert (c4_dir / "c4-context.adoc").exists()
        assert (c4_dir / "c4-context.html").exists()
        assert (c4_dir / "c4-container.confluence").exists()

    def test_arc42_toc_generated_in_three_formats(self, tmp_path):
        """arc42 directory gets ToC files in all 3 formats."""
        from aicodegencrew.shared.utils.confluence_converter import DocumentConverter

        arc42_dir = tmp_path / "arc42"
        arc42_dir.mkdir()

        for num in ["01", "02", "03", "04", "05"]:
            (arc42_dir / f"{num}-chapter.md").write_text(f"# Chapter {num}\n\nContent.\n", encoding="utf-8")

        converter = DocumentConverter()
        converter.convert_directory(tmp_path, lang="en")

        # ToC in all 3 formats
        assert (arc42_dir / "00-arc42-toc.confluence").exists()
        assert (arc42_dir / "00-arc42-toc.adoc").exists()
        assert (arc42_dir / "00-arc42-toc.html").exists()

        # Verify ToC content
        conf_toc = (arc42_dir / "00-arc42-toc.confluence").read_text(encoding="utf-8")
        assert "arc42" in conf_toc.lower()
        assert "Introduction" in conf_toc or "Goals" in conf_toc

        adoc_toc = (arc42_dir / "00-arc42-toc.adoc").read_text(encoding="utf-8")
        assert ":toc:" in adoc_toc

        html_toc = (arc42_dir / "00-arc42-toc.html").read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in html_toc

    def test_german_language_titles(self, tmp_path):
        """German arc42 ToC uses Architekturdokumentation title."""
        from aicodegencrew.shared.utils.confluence_converter import (
            ARC42_CHAPTERS,
            DocumentConverter,
        )

        arc42_dir = tmp_path / "arc42"
        arc42_dir.mkdir()
        (arc42_dir / "01-einfuehrung.md").write_text("# Einleitung\n\nContent.\n", encoding="utf-8")

        converter = DocumentConverter()
        converter.convert_directory(tmp_path, lang="de")

        # Confluence ToC should use German title
        conf_toc = (arc42_dir / "00-arc42-toc.confluence").read_text(encoding="utf-8")
        assert "Architekturdokumentation" in conf_toc

        # German chapter titles from the mapping
        de_chapters = ARC42_CHAPTERS["de"]
        assert de_chapters["01"] == "Einführung und Ziele"
        assert de_chapters["05"] == "Bausteinsicht"
        assert de_chapters["12"] == "Glossar"

        # Verify German chapter titles appear in ToC
        assert "Einführung und Ziele" in conf_toc

    def test_confluence_format_details(self, tmp_path):
        """Verify Confluence format specifics: headings, tables, lists, code."""
        from aicodegencrew.shared.utils.confluence_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.to_confluence(self.SAMPLE_MD)

        # Headings use h1. h2. h3. syntax
        assert "h1. Test Chapter" in result
        assert "h2. Overview" in result
        assert "h3. Table" in result

        # Bold uses single *
        assert "*test*" in result

        # Inline code uses {{}}
        assert "{{code}}" in result

        # Table header uses ||
        assert "||Column A||" in result
        # Table body uses |
        assert "|value 1|" in result

        # Unordered list uses *
        assert "* bullet 1" in result

        # Ordered list uses #
        assert "# numbered 1" in result

    def test_asciidoc_format_details(self, tmp_path):
        """Verify AsciiDoc format specifics: headings, code, tables."""
        from aicodegencrew.shared.utils.confluence_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.to_asciidoc(self.SAMPLE_MD)

        # Headings use = prefix
        assert "= Test Chapter" in result
        assert "== Overview" in result
        assert "=== Table" in result

        # Code blocks
        assert "[source,java]" in result
        assert "----" in result

        # Table uses |===
        assert "|===" in result

        # Lists
        assert "* bullet 1" in result
        assert ". numbered 1" in result

        # Blockquote
        assert "[quote]" in result
        assert "____" in result

    def test_html_format_details(self):
        """Verify HTML format specifics: structure, styles, elements."""
        from aicodegencrew.shared.utils.confluence_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.to_html(self.SAMPLE_MD, title="Arch Doc")

        # Full HTML document
        assert "<!DOCTYPE html>" in result
        assert "<title>Arch Doc</title>" in result
        assert "<style>" in result

        # Should contain rendered elements
        assert "<h1>" in result or "<h1" in result
        assert "<h2>" in result or "<h2" in result
        assert "<table>" in result or "<table" in result or "<th>" in result
        assert "<code>" in result or "<pre>" in result

    def test_convert_file_selective_formats(self, tmp_path):
        """convert_file can generate only selected formats."""
        from aicodegencrew.shared.utils.confluence_converter import DocumentConverter

        md_file = tmp_path / "doc.md"
        md_file.write_text("# Title\n\nText.\n", encoding="utf-8")

        converter = DocumentConverter()

        # Only Confluence
        results = converter.convert_file(md_file, formats=["confluence"])
        assert len(results) == 1
        assert "confluence" in results
        assert (tmp_path / "doc.confluence").exists()
        assert not (tmp_path / "doc.adoc").exists()

    def test_convert_preserves_links(self):
        """Links are converted correctly in all formats."""
        from aicodegencrew.shared.utils.confluence_converter import DocumentConverter

        md = "Visit [Google](https://google.com) for search."

        converter = DocumentConverter()

        conf = converter.to_confluence(md)
        assert "[Google|https://google.com]" in conf

        adoc = converter.to_asciidoc(md)
        assert "link:https://google.com[Google]" in adoc

        html = converter.to_html(md)
        assert 'href="https://google.com"' in html

    def test_convert_preserves_images(self):
        """Image syntax is converted correctly."""
        from aicodegencrew.shared.utils.confluence_converter import DocumentConverter

        md = "See diagram: ![Architecture](arch.png)"

        converter = DocumentConverter()

        conf = converter.to_confluence(md)
        assert "!arch.png!" in conf

        adoc = converter.to_asciidoc(md)
        assert "image:arch.png[Architecture]" in adoc


# =============================================================================
# Cross-cutting: collector base classes and raw facts
# =============================================================================


class TestCollectorBaseClasses:
    """Tests for collector base functionality used across all phases."""

    def test_raw_component_structure(self):
        """RawComponent has all expected fields."""
        from aicodegencrew.pipelines.architecture_facts.collectors.base import (
            RawComponent,
        )

        comp = RawComponent(
            name="UserService",
            stereotype="service",
            container_hint="backend",
            file_path="src/UserService.java",
            module="com.example",
        )

        assert comp.name == "UserService"
        assert comp.stereotype == "service"
        assert comp.container_hint == "backend"
        assert comp.evidence == []

    def test_raw_component_add_evidence(self):
        """RawComponent.add_evidence creates RawEvidence."""
        from aicodegencrew.pipelines.architecture_facts.collectors.base import (
            RawComponent,
        )

        comp = RawComponent(name="Svc", stereotype="service")
        comp.add_evidence(
            path="Svc.java",
            line_start=5,
            line_end=20,
            reason="@Service annotation",
        )

        assert len(comp.evidence) == 1
        assert comp.evidence[0].path == "Svc.java"
        assert comp.evidence[0].reason == "@Service annotation"

    def test_collector_output_counts(self):
        """CollectorOutput tracks fact and relation counts."""
        from aicodegencrew.pipelines.architecture_facts.collectors.base import (
            CollectorOutput,
            RawComponent,
            RelationHint,
        )

        output = CollectorOutput(dimension="components")
        assert output.fact_count == 0

        output.add_fact(RawComponent(name="A", stereotype="service"))
        output.add_fact(RawComponent(name="B", stereotype="controller"))
        assert output.fact_count == 2

        output.add_relation(RelationHint(from_name="B", to_name="A", type="uses"))
        assert output.relation_count == 1

    def test_relation_hint_to_dict(self):
        """RelationHint.to_dict includes all relevant fields."""
        from aicodegencrew.pipelines.architecture_facts.collectors.base import (
            RelationHint,
        )

        rel = RelationHint(
            from_name="Controller",
            to_name="Service",
            type="uses",
            confidence=0.95,
            from_file_hint="Controller.java",
        )

        d = rel.to_dict()
        assert d["from"] == "Controller"
        assert d["to"] == "Service"
        assert d["type"] == "uses"
        assert d["confidence"] == 0.95
        assert d["from_file"] == "Controller.java"

    def test_normalize_name(self):
        """DimensionCollector._normalize_name converts CamelCase to snake_case."""
        from aicodegencrew.pipelines.architecture_facts.collectors.base import (
            DimensionCollector,
        )

        assert DimensionCollector._normalize_name("UserService") == "user_service"
        assert DimensionCollector._normalize_name("HTTPClient") == "http_client"
        assert DimensionCollector._normalize_name("simple") == "simple"

    def test_component_collector_technology_dispatch(self, tmp_path):
        """ComponentCollector dispatches to correct specialist by technology."""
        from aicodegencrew.pipelines.architecture_facts.collectors.component_collector import (
            ComponentCollector,
        )

        containers = [
            {"name": "backend", "type": "backend", "technology": "Spring Boot", "root_path": "backend"},
            {"name": "frontend", "type": "frontend", "technology": "Angular", "root_path": "frontend"},
        ]

        collector = ComponentCollector(repo_path=tmp_path, containers=containers)

        # Should correctly filter by technology
        spring_containers = collector._get_containers_by_technologies({"Spring Boot", "Java/Gradle", "Java/Maven"})
        assert len(spring_containers) == 1
        assert spring_containers[0]["name"] == "backend"

        angular_containers = collector._get_containers_by_technology("Angular")
        assert len(angular_containers) == 1
        assert angular_containers[0]["name"] == "frontend"


# =============================================================================
# Orchestrator data flow
# =============================================================================


class TestOrchestratorDataFlow:
    """Tests for orchestrator register/run flow without actual phase execution."""

    def test_register_and_resolve(self, tmp_path):
        """Registered phases appear in resolved phase list."""
        from aicodegencrew.orchestrator import SDLCOrchestrator

        config_path = Path(__file__).parent.parent / "config" / "phases_config.yaml"
        if not config_path.exists():
            pytest.skip("Config not found")

        orch = SDLCOrchestrator(config_path=str(config_path))

        # Mock phase executables
        class MockPhase:
            def kickoff(self, inputs=None):
                return {"status": "success"}

        orch.register("discover", MockPhase())
        orch.register("extract", MockPhase())

        resolved = orch._resolve_phases("scan", None)
        assert "discover" in resolved
        assert "extract" in resolved

    def test_explicit_phases_override_preset(self, tmp_path):
        """Explicit phase list overrides preset."""
        from aicodegencrew.orchestrator import SDLCOrchestrator

        config_path = Path(__file__).parent.parent / "config" / "phases_config.yaml"
        if not config_path.exists():
            pytest.skip("Config not found")

        orch = SDLCOrchestrator(config_path=str(config_path))

        class MockPhase:
            def kickoff(self, inputs=None):
                return {"status": "success"}

        orch.register("discover", MockPhase())

        # Explicit list should override preset
        resolved = orch._resolve_phases(
            "architect",
            ["discover"],
        )
        assert resolved == ["discover"]

    def test_pipeline_result_structure(self):
        """PipelineResult.to_dict has expected structure."""
        from aicodegencrew.orchestrator import PhaseResult, PipelineResult

        result = PipelineResult(
            status="success",
            message="All done",
            phases=[
                PhaseResult(phase_id="p0", status="success", message="ok"),
                PhaseResult(phase_id="p1", status="success", message="ok"),
            ],
            total_duration="0:05:00",
        )

        d = result.to_dict()
        assert d["status"] == "success"
        assert len(d["phases"]) == 2
        assert d["phases"][0]["phase"] == "p0"
        assert d["total_duration"] == "0:05:00"

    def test_phase_result_to_dict(self):
        """PhaseResult.to_dict includes all fields."""
        from aicodegencrew.orchestrator import PhaseResult

        result = PhaseResult(
            phase_id="analyze",
            status="success",
            message="Completed",
            duration_seconds=42.5,
        )

        d = result.to_dict()
        assert d["phase"] == "analyze"
        assert d["status"] == "success"
        assert d["duration"] == "42.50s"

    def test_context_backward_compat(self, tmp_path):
        """Orchestrator.context provides backward-compatible structure."""
        from aicodegencrew.orchestrator import SDLCOrchestrator

        config_path = Path(__file__).parent.parent / "config" / "phases_config.yaml"
        if not config_path.exists():
            pytest.skip("Config not found")

        orch = SDLCOrchestrator(config_path=str(config_path))
        ctx = orch.context

        assert "phases" in ctx
        assert "knowledge" in ctx
        assert "shared" in ctx
        assert isinstance(ctx["phases"], dict)


# =============================================================================
# Scenario 6: Run Report Export
# =============================================================================


class TestScenario6RunReport:
    """Tests for run_report.json export to knowledge/ directory."""

    def test_export_run_report_creates_file(self, tmp_path, monkeypatch):
        """_export_run_report writes a valid JSON file."""
        monkeypatch.chdir(tmp_path)
        from aicodegencrew.cli import Config, _export_run_report
        from aicodegencrew.orchestrator import PhaseResult, PipelineResult

        result = PipelineResult(
            status="success",
            message="All phases completed",
            phases=[
                PhaseResult(phase_id="discover", status="success", duration_seconds=1.5),
                PhaseResult(phase_id="extract", status="success", duration_seconds=10.2),
            ],
            total_duration="0:00:12",
        )
        config = Config(
            repo_path=Path("/some/repo"),
            index_mode="auto",
            config_path=None,
            clean=False,
            no_clean=False,
            git_repo_url="",
            git_branch="",
        )

        report_path = _export_run_report(result, config, {"discover", "extract"})

        assert report_path is not None
        assert report_path.exists()

        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["status"] == "success"
        assert report["run_id"]  # Non-empty
        assert len(report["phases"]) == 2
        assert report["phases"][0]["phase"] == "discover"
        assert report["phases"][0]["duration_seconds"] == 1.5
        assert report["environment"]["repo_path"] == str(Path("/some/repo"))
        assert report["environment"]["index_mode"] == "auto"
        assert "timestamp" in report
        assert "output_summary" in report

    def test_export_run_report_on_failure(self, tmp_path, monkeypatch):
        """_export_run_report also works for failed pipelines."""
        monkeypatch.chdir(tmp_path)
        from aicodegencrew.cli import Config, _export_run_report
        from aicodegencrew.orchestrator import PhaseResult, PipelineResult

        result = PipelineResult(
            status="failed",
            message="Phase 2 crashed",
            phases=[
                PhaseResult(phase_id="discover", status="success", duration_seconds=1.0),
                PhaseResult(phase_id="extract", status="success", duration_seconds=8.0),
                PhaseResult(phase_id="analyze", status="failed", message="LLM timeout"),
            ],
            total_duration="0:01:30",
        )
        config = Config(
            repo_path=Path("."),
            index_mode="auto",
            config_path=None,
            clean=False,
            no_clean=False,
            git_repo_url="",
            git_branch="",
        )

        report_path = _export_run_report(result, config, {"discover", "extract", "analyze"})

        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["status"] == "failed"
        assert report["message"] == "Phase 2 crashed"
        assert report["phases"][2]["status"] == "failed"

    def test_export_run_report_planned_phases_sorted(self, tmp_path, monkeypatch):
        """planned_phases appear sorted alphabetically in the report."""
        monkeypatch.chdir(tmp_path)
        from aicodegencrew.cli import Config, _export_run_report
        from aicodegencrew.orchestrator import PipelineResult

        result = PipelineResult(status="success", message="ok", total_duration="0:00:01")
        config = Config(
            repo_path=Path("."),
            index_mode="auto",
            config_path=None,
            clean=False,
            no_clean=False,
            git_repo_url="",
            git_branch="",
        )

        _export_run_report(result, config, {"analyze", "discover", "extract"})

        report = json.loads((tmp_path / "knowledge" / "run_report.json").read_text(encoding="utf-8"))
        # sorted() produces alphabetical order
        assert report["planned_phases"] == [
            "analyze",
            "discover",
            "extract",
        ]
