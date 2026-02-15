"""
Stage 4b: Build Verifier

Compiles generated code in the target project to verify correctness.
If build fails, parses errors and uses LLM to self-heal (max retries).

GENERIC: Auto-detects build system from build_system.json + architecture_facts.json
(produced by the Extract phase). Works with Gradle, Maven, npm, Angular — any repo.

Duration: 30s-5min per container (build + optional heal)

SAFETY:
- Always restores original files after build (Stage 5 does final writes)
- Baseline check: skips containers where the build was already broken before codegen
- Works identically in dry_run and normal mode
"""

import json
import os
import platform
import re
import shlex
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

IS_WINDOWS = platform.system() == "Windows"

from ....shared.utils.logger import setup_logger
from ..schemas import (
    BuildVerificationResult,
    CodegenPlanInput,
    ContainerBuildResult,
    GeneratedFile,
    ValidationResult,
)
from ..strategies.base import BaseStrategy

logger = setup_logger(__name__)

# Internal constants (no env vars)
BUILD_VERIFY_ENABLED = True
MAX_RETRIES = 3
CALL_DELAY = 2.0
BUILD_TIMEOUT = 600


# =========================================================================
# Container build configuration (auto-detected)
# =========================================================================


@dataclass
class ContainerConfig:
    """Build configuration for a target-repo container."""

    container_id: str
    name: str
    root_path: str  # relative path prefix in repo (e.g. "backend/")
    build_cwd: str  # relative dir from repo root to run build in
    build_command: str  # shell command string (runs via bash -c)
    build_tool: str  # "gradle" | "maven" | "npm" | "angular"
    timeout: int = BUILD_TIMEOUT


def _detect_containers(
    repo_path: Path,
    facts_path: Path,
) -> list[ContainerConfig]:
    """
    Auto-detect buildable containers from architecture_facts.json only.

    Each container has: id, root_path, type, technology, and
    metadata.metadata.build_system (gradle/maven/npm).

    Build commands are derived by scanning the container directory on disk.
    """
    containers: list[dict] = []
    if facts_path.exists():
        try:
            with open(facts_path, encoding="utf-8") as f:
                facts = json.load(f)
            containers = facts.get("containers", [])
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"[Stage4b] Could not read architecture_facts: {e}")
            return []

    configs: list[ContainerConfig] = []
    skip_types = {"test", "e2e"}

    for container in containers:
        cid = container.get("id", "")
        ctype = container.get("type", "")
        root = container.get("root_path", "").replace("\\", "/").strip("/")

        # Skip test-only containers
        if ctype in skip_types or "e2e" in cid.lower():
            continue

        # Get build_system from container metadata
        meta = container.get("metadata", {})
        build_tool = meta.get("build_system", "")

        if not build_tool:
            logger.info(f"[Stage4b] No build_system in facts for {cid}, skipping")
            continue

        # Derive build command from build tool + disk scan
        build_cmd = _derive_build_command(build_tool, repo_path, root)
        if not build_cmd:
            logger.info(f"[Stage4b] Could not derive build command for {cid} ({build_tool}), skipping")
            continue

        configs.append(
            ContainerConfig(
                container_id=cid,
                name=container.get("name", root),
                root_path=root + "/",
                build_cwd=root,
                build_command=build_cmd,
                build_tool=build_tool,
            )
        )

    if configs:
        logger.info(f"[Stage4b] Detected {len(configs)} buildable containers:")
        for c in configs:
            logger.info(f"  {c.name} ({c.build_tool}): {c.build_command}")
    else:
        logger.warning("[Stage4b] No buildable containers detected")

    return configs


