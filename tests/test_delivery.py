"""
Tests for delivery, packaging, and release readiness.

Covers:
- Version management (scripts/build_release.py)
- Package structure (pyproject.toml)
- Delivery artifacts (.env.example, docker-compose.yml, Dockerfile, etc.)
- Documentation completeness (README.md, USER_GUIDE.md, etc.)
- Code quality (no print in production, no hardcoded keys, __init__.py coverage)
- .gitignore correctness
"""

import ast
import re
import sys
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src" / "aicodegencrew"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# Make build_release importable
sys.path.insert(0, str(SCRIPTS_DIR))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_text(path: Path) -> str:
    """Read a file as UTF-8 text."""
    return path.read_text(encoding="utf-8")


def _load_pyproject() -> dict:
    """Parse pyproject.toml into a dict (simple TOML-like parser, no dependency)."""
    # We parse it minimally since we cannot guarantee 'tomllib' on 3.10
    content = _read_text(PROJECT_ROOT / "pyproject.toml")
    # For detailed checks we just inspect the raw text; for structured checks
    # we rely on the build_release helpers.
    return content


# ============================================================================
# 1. Version Management  (scripts/build_release.py)
# ============================================================================


class TestVersionManagement:
    """Tests for get_version() and bump_version() in build_release.py."""

    def _import_build_release(self):
        """Import the build_release module."""
        # Ensure the module can be re-imported cleanly
        if "build_release" in sys.modules:
            del sys.modules["build_release"]
        import build_release

        return build_release

    def test_get_version_parses_from_pyproject(self):
        """get_version() should return the version string from pyproject.toml."""
        br = self._import_build_release()
        version = br.get_version()
        # Must be a valid semver-ish string
        assert re.match(r"^\d+\.\d+\.\d+$", version), f"get_version() returned '{version}', expected X.Y.Z format"

    def test_bump_version_patch(self):
        """bump_version('0.1.0', 'patch') should return '0.1.1'."""
        br = self._import_build_release()
        assert br.bump_version("0.1.0", "patch") == "0.1.1"

    def test_bump_version_minor(self):
        """bump_version('0.1.0', 'minor') should return '0.2.0'."""
        br = self._import_build_release()
        assert br.bump_version("0.1.0", "minor") == "0.2.0"

    def test_bump_version_major(self):
        """bump_version('0.1.0', 'major') should return '1.0.0'."""
        br = self._import_build_release()
        assert br.bump_version("0.1.0", "major") == "1.0.0"

    def test_bump_version_patch_higher(self):
        """bump_version('1.2.3', 'patch') should return '1.2.4'."""
        br = self._import_build_release()
        assert br.bump_version("1.2.3", "patch") == "1.2.4"

    def test_bump_version_invalid_part_exits(self):
        """bump_version with invalid part should call sys.exit."""
        br = self._import_build_release()
        with pytest.raises(SystemExit):
            br.bump_version("0.1.0", "invalid")

    def test_bump_version_minor_resets_patch(self):
        """bump_version('1.2.3', 'minor') should reset patch to 0."""
        br = self._import_build_release()
        assert br.bump_version("1.2.3", "minor") == "1.3.0"

    def test_bump_version_major_resets_minor_and_patch(self):
        """bump_version('1.2.3', 'major') should reset minor and patch to 0."""
        br = self._import_build_release()
        assert br.bump_version("1.2.3", "major") == "2.0.0"


# ============================================================================
# 2. Package Structure  (pyproject.toml)
# ============================================================================


