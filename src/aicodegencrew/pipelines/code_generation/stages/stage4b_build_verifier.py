"""
Stage 4b: Build Verifier

Compiles generated code in the target project to verify correctness.
If build fails, parses errors and uses LLM to self-heal (max retries).

Duration: 30s-5min per container (build + optional heal)

SAFETY:
- Always restores original files after build (Stage 5 does final writes)
- Works identically in dry_run and normal mode
"""

import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

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

# Environment config
BUILD_VERIFY_ENABLED = os.getenv("CODEGEN_BUILD_VERIFY", "true").lower() != "false"
MAX_RETRIES = int(os.getenv("CODEGEN_BUILD_MAX_RETRIES", "3"))
CALL_DELAY = float(os.getenv("CODEGEN_CALL_DELAY", "2"))


# =========================================================================
# Container build configuration
# =========================================================================

@dataclass
class ContainerConfig:
    """Build configuration for a target-repo container."""

    container_id: str
    name: str
    root_path: str  # relative path prefix in repo (e.g. "backend/")
    build_command: list[str]
    timeout: int = 120


# Hardcoded from containers.json + build_system.json
_CONTAINER_CONFIGS: list[ContainerConfig] = [
    ContainerConfig(
        container_id="container.backend",
        name="backend",
        root_path="backend/",
        build_command=["gradlew.bat", "compileJava", "-q"],
        timeout=120,
    ),
    ContainerConfig(
        container_id="container.frontend",
        name="frontend",
        root_path="frontend/",
        build_command=["npx", "ng", "build", "--configuration=development"],
        timeout=180,
    ),
    ContainerConfig(
        container_id="container.import_schema",
        name="import_schema",
        root_path="import-schema/",
        build_command=["gradlew.bat", "compileJava", "-q"],
        timeout=120,
    ),
]

# js_api is grouped into frontend build; e2e is test-only → skipped
_FRONTEND_ALIASES = {"container.js_api"}
_SKIPPED_CONTAINERS = {"container.e2e_xnp"}


# =========================================================================
# Error parsing
# =========================================================================

# Gradle/javac: File.java:42: error: message
_JAVAC_PATTERN = re.compile(
    r"^(?P<file>[^\s:]+\.java):(?P<line>\d+):\s*error:\s*(?P<msg>.+)$", re.MULTILINE
)

# Angular/TypeScript: file.ts:42:10 - error TS2345: message
_TSC_PATTERN1 = re.compile(
    r"^(?P<file>[^\s:]+\.ts):(?P<line>\d+):(?P<col>\d+)\s*-\s*error\s+(?P<code>TS\d+):\s*(?P<msg>.+)$",
    re.MULTILINE,
)