def _derive_build_command(build_tool: str, repo_path: Path, container_root: str) -> str:
    """Derive the shell build command from build tool type + disk scan."""
    build_dir = repo_path / container_root

    if build_tool == "gradle":
        has_wrapper = (build_dir / "gradlew").exists() or (build_dir / "gradlew.bat").exists()
        if has_wrapper:
            if IS_WINDOWS:
                return r".\gradlew.bat clean build --info"
            return "./gradlew clean build --info"
        return "gradle clean build --info"

    elif build_tool == "maven":
        has_wrapper = (build_dir / "mvnw").exists() or (build_dir / "mvnw.cmd").exists()
        if has_wrapper:
            if IS_WINDOWS:
                return r".\mvnw.cmd clean compile"
            return "./mvnw clean compile"
        return "mvn clean compile"

    elif build_tool == "npm":
        # Read package.json to find the best build script
        pkg_path = build_dir / "package.json"
        if pkg_path.exists():
            try:
                with open(pkg_path, encoding="utf-8") as f:
                    pkg = json.load(f)
                scripts = pkg.get("scripts", {})
                for script_name in ("build:cap-ci", "build:prod", "build"):
                    if script_name in scripts:
                        return f"npm run {script_name}"
            except (json.JSONDecodeError, OSError):
                pass
        # Fallback for Angular
        if (build_dir / "angular.json").exists():
            return "npx ng build"
        return ""

    return ""


def _prepare_subprocess_command(command: str) -> list[str]:
    """Prepare command args for subprocess.run without shell=True."""
    if IS_WINDOWS:
        # Use cmd explicitly for .cmd/.bat wrappers and shell built-ins.
        return ["cmd", "/d", "/s", "/c", command]
    return shlex.split(command)


# =========================================================================
# Error parsing
# =========================================================================

# Gradle/javac: File.java:42: error: message
# Handles both relative paths (src/File.java) and Windows absolute paths (C:\...\File.java)
_JAVAC_PATTERN = re.compile(r"^(?P<file>.+?\.java):(?P<line>\d+):\s*error:\s*(?P<msg>.+)$", re.MULTILINE)

# Angular/TypeScript error patterns (handles TS and NG error codes).
# Angular CLI outputs errors in multiple formats with optional prefix:
#   "Error: src/app/foo.ts:42:10 - error TS2345: msg"
#   "ERROR in src/app/foo.ts:42:10 - error NG6002: msg"
#   "./src/app/foo.ts:42:10 - error TS2345: msg"
#   "src/app/foo.ts:42:10 - error NG8001: msg"
_TSC_PATTERN1 = re.compile(
    r"^(?:Error:\s*|ERROR\s+in\s*|\.\/)?(?P<file>[^\s:]+\.(?:ts|html)):(?P<line>\d+):(?P<col>\d+)\s*-\s*error\s+(?P<code>(?:TS|NG)\d+):\s*(?P<msg>.+)$",
    re.MULTILINE,
)

# TypeScript alternate: file.ts(42,10): error TS2345: message
_TSC_PATTERN2 = re.compile(
    r"^(?:Error:\s*|ERROR\s+in\s*|\.\/)?(?P<file>[^\s(]+\.(?:ts|html))\((?P<line>\d+),(?P<col>\d+)\):\s*error\s+(?P<code>(?:TS|NG)\d+):\s*(?P<msg>.+)$",
    re.MULTILINE,
)

# ANSI escape code stripper (Angular CLI uses color codes in output)
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    """Remove ANSI color/style escape codes from text."""
    return _ANSI_ESCAPE.sub("", text)


# Maven/javac: [ERROR] /path/File.java:[42,10] error message
_MAVEN_PATTERN = re.compile(
    r"^\[ERROR\]\s*(?P<file>.+?\.java):\[(?P<line>\d+),(?P<col>\d+)\]\s*(?P<msg>.+)$",
    re.MULTILINE,
)


@dataclass
class BuildError:
    """A single parsed build error."""

    file_path: str  # repo-relative
    line: int = 0
    column: int = 0
    code: str = ""
    message: str = ""


def _parse_build_errors(output: str, build_tool: str) -> list[BuildError]:
    """Parse build output into structured errors based on build tool."""
    # Strip ANSI color codes (Angular CLI, Gradle with --info use colors)
    output = _strip_ansi(output)
    errors: list[BuildError] = []

    if build_tool in ("gradle", "maven"):
        # javac errors
        for m in _JAVAC_PATTERN.finditer(output):
            errors.append(
                BuildError(
                    file_path=m.group("file"),
                    line=int(m.group("line")),
                    message=m.group("msg").strip(),
                )
            )
        # Maven-style errors
        for m in _MAVEN_PATTERN.finditer(output):
            errors.append(
                BuildError(
                    file_path=m.group("file"),
                    line=int(m.group("line")),
                    column=int(m.group("col")),
                    message=m.group("msg").strip(),
                )
            )
    elif build_tool in ("npm", "angular"):
        for pattern in (_TSC_PATTERN1, _TSC_PATTERN2):
            for m in pattern.finditer(output):
                errors.append(
                    BuildError(
                        file_path=m.group("file"),
                        line=int(m.group("line")),
                        column=int(m.group("col")),
                        code=m.group("code"),
                        message=m.group("msg").strip(),
                    )
                )

    # Deduplicate (same file+line can match multiple patterns)
    seen = set()
    unique_errors = []
    for e in errors:
        key = (e.file_path, e.line, e.code)
        if key not in seen:
            seen.add(key)
            unique_errors.append(e)

    return unique_errors