class TestPackageStructure:
    """Tests for pyproject.toml validity and required fields."""

    @pytest.fixture(autouse=True)
    def _load_toml(self):
        self.toml_path = PROJECT_ROOT / "pyproject.toml"
        self.content = _read_text(self.toml_path)

    def test_pyproject_toml_exists(self):
        """pyproject.toml must exist at project root."""
        assert self.toml_path.exists(), "pyproject.toml not found"

    def test_pyproject_has_project_section(self):
        """pyproject.toml must have a [project] section."""
        assert "[project]" in self.content

    def test_pyproject_has_name(self):
        """pyproject.toml must define name = 'aicodegencrew'."""
        assert re.search(r'^name\s*=\s*"aicodegencrew"', self.content, re.MULTILINE)

    def test_pyproject_has_version(self):
        """pyproject.toml must define a version field."""
        assert re.search(r'^version\s*=\s*"\d+\.\d+\.\d+"', self.content, re.MULTILINE)

    def test_pyproject_has_required_dependencies(self):
        """pyproject.toml must list all core dependencies."""
        required_deps = [
            "crewai",
            "chromadb",
            "python-dotenv",
            "pydantic",
            "pyyaml",
            "jinja2",
            "requests",
            "ollama",
        ]
        for dep in required_deps:
            assert dep in self.content.lower(), f"Required dependency '{dep}' not found in pyproject.toml"

    def test_pyproject_has_parsers_optional_deps(self):
        """pyproject.toml must have a 'parsers' optional dependency group."""
        assert re.search(r"^\[project\.optional-dependencies\]", self.content, re.MULTILINE)
        # Check for parsers group
        assert re.search(r"^parsers\s*=\s*\[", self.content, re.MULTILINE), (
            "'parsers' optional dependency group not found"
        )

    def test_pyproject_build_backend_is_hatchling(self):
        """Build backend must be hatchling."""
        assert 'build-backend = "hatchling.build"' in self.content

    def test_pyproject_wheel_packages(self):
        """Wheel packages must point to src/aicodegencrew."""
        assert re.search(
            r'packages\s*=\s*\["src/aicodegencrew"\]',
            self.content,
        ), "Wheel packages must be ['src/aicodegencrew']"

    def test_pyproject_has_build_system(self):
        """pyproject.toml must have a [build-system] section."""
        assert "[build-system]" in self.content

    def test_pyproject_requires_hatchling(self):
        """Build system requires must include hatchling."""
        assert 'requires = ["hatchling"]' in self.content


# ============================================================================
# 3. Delivery Artifacts
# ============================================================================