# TypeScript alternate: file.ts(42,10): error TS2345: message
_TSC_PATTERN2 = re.compile(
    r"^(?P<file>[^\s(]+\.ts)\((?P<line>\d+),(?P<col>\d+)\):\s*error\s+(?P<code>TS\d+):\s*(?P<msg>.+)$",
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


def _parse_build_errors(output: str, container_name: str) -> list[BuildError]:
    """Parse build output into structured errors."""
    errors: list[BuildError] = []

    if container_name in ("backend", "import_schema"):
        for m in _JAVAC_PATTERN.finditer(output):
            errors.append(
                BuildError(
                    file_path=m.group("file"),
                    line=int(m.group("line")),
                    message=m.group("msg").strip(),
                )
            )
    elif container_name == "frontend":
        for m in _TSC_PATTERN1.finditer(output):
            errors.append(
                BuildError(
                    file_path=m.group("file"),
                    line=int(m.group("line")),
                    column=int(m.group("col")),
                    code=m.group("code"),
                    message=m.group("msg").strip(),
                )
            )
        for m in _TSC_PATTERN2.finditer(output):
            errors.append(
                BuildError(
                    file_path=m.group("file"),
                    line=int(m.group("line")),
                    column=int(m.group("col")),
                    code=m.group("code"),
                    message=m.group("msg").strip(),
                )
            )

    return errors


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

    def __init__(self, repo_path: str, dry_run: bool = False):
        self.repo_path = Path(repo_path)
        self.dry_run = dry_run
        self._llm = None
        self._model = os.getenv("MODEL", "gpt-oss-120b")
        self.total_calls = 0
        self.total_tokens = 0

    def run(
        self,
        generated_files: list[GeneratedFile],
        validation: ValidationResult,
        plan_input: CodegenPlanInput,
        strategy: BaseStrategy,
    ) -> tuple[list[GeneratedFile], BuildVerificationResult]:
        """
        Run build verification with self-healing.

        Args:
            generated_files: Files from Stage 3 (post Stage 4 validation).
            validation: Validation results from Stage 4.
            plan_input: Plan input for heal prompt context.
            strategy: Strategy for post-processing healed code.

        Returns:
            Tuple of (possibly-healed generated_files, BuildVerificationResult).
        """
        if not BUILD_VERIFY_ENABLED:
            logger.info("[Stage4b] Build verification disabled (CODEGEN_BUILD_VERIFY=false)")
            return generated_files, BuildVerificationResult(
                skipped=True, skip_reason="CODEGEN_BUILD_VERIFY=false"
            )

        # Filter to valid files only (skip files that failed Stage 4)
        invalid_paths = {r.file_path for r in validation.file_results if not r.is_valid}
        valid_files = [gf for gf in generated_files if gf.file_path not in invalid_paths]

        if not valid_files:
            logger.info("[Stage4b] No valid files to build-verify")
            return generated_files, BuildVerificationResult(
                skipped=True, skip_reason="No valid generated files"
            )

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
                result = self._verify_container(
                    config, files, valid_files, backup, plan_input, strategy
                )
                container_results.append(result)
        finally:
            # Always restore — Stage 5 handles final writes
            backup.restore()

        total_duration = time.time() - start_time
        all_passed = all(r.success for r in container_results)
        total_heal_attempts = sum(max(r.attempts - 1, 0) for r in container_results)
        total_heal_successes = sum(
            1 for r in container_results if r.success and r.attempts > 1
        )

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

        # Map file_path → GeneratedFile for quick lookup
        gen_file_map = {gf.file_path: gf for gf in container_gen_files}

        healed_files: list[str] = []

        for attempt in range(1, MAX_RETRIES + 1):
            logger.info(
                f"[Stage4b] {config.name}: attempt {attempt}/{MAX_RETRIES}"
            )

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
                    build_command=" ".join(config.build_command),
                    success=True,
                    exit_code=0,
                    attempts=attempt,
                    healed_files=healed_files,
                    duration_seconds=time.time() - start_time,
                )

            logger.warning(
                f"[Stage4b] {config.name}: BUILD FAILED (attempt {attempt}, exit={exit_code})"
            )

            # Last attempt — don't try to heal
            if attempt >= MAX_RETRIES:
                break

            # Parse errors and try self-healing
            errors = _parse_build_errors(output, config.name)

            if not errors:
                logger.warning(
                    f"[Stage4b] {config.name}: could not parse build errors, skipping heal"
                )
                break

            # Match errors to generated files
            healed_any = False
            files_with_errors = self._match_errors_to_files(errors, gen_file_map)

            for file_path, file_errors in files_with_errors.items():
                gf = gen_file_map[file_path]
                healed_code = self._heal_file(gf, file_errors, plan_input)

                if healed_code and healed_code != gf.content:
                    # Validate healed code with basic syntax check
                    from .stage4_code_validator import CodeValidatorStage

                    syntax_errors = CodeValidatorStage._check_syntax(healed_code, gf.language)
                    if syntax_errors:
                        logger.warning(
                            f"[Stage4b] Healed code for {file_path} has syntax errors: {syntax_errors}"
                        )
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

        # Summarize error output (first 500 chars)
        error_summary = output[:500] if output else "Build failed with no parseable output"

        return ContainerBuildResult(
            container_id=config.container_id,
            container_name=config.name,
            build_command=" ".join(config.build_command),
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
        """Run build command for a container. Returns (exit_code, combined_output)."""
        try:
            result = subprocess.run(
                config.build_command,
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=config.timeout,
            )
            output = (result.stdout or "") + "\n" + (result.stderr or "")
            return result.returncode, output.strip()
        except FileNotFoundError:
            msg = f"Build tool not found: {config.build_command[0]}"
            logger.error(f"[Stage4b] {msg}")
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
                # file_path not under repo_path — skip
                continue

            matched_id = None
            for config in _CONTAINER_CONFIGS:
                if repo_relative.startswith(config.root_path):
                    matched_id = config.container_id
                    break

            if matched_id is None:
                # Check frontend aliases
                for alias in _FRONTEND_ALIASES:
                    # js_api files are also under frontend build
                    pass
                continue

            if matched_id in _SKIPPED_CONTAINERS:
                continue

            groups.setdefault(matched_id, []).append(gf)

        # Build result list
        result = []
        for config in _CONTAINER_CONFIGS:
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
        """Match build errors to generated files. Only returns matches."""
        result: dict[str, list[BuildError]] = {}

        for error in errors:
            # Try to match error file path to a generated file
            for file_path in gen_file_map:
                try:
                    repo_relative = str(Path(file_path).relative_to(self.repo_path)).replace("\\", "/")
                except ValueError:
                    repo_relative = file_path

                # Error paths may be relative or absolute — normalize
                error_normalized = error.file_path.replace("\\", "/")

                if (
                    repo_relative.endswith(error_normalized)
                    or error_normalized.endswith(repo_relative)
                    or Path(error_normalized).name == Path(repo_relative).name
                ):
                    result.setdefault(file_path, []).append(error)
                    break

        return result

    # =========================================================================
    # Self-healing via LLM
    # =========================================================================

    def _get_llm(self):
        """Lazy-init LLM client (same as Stage 3)."""
        if self._llm is None:
            from openai import OpenAI

            api_base = os.getenv("API_BASE", "http://sov-ai-platform.nue.local.vm:4000/v1")
            api_key = os.getenv("OPENAI_API_KEY", "dummy-key")
            self._llm = OpenAI(base_url=api_base, api_key=api_key)
        return self._llm

    def _heal_file(
        self,
        gf: GeneratedFile,
        errors: list[BuildError],
        plan_input: CodegenPlanInput,
    ) -> str | None:
        """Use LLM to fix build errors in a generated file."""
        error_text = "\n".join(
            f"  Line {e.line}: {e.code + ': ' if e.code else ''}{e.message}"
            for e in errors
        )

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
{gf.original_content if gf.original_content else '(new file)'}

## Instructions
1. Fix ALL compilation errors listed above
2. Preserve the intended functionality from the task
3. Keep all imports, annotations, and structure intact
4. Return the COMPLETE file — not a partial diff
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