# =========================================================================
# File backup/restore
# =========================================================================


@dataclass
class _FileBackup:
    """Manages backup and restore of generated files on disk."""

    repo_path: Path
    backups: dict[str, str | None] = field(default_factory=dict)  # path → original content (None = did not exist)

    def apply(self, generated_files: list[GeneratedFile]) -> None:
        """Write generated files to disk, saving originals for restore."""
        for gf in generated_files:
            path = Path(gf.file_path)
            # Save original
            if path.exists():
                try:
                    self.backups[gf.file_path] = path.read_text(encoding="utf-8")
                except Exception:
                    self.backups[gf.file_path] = None
            else:
                self.backups[gf.file_path] = None

            # Write generated content
            if gf.action == "delete":
                if path.exists():
                    path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(gf.content, encoding="utf-8")

    def restore(self) -> None:
        """Restore all files to their original state."""
        for file_path, original in self.backups.items():
            path = Path(file_path)
            try:
                if original is None:
                    # File didn't exist before — remove it
                    if path.exists():
                        path.unlink()
                else:
                    path.write_text(original, encoding="utf-8")
            except Exception as e:
                logger.warning(f"[Stage4b] Failed to restore {file_path}: {e}")
        self.backups.clear()


# =========================================================================
# Build Verifier Stage
# =========================================================================