class TestDeliveryArtifacts:
    """Tests for delivery files: .env.example, docker-compose, Dockerfile, config."""

    # --- .env.example ---

    def test_env_example_exists(self):
        """.env.example must exist at project root."""
        assert (PROJECT_ROOT / ".env.example").exists()

    def test_env_example_has_no_real_api_keys(self):
        """.env.example must not contain real API keys (only placeholders)."""
        content = _read_text(PROJECT_ROOT / ".env.example")
        # Check that OPENAI_API_KEY is set to a placeholder, not a real key
        for line in content.splitlines():
            line_stripped = line.strip()
            if line_stripped.startswith("#"):
                continue
            if "OPENAI_API_KEY" in line_stripped:
                # Must contain placeholder text, not a real key
                value = line_stripped.split("=", 1)[1].strip() if "=" in line_stripped else ""
                assert "sk-" not in value, "Real OpenAI key found in .env.example!"
                assert (
                    value
                    in (
                        "your-api-key-here",
                        "",
                        "changeme",
                        "your_api_key_here",
                    )
                    or "your" in value.lower()
                    or "placeholder" in value.lower()
                    or "here" in value.lower()
                ), f"OPENAI_API_KEY value '{value}' looks like a real key"

    def test_env_example_has_documented_env_vars(self):
        """.env.example must have all core documented environment variables."""
        content = _read_text(PROJECT_ROOT / ".env.example")
        required_vars = [
            "PROJECT_PATH",
            "LLM_PROVIDER",
            "MODEL",
            "API_BASE",
            "OPENAI_API_KEY",
            "OLLAMA_BASE_URL",
            "EMBED_MODEL",
            "INDEX_MODE",
            "CHROMA_DIR",
            "OUTPUT_DIR",
            "LOG_LEVEL",
            "MAX_LLM_INPUT_TOKENS",
            "MAX_LLM_OUTPUT_TOKENS",
            "LLM_CONTEXT_WINDOW",
        ]
        for var in required_vars:
            assert var in content, f"Environment variable '{var}' not found in .env.example"

    # --- docker-compose.yml ---

    def test_docker_compose_exists(self):
        """docker-compose.yml must exist at project root."""
        assert (PROJECT_ROOT / "docker-compose.yml").exists()

    def test_docker_compose_valid_yaml(self):
        """docker-compose.yml must be valid YAML."""
        content = _read_text(PROJECT_ROOT / "docker-compose.yml")
        data = yaml.safe_load(content)
        assert isinstance(data, dict), "docker-compose.yml did not parse to a dict"

    def test_docker_compose_has_services(self):
        """docker-compose.yml must define services."""
        content = _read_text(PROJECT_ROOT / "docker-compose.yml")
        data = yaml.safe_load(content)
        assert "services" in data, "No 'services' key in docker-compose.yml"
        assert "aicodegencrew" in data["services"], "No 'aicodegencrew' service defined"

    def test_docker_compose_mounts_required_volumes(self):
        """docker-compose.yml must mount .env, repo, knowledge, and cache volumes."""
        content = _read_text(PROJECT_ROOT / "docker-compose.yml")
        # Check for key volume patterns (raw text since YAML anchors can vary)
        required_volume_patterns = [
            ".env",  # Configuration mount
            "/repo",  # Target repository
            "knowledge",  # Output directory
            ".cache",  # ChromaDB cache
        ]
        for pattern in required_volume_patterns:
            assert pattern in content, f"Volume mount pattern '{pattern}' not found in docker-compose.yml"

    # --- Dockerfile ---

    def test_dockerfile_exists(self):
        """Dockerfile must exist at project root."""
        assert (PROJECT_ROOT / "Dockerfile").exists(), "Dockerfile not found at project root"

    # --- config/phases_config.yaml ---

    def test_phases_config_exists(self):
        """config/phases_config.yaml must exist."""
        assert (PROJECT_ROOT / "config" / "phases_config.yaml").exists()

    def test_phases_config_valid_yaml(self):
        """config/phases_config.yaml must be valid YAML."""
        content = _read_text(PROJECT_ROOT / "config" / "phases_config.yaml")
        data = yaml.safe_load(content)
        assert isinstance(data, dict)

    def test_phases_config_has_phases_section(self):
        """phases_config.yaml must have a 'phases' section."""
        content = _read_text(PROJECT_ROOT / "config" / "phases_config.yaml")
        data = yaml.safe_load(content)
        assert "phases" in data, "No 'phases' key in phases_config.yaml"

    def test_phases_config_has_presets(self):
        """phases_config.yaml must have a 'presets' section."""
        content = _read_text(PROJECT_ROOT / "config" / "phases_config.yaml")
        data = yaml.safe_load(content)
        assert "presets" in data, "No 'presets' key in phases_config.yaml"

    def test_phases_config_has_core_phases(self):
        """phases_config.yaml must define phase0 through phase3."""
        content = _read_text(PROJECT_ROOT / "config" / "phases_config.yaml")
        data = yaml.safe_load(content)
        phases = data.get("phases", {})
        required_phases = [
            "phase0_indexing",
            "phase1_architecture_facts",
            "phase2_architecture_analysis",
            "phase3_architecture_synthesis",
        ]
        for phase_name in required_phases:
            assert phase_name in phases, f"Phase '{phase_name}' not found in phases_config.yaml"

    def test_phases_config_phase_structure(self):
        """Each phase in phases_config.yaml must have name, type, and order."""
        content = _read_text(PROJECT_ROOT / "config" / "phases_config.yaml")
        data = yaml.safe_load(content)
        phases = data.get("phases", {})
        for phase_id, phase_cfg in phases.items():
            assert "name" in phase_cfg, f"Phase '{phase_id}' missing 'name'"
            assert "type" in phase_cfg, f"Phase '{phase_id}' missing 'type'"
            assert "order" in phase_cfg, f"Phase '{phase_id}' missing 'order'"
            assert phase_cfg["type"] in ("pipeline", "crew"), (
                f"Phase '{phase_id}' has invalid type: {phase_cfg['type']}"
            )

    # --- install scripts (generated into dist/release by build_release.py) ---
    # These only exist after a build; test at project root is conditional.

    def test_install_bat_in_release_if_built(self):
        """If dist/release exists, install.bat must be present."""
        release_dir = PROJECT_ROOT / "dist" / "release"
        if release_dir.exists():
            assert (release_dir / "install.bat").exists(), "install.bat not found in dist/release/"

    def test_install_sh_in_release_if_built(self):
        """If dist/release exists, install.sh must be present."""
        release_dir = PROJECT_ROOT / "dist" / "release"
        if release_dir.exists():
            assert (release_dir / "install.sh").exists(), "install.sh not found in dist/release/"


# ============================================================================
# 4. Documentation Completeness
# ============================================================================


class TestDocumentationCompleteness:
    """Tests that required documentation files exist and are substantive."""

    def test_readme_exists(self):
        """README.md must exist at project root."""
        assert (PROJECT_ROOT / "README.md").exists()

    def test_readme_is_substantive(self):
        """README.md must be >1000 characters."""
        content = _read_text(PROJECT_ROOT / "README.md")
        assert len(content) > 1000, f"README.md is only {len(content)} chars, expected >1000"

    def test_user_guide_exists(self):
        """docs/USER_GUIDE.md must exist."""
        assert (PROJECT_ROOT / "docs" / "USER_GUIDE.md").exists()

    def test_user_guide_has_all_12_sections(self):
        """docs/USER_GUIDE.md must have all 12 sections."""
        content = _read_text(PROJECT_ROOT / "docs" / "USER_GUIDE.md")
        expected_sections = [
            "Overview",
            "Installation",
            "Configuration",
            "Quick Start",
            "Commands",
            "Input Files",
            "Output Files",
            "Presets",
            "Environment Variables",
            "Docker Usage",
            "Troubleshooting",
            "FAQ",
        ]
        for section in expected_sections:
            # Match "## N. Section" or "## Section" patterns
            pattern = rf"##\s+(\d+\.\s+)?{re.escape(section)}"
            assert re.search(pattern, content, re.IGNORECASE), f"Section '{section}' not found in USER_GUIDE.md"

    def test_delivery_guide_exists(self):
        """docs/DELIVERY_GUIDE.md must exist."""
        assert (PROJECT_ROOT / "docs" / "DELIVERY_GUIDE.md").exists()

    def test_changelog_exists(self):
        """CHANGELOG.md must exist at project root."""
        assert (PROJECT_ROOT / "CHANGELOG.md").exists()

    def test_changelog_has_version_entry(self):
        """CHANGELOG.md must have at least one version entry."""
        content = _read_text(PROJECT_ROOT / "CHANGELOG.md")
        assert re.search(r"##\s+\[\d+\.\d+\.\d+\]", content), "CHANGELOG.md has no version entry (## [X.Y.Z])"


# ============================================================================
# 5. Code Quality
# ============================================================================