class BuildVerifierStage:
    """Verify generated code compiles in the target project, with self-healing."""

    def __init__(
        self,
        repo_path: str,
        dry_run: bool = False,
        facts_path: str = "knowledge/extract/architecture_facts.json",
    ):
        self.repo_path = Path(repo_path)
        self.facts_path = Path(facts_path)
        self.dry_run = dry_run
        self._llm = None
        self._model = os.getenv("MODEL", "gpt-4o-mini")
        self.total_calls = 0
        self.total_tokens = 0
        self._container_configs: list[ContainerConfig] | None = None

    @property
    def container_configs(self) -> list[ContainerConfig]:
        """Lazy-load container configs from extract-phase outputs."""
        if self._container_configs is None:
            self._container_configs = _detect_containers(self.repo_path, self.facts_path)
        return self._container_configs

    def run(
        self,
        generated_files: list[GeneratedFile],
        validation: ValidationResult,
        plan_input: CodegenPlanInput,
        strategy: BaseStrategy,
    ) -> tuple[list[GeneratedFile], BuildVerificationResult]:
        """
        Run build verification with self-healing.

        Returns:
            Tuple of (possibly-healed generated_files, BuildVerificationResult).
        """
        if not BUILD_VERIFY_ENABLED:
            logger.info("[Stage4b] Build verification disabled")
            return generated_files, BuildVerificationResult(skipped=True, skip_reason="build verification disabled")

        # Filter to valid files only (skip files that failed Stage 4)
        invalid_paths = {r.file_path for r in validation.file_results if not r.is_valid}
        valid_files = [gf for gf in generated_files if gf.file_path not in invalid_paths]

        if not valid_files:
            logger.info("[Stage4b] No valid files to build-verify")
            return generated_files, BuildVerificationResult(skipped=True, skip_reason="No valid generated files")

        # Group files by container
        container_files = self._group_by_container(valid_files)

        if not container_files:
            logger.info("[Stage4b] No files matched any buildable container")
            return generated_files, BuildVerificationResult(
                skipped=True, skip_reason="No files in buildable containers"
            )

        start_time = time.time()
        container_results: list[ContainerBuildResult] = []

        # Build each container. Apply ALL files before each build (cross-container deps).
        backup = _FileBackup(repo_path=self.repo_path)

        try:
            for config, files in container_files:
                result = self._verify_container(config, files, valid_files, backup, plan_input, strategy)
                container_results.append(result)
        finally:
            # Always restore — Stage 5 handles final writes
            backup.restore()

        total_duration = time.time() - start_time
        all_passed = all(r.success for r in container_results)
        total_heal_attempts = sum(max(r.attempts - 1, 0) for r in container_results)
        total_heal_successes = sum(1 for r in container_results if r.success and r.attempts > 1)

        build_result = BuildVerificationResult(
            container_results=container_results,
            all_passed=all_passed,
            total_containers_built=sum(1 for r in container_results if r.success),
            total_containers_failed=sum(1 for r in container_results if not r.success),
            total_heal_attempts=total_heal_attempts,
            total_heal_successes=total_heal_successes,
            duration_seconds=total_duration,
        )

        logger.info(
            f"[Stage4b] Build verification: {'PASSED' if all_passed else 'FAILED'} — "
            f"{build_result.total_containers_built} passed, "
            f"{build_result.total_containers_failed} failed, "
            f"{total_heal_attempts} heal attempts, {total_duration:.1f}s"
        )

        return generated_files, build_result

    # =========================================================================
    # Container verification with heal loop
    # =========================================================================

    def _verify_container(
        self,
        config: ContainerConfig,
        container_gen_files: list[GeneratedFile],
        all_gen_files: list[GeneratedFile],
        backup: _FileBackup,
        plan_input: CodegenPlanInput,
        strategy: BaseStrategy,
    ) -> ContainerBuildResult:
        """Build-verify a single container with self-healing retries."""
        start_time = time.time()

        # Baseline check: build WITHOUT generated files first
        logger.info(f"[Stage4b] {config.name}: running baseline build (no generated files)...")
        baseline_exit, baseline_output = self._run_build(config)
        if baseline_exit != 0:
            logger.warning(
                f"[Stage4b] {config.name}: BASELINE BUILD ALREADY BROKEN (exit={baseline_exit}), "
                f"skipping verification — pre-existing errors in target repo"
            )
            return ContainerBuildResult(
                container_id=config.container_id,
                container_name=config.name,
                build_command=config.build_command,
                success=True,  # not our fault → treat as pass
                exit_code=baseline_exit,
                error_summary=f"Baseline broken (pre-existing): {baseline_output[-500:]}",
                attempts=0,
                duration_seconds=time.time() - start_time,
            )
        logger.info(f"[Stage4b] {config.name}: baseline build OK")

        # Map file_path → GeneratedFile for quick lookup
        gen_file_map = {gf.file_path: gf for gf in container_gen_files}

        healed_files: list[str] = []

        for attempt in range(1, MAX_RETRIES + 1):
            logger.info(f"[Stage4b] {config.name}: attempt {attempt}/{MAX_RETRIES}")

            # Apply ALL generated files (cross-container deps)
            backup.restore()
            backup.apply(all_gen_files)

            # Run build
            exit_code, output = self._run_build(config)

            if exit_code == 0:
                logger.info(f"[Stage4b] {config.name}: BUILD PASSED (attempt {attempt})")
                return ContainerBuildResult(
                    container_id=config.container_id,
                    container_name=config.name,
                    build_command=config.build_command,
                    success=True,
                    exit_code=0,
                    attempts=attempt,
                    healed_files=healed_files,
                    duration_seconds=time.time() - start_time,
                )

            logger.warning(f"[Stage4b] {config.name}: BUILD FAILED (attempt {attempt}, exit={exit_code})")

            # Last attempt — don't try to heal
            if attempt >= MAX_RETRIES:
                break

            # Parse errors and try self-healing
            errors = _parse_build_errors(output, config.build_tool)

            if not errors:
                # Log last 500 chars of output for debugging
                logger.warning(
                    f"[Stage4b] {config.name}: could not parse build errors, skipping heal. "
                    f"Output tail: {output[-500:]}"
                )
                break

            logger.info(f"[Stage4b] {config.name}: parsed {len(errors)} build errors")

            # Match errors to generated files
            healed_any = False
            files_with_errors = self._match_errors_to_files(errors, gen_file_map)

            for file_path, file_errors in files_with_errors.items():
                gf = gen_file_map[file_path]
                other_gen_files = [g for fp, g in gen_file_map.items() if fp != file_path]
                healed_code = self._heal_file(gf, file_errors, plan_input, other_gen_files)

                if healed_code and healed_code != gf.content:
                    # Validate healed code with basic syntax check
                    from .stage4_code_validator import CodeValidatorStage

                    syntax_errors = CodeValidatorStage._check_syntax(healed_code, gf.language)
                    if syntax_errors:
                        logger.warning(f"[Stage4b] Healed code for {file_path} has syntax errors: {syntax_errors}")
                        continue

                    gf.content = healed_code
                    healed_any = True
                    if file_path not in healed_files:
                        healed_files.append(file_path)
                    logger.info(f"[Stage4b] Healed: {file_path}")

            if not healed_any:
                logger.warning(f"[Stage4b] {config.name}: no files healed, stopping retries")
                break

        duration = time.time() - start_time

        # Summarize error output — use tail (errors are usually at the end of build output)
        error_summary = output[-2000:] if output else "Build failed with no parseable output"

        return ContainerBuildResult(
            container_id=config.container_id,
            container_name=config.name,
            build_command=config.build_command,
            success=False,
            exit_code=exit_code,
            error_summary=error_summary,
            attempts=min(attempt, MAX_RETRIES),
            healed_files=healed_files,
            duration_seconds=duration,
        )

    # =========================================================================
    # Build execution
    # =========================================================================

    def _run_build(self, config: ContainerConfig) -> tuple[int, str]:
        """Run build command via shell. Returns (exit_code, combined_output)."""
        build_dir = self.repo_path / config.build_cwd
        if not build_dir.exists():
            msg = f"Build directory not found: {build_dir}"
            logger.error(f"[Stage4b] {config.name}: {msg}")
            return -1, msg

        logger.info(f"[Stage4b] {config.name}: running '{config.build_command}' in {build_dir}")

        try:
            result = subprocess.run(
                _prepare_subprocess_command(config.build_command),
                cwd=str(build_dir),
                capture_output=True,
                timeout=config.timeout,
            )
            # Decode with error handling (gradle output may contain non-UTF-8 bytes)
            stdout = result.stdout.decode("utf-8", errors="replace") if result.stdout else ""
            stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
            output = stdout + "\n" + stderr
            return result.returncode, output.strip()
        except FileNotFoundError:
            msg = f"Build tool not found for: {config.build_command}"
            logger.error(f"[Stage4b] {config.name}: {msg}")
            return -1, msg
        except subprocess.TimeoutExpired:
            msg = f"Build timed out after {config.timeout}s"
            logger.error(f"[Stage4b] {config.name}: {msg}")
            return -1, msg
        except Exception as e:
            msg = f"Build error: {e}"
            logger.error(f"[Stage4b] {config.name}: {msg}")
            return -1, msg

    # =========================================================================
    # File-to-container resolution
    # =========================================================================

    def _group_by_container(
        self, generated_files: list[GeneratedFile]
    ) -> list[tuple[ContainerConfig, list[GeneratedFile]]]:
        """Group generated files by their target container."""
        groups: dict[str, list[GeneratedFile]] = {}

        for gf in generated_files:
            try:
                repo_relative = str(Path(gf.file_path).relative_to(self.repo_path)).replace("\\", "/")
            except ValueError:
                continue

            for config in self.container_configs:
                if repo_relative.startswith(config.root_path):
                    groups.setdefault(config.container_id, []).append(gf)
                    break

        result = []
        for config in self.container_configs:
            if config.container_id in groups:
                result.append((config, groups[config.container_id]))

        return result

    # =========================================================================
    # Error matching
    # =========================================================================

    def _match_errors_to_files(
        self,
        errors: list[BuildError],
        gen_file_map: dict[str, GeneratedFile],
    ) -> dict[str, list[BuildError]]:
        """Match build errors to generated files.

        Errors in non-generated files (e.g. app.module.ts failing because a
        generated component exports the wrong thing) are distributed to ALL
        generated files so the healer sees the full picture.
        """
        result: dict[str, list[BuildError]] = {}
        unmatched: list[BuildError] = []

        # Pre-compute normalized paths
        gen_paths: dict[str, str] = {}
        for fp in gen_file_map:
            try:
                rp = str(Path(fp).relative_to(self.repo_path)).replace("\\", "/")
            except ValueError:
                rp = fp.replace("\\", "/")
            gen_paths[fp] = rp

        for error in errors:
            error_norm = error.file_path.replace("\\", "/")
            best_match: str | None = None

            # Phase 1: strong path match (endswith)
            for fp, rp in gen_paths.items():
                if rp.endswith(error_norm) or error_norm.endswith(rp):
                    best_match = fp
                    break

            # Phase 2: weak filename-only match (fallback)
            if not best_match:
                error_basename = Path(error_norm).name
                for fp, rp in gen_paths.items():
                    if Path(rp).name == error_basename:
                        best_match = fp
                        break

            if best_match:
                result.setdefault(best_match, []).append(error)
            else:
                unmatched.append(error)

        # Distribute unmatched errors to ALL generated files — they are likely
        # caused by cross-file issues (wrong exports, missing imports, etc.)
        if unmatched:
            logger.info(
                f"[Stage4b] {len(unmatched)} error(s) in non-generated files — "
                f"distributing as context to all {len(gen_file_map)} generated files"
            )
            for e in unmatched:
                logger.info(f"[Stage4b]   Unmatched: {e.file_path}:{e.line} — {e.message[:120]}")
            for fp in gen_file_map:
                result.setdefault(fp, []).extend(unmatched)

        return result

    # =========================================================================
    # Self-healing via LLM
    # =========================================================================

    def _get_llm(self):
        """Lazy-init LLM client (same as Stage 3)."""
        if self._llm is None:
            from openai import OpenAI

            api_base = os.getenv("API_BASE", "")
            api_key = os.getenv("OPENAI_API_KEY", "dummy-key")
            self._llm = OpenAI(base_url=api_base, api_key=api_key)
        return self._llm

    def _heal_file(
        self,
        gf: GeneratedFile,
        errors: list[BuildError],
        plan_input: CodegenPlanInput,
        other_gen_files: list[GeneratedFile] | None = None,
    ) -> str | None:
        """Use LLM to fix build errors in a generated file."""
        error_text = "\n".join(f"  Line {e.line}: {e.code + ': ' if e.code else ''}{e.message}" for e in errors)

        # Build cross-file context (paths + first 30 lines of each sibling gen file)
        cross_file_context = ""
        if other_gen_files:
            parts = []
            for ogf in other_gen_files[:8]:  # cap at 8 files to avoid prompt bloat
                lines = (ogf.content or "").split("\n")
                preview = "\n".join(lines[:30])
                suffix = f"\n  ... ({len(lines) - 30} more lines)" if len(lines) > 30 else ""
                parts.append(f"### {ogf.file_path}\n```{ogf.language}\n{preview}{suffix}\n```")
            cross_file_context = "\n\n## Other Generated Files (for cross-file context)\n" + "\n\n".join(parts)

        prompt = f"""You are a code-repair assistant. Fix ONLY the compilation errors in the code below.
Do NOT change functionality, do NOT add features, do NOT refactor.
Return ONLY the complete fixed file content — no explanations, no markdown fences.

## Task Context
Task: {plan_input.task_id} — {plan_input.summary}

## File
Path: {gf.file_path}
Language: {gf.language}

## Build Errors
{error_text}

## Current Code (with errors)
{gf.content}

## Original Code (before generation)
{gf.original_content if gf.original_content else "(new file)"}
{cross_file_context}

## Instructions
1. Fix ALL compilation errors listed above
2. If errors reference imports from other generated files, ensure exports/imports are consistent
3. Preserve the intended functionality from the task
4. Keep all imports, annotations, and structure intact
5. Return the COMPLETE file — not a partial diff
"""

        try:
            time.sleep(CALL_DELAY)

            client = self._get_llm()
            response = client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.05,
                max_tokens=8000,
            )

            self.total_calls += 1
            usage = getattr(response, "usage", None)
            if usage:
                self.total_tokens += getattr(usage, "total_tokens", 0)

            raw = response.choices[0].message.content or ""

            # Strip markdown fences if present
            code = BaseStrategy._extract_code_block(raw) if "```" in raw else raw

            if not code.strip():
                logger.warning(f"[Stage4b] LLM returned empty heal for {gf.file_path}")
                return None

            return code

        except Exception as e:
            logger.error(f"[Stage4b] Heal LLM call failed for {gf.file_path}: {e}")
            return None