class TestCodeQuality:
    """Tests for code hygiene: no print(), no hardcoded keys, __init__.py coverage."""

    # --- No print() in production code ---

    def _get_production_py_files(self) -> list[Path]:
        """Return all .py files under src/aicodegencrew/ (production code)."""
        return sorted(SRC_DIR.rglob("*.py"))

    def _get_script_and_test_paths(self) -> set[str]:
        """Return directory names that are allowed to have print() statements."""
        return {"scripts", "tests", "test", "e2e"}

    def test_no_print_in_production_code(self):
        """Production code (src/aicodegencrew/) must not contain print() calls.

        Exceptions:
        - CLI modules (cli.py) -- CLI output is inherently print-based
        - __main__.py files (entry points)
        - Comments (lines starting with #)
        - Lines inside ``if __name__ == "__main__"`` guard blocks
        - String literals (docstrings, comments containing the word 'print')
        """
        # Files that are allowed to use print() freely
        allowed_files = {"cli.py", "__main__.py"}

        # Modules where print() is acceptable for specific reasons:
        #   logger.py - bootstrap fallback when logging setup itself fails
        allowed_modules = {"logger.py"}

        violations = []
        for py_file in self._get_production_py_files():
            if py_file.name in allowed_files:
                continue
            if py_file.name in allowed_modules:
                continue

            try:
                source = py_file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            lines = source.splitlines()
            in_main_guard = False
            in_print_method = False

            for i, line in enumerate(lines, 1):
                stripped = line.strip()

                # Track if we are inside an ``if __name__`` guard
                if re.match(r'^if\s+__name__\s*==\s*["\']__main__["\']', stripped):
                    in_main_guard = True
                    continue
                # Reset when we hit a top-level (non-indented) line that is not blank
                if in_main_guard and line and not line[0].isspace():
                    in_main_guard = False

                if in_main_guard:
                    continue

                # Track if we are inside a method named print_* (diagnostic methods)
                if re.match(r"def\s+print_\w+", stripped):
                    in_print_method = True
                    continue
                # Reset when we encounter a new def/class at same or lower indent
                if in_print_method and re.match(r"(def |class )", stripped):
                    in_print_method = False

                if in_print_method:
                    continue

                # Skip comments
                if stripped.startswith("#"):
                    continue
                # Skip lines that are purely string literals (docstrings, etc.)
                if stripped.startswith(('"""', "'''", '"', "'", "- ")):
                    continue
                # Detect bare print( calls
                if re.search(r"\bprint\s*\(", stripped):
                    violations.append(f"{py_file.relative_to(PROJECT_ROOT)}:{i}: {stripped[:100]}")

        # Core library modules (crews, pipelines, shared) should have zero print().
        # We allow none -- any print() outside of CLI/main/scripts/logger/print_methods
        # is a bug.
        assert not violations, (
            f"Found {len(violations)} print() statements in production code "
            f"(excluding cli.py, __main__.py, logger.py, __main__ guards, "
            f"print_* methods):\n" + "\n".join(violations)
        )

    # --- No hardcoded API keys ---

    def test_no_hardcoded_api_keys_in_source(self):
        """Source code must not contain hardcoded API keys."""
        dangerous_patterns = [
            r"sk-[a-zA-Z0-9]{20,}",  # OpenAI-style keys
            r'api_key\s*=\s*"[^"]{20,}"',  # Generic long key assignment
            r'OPENAI_API_KEY\s*=\s*"sk-',  # Explicit OpenAI key
            r"Bearer\s+sk-[a-zA-Z0-9]{20,}",  # Bearer token with key
        ]
        violations = []
        for py_file in self._get_production_py_files():
            try:
                source = py_file.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            for pattern in dangerous_patterns:
                matches = re.findall(pattern, source)
                if matches:
                    violations.append(f"{py_file.relative_to(PROJECT_ROOT)}: matches pattern '{pattern}'")

        assert not violations, "Hardcoded API keys found in source code:\n" + "\n".join(violations)

    # --- __init__.py coverage ---

    def test_all_package_dirs_have_init_py(self):
        """Every directory under src/aicodegencrew/ containing .py files must have __init__.py."""
        missing = []
        for py_file in SRC_DIR.rglob("*.py"):
            parent = py_file.parent
            if parent == SRC_DIR:
                continue
            # Skip __pycache__ directories
            if "__pycache__" in str(parent):
                continue
            init_file = parent / "__init__.py"
            if not init_file.exists():
                rel = str(parent.relative_to(PROJECT_ROOT))
                if rel not in [str(m) for m in missing]:
                    missing.append(parent)

        missing_strs = [str(m.relative_to(PROJECT_ROOT)) for m in missing]
        # Deduplicate
        missing_strs = sorted(set(missing_strs))
        assert not missing_strs, f"Missing __init__.py in {len(missing_strs)} package directories:\n" + "\n".join(
            missing_strs
        )

    # --- No syntax errors ---

    def test_no_syntax_errors_in_py_files(self):
        """All .py files under src/ must be syntactically valid (parseable by ast)."""
        errors = []
        for py_file in SRC_DIR.rglob("*.py"):
            try:
                source = py_file.read_bytes()
                ast.parse(source, filename=str(py_file))
            except SyntaxError as e:
                errors.append(f"{py_file.relative_to(PROJECT_ROOT)}:{e.lineno}: {e.msg}")

        assert not errors, f"Syntax errors found in {len(errors)} files:\n" + "\n".join(errors)


# ============================================================================
# 6. Gitignore
# ============================================================================


class TestGitignore:
    """Tests that .gitignore contains critical entries."""

    @pytest.fixture(autouse=True)
    def _load_gitignore(self):
        self.gitignore_path = PROJECT_ROOT / ".gitignore"
        self.content = _read_text(self.gitignore_path)
        # Parse into a list of non-comment, non-empty lines
        self.entries = []
        for line in self.content.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                self.entries.append(stripped)

    def test_gitignore_exists(self):
        """.gitignore must exist."""
        assert self.gitignore_path.exists()

    def test_env_is_in_gitignore(self):
        """.env must be in .gitignore."""
        assert ".env" in self.entries, ".env not found in .gitignore entries"

    def test_cache_is_in_gitignore(self):
        """.cache/ must be in .gitignore."""
        assert any(entry in (".cache/", ".cache") for entry in self.entries), ".cache/ not found in .gitignore"

    def test_pycache_is_in_gitignore(self):
        """__pycache__/ must be in .gitignore."""
        assert any("__pycache__" in entry for entry in self.entries), "__pycache__/ not found in .gitignore"

    def test_dist_is_in_gitignore(self):
        """dist/ (build artifacts) must be in .gitignore."""
        assert any(entry in ("dist/", "dist") for entry in self.entries), "dist/ not found in .gitignore"

    def test_env_example_is_not_ignored(self):
        """.env.example must NOT be ignored (negation pattern should exist)."""
        assert "!.env.example" in self.entries, ".env.example is not excluded from .env* ignore pattern"

    def test_knowledge_archive_is_ignored(self):
        """knowledge/architecture/archive/ should be in .gitignore."""
        assert any("archive" in entry and "knowledge" in entry for entry in self.entries), (
            "knowledge/architecture/archive/ not found in .gitignore"
        )

    def test_checkpoint_files_are_ignored(self):
        """Checkpoint files (.checkpoint_*.json) should be in .gitignore."""
        assert any(".checkpoint_" in entry or "checkpoint" in entry.lower() for entry in self.entries), (
            "Checkpoint files not found in .gitignore"
        )

    def test_venv_is_in_gitignore(self):
        """Virtual environment directories must be in .gitignore."""
        assert any(entry in (".venv/", "venv/", ".venv", "venv") for entry in self.entries), (
            "Virtual environment directory not found in .gitignore"
        )

    def test_logs_dir_is_in_gitignore(self):
        """logs/ directory must be in .gitignore."""
        assert any(entry in ("logs/", "logs", "/logs/", "/logs") for entry in self.entries), (
            "logs/ not found in .gitignore"
        )
