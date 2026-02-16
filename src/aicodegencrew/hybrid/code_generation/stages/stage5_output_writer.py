"""
Stage 5: Output Writer

Writes validated files to the target repo on a feature branch.
Generates codegen report JSON.

Duration: 2-5s (file I/O + git)

SAFETY:
- Never pushes to remote
- Never touches main/develop
- Auto-recovers if working tree is dirty (git checkout -- .)
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path

from ....shared.utils.logger import setup_logger
from ..schemas import BuildVerificationResult, CodegenReport, GeneratedFile, ValidationResult

logger = setup_logger(__name__)


class OutputWriterStage:
    """Write generated code to target repo and create codegen report."""

    def __init__(
        self,
        repo_path: str,
        report_dir: str = "knowledge/implement",
        dry_run: bool = False,
    ):
        self.repo_path = Path(repo_path)
        self.report_dir = Path(report_dir)
        self.dry_run = dry_run

    def run(
        self,
        task_id: str,
        generated_files: list[GeneratedFile],
        validation: ValidationResult,
        duration_seconds: float = 0.0,
        llm_calls: int = 0,
        total_tokens: int = 0,
        build_verification: BuildVerificationResult | None = None,
        degradation_reasons: list[str] | None = None,
    ) -> CodegenReport:
        """
        Write files to target repo and generate report.

        Args:
            task_id: Task identifier.
            generated_files: Files from Stage 3 (post-validation).
            validation: Validation result from Stage 4.
            duration_seconds: Total pipeline duration.
            llm_calls: Number of LLM calls made.
            total_tokens: Total tokens used.

        Returns:
            CodegenReport with branch name, files changed, etc.
        """
        # Filter to valid files only
        valid_files = self._filter_valid_files(generated_files, validation)
        failed_count = len(generated_files) - len(valid_files)

        # Check failure threshold
        if len(generated_files) > 0 and failed_count / len(generated_files) > 0.5:
            logger.error(
                f"[Stage5] >50% files failed ({failed_count}/{len(generated_files)}), aborting code generation"
            )
            return self._build_report(
                task_id=task_id,
                status="failed",
                generated_files=generated_files,
                validation=validation,
                duration_seconds=duration_seconds,
                llm_calls=llm_calls,
                total_tokens=total_tokens,
                build_verification=build_verification,
                degradation_reasons=degradation_reasons,
            )

        # Build gate: skip commit if build verification failed
        if build_verification and not build_verification.skipped and not build_verification.all_passed:
            logger.error(
                f"[Stage5] Build failed ({build_verification.total_containers_failed} container(s)) — aborting commit"
            )
            return self._build_report(
                task_id=task_id,
                status="failed",
                generated_files=generated_files,
                validation=validation,
                duration_seconds=duration_seconds,
                llm_calls=llm_calls,
                total_tokens=total_tokens,
                build_verification=build_verification,
                degradation_reasons=degradation_reasons,
            )

        if self.dry_run:
            logger.info("[Stage5] DRY RUN — skipping file writes and git operations")
            report = self._build_report(
                task_id=task_id,
                status="dry_run",
                generated_files=generated_files,
                validation=validation,
                duration_seconds=duration_seconds,
                llm_calls=llm_calls,
                total_tokens=total_tokens,
                dry_run=True,
                build_verification=build_verification,
                degradation_reasons=degradation_reasons,
            )
            self._write_report(report)
            return report

        # Safety checks
        if not self._is_git_repo():
            logger.error(f"[Stage5] {self.repo_path} is not a git repository")
            return self._build_report(
                task_id=task_id,
                status="failed",
                generated_files=generated_files,
                validation=validation,
                duration_seconds=duration_seconds,
                llm_calls=llm_calls,
                total_tokens=total_tokens,
                build_verification=build_verification,
                degradation_reasons=degradation_reasons,
            )

        if not self._is_clean_working_tree():
            logger.error("[Stage5] Target repo has uncommitted changes. Please commit or stash changes first.")
            return self._build_report(
                task_id=task_id,
                status="failed",
                generated_files=generated_files,
                validation=validation,
                duration_seconds=duration_seconds,
                llm_calls=llm_calls,
                total_tokens=total_tokens,
                build_verification=build_verification,
                degradation_reasons=degradation_reasons,
            )

        # Create branch
        branch_name = self._create_branch(task_id)
        if not branch_name:
            return self._build_report(
                task_id=task_id,
                status="failed",
                generated_files=generated_files,
                validation=validation,
                duration_seconds=duration_seconds,
                llm_calls=llm_calls,
                total_tokens=total_tokens,
                degradation_reasons=degradation_reasons,
            )

        # Write files
        files_changed = 0
        files_created = 0
        written_paths: list[str] = []
        for gf in valid_files:
            written = self._write_file(gf)
            if written:
                written_paths.append(gf.file_path)
                if gf.action == "create":
                    files_created += 1
                else:
                    files_changed += 1

        # Commit only the files we wrote
        commit_ok = self._git_commit(task_id, written_paths)

        # Switch back to original branch
        self._git_switch_back()

        if not commit_ok:
            logger.error("[Stage5] Git commit failed — reporting as failed")

        report = self._build_report(
            task_id=task_id,
            status="failed" if not commit_ok else ("success" if failed_count == 0 else "partial"),
            branch_name=branch_name,
            generated_files=generated_files,
            validation=validation,
            files_changed=files_changed,
            files_created=files_created,
            files_failed=failed_count,
            duration_seconds=duration_seconds,
            llm_calls=llm_calls,
            total_tokens=total_tokens,
            build_verification=build_verification,
            degradation_reasons=degradation_reasons,
        )

        # Write report JSON
        self._write_report(report)

        logger.info(
            f"[Stage5] Done: branch={branch_name}, "
            f"changed={files_changed}, created={files_created}, failed={failed_count}"
        )

        return report

    # =========================================================================
    # Cascade Mode — single integration branch for multiple tasks
    # =========================================================================

    def setup_cascade_branch(self) -> str | None:
        """
        Create a single integration branch for cascade processing.

        Called ONCE before all tasks. Returns branch name or None on failure.
        """
        if self.dry_run:
            branch = f"codegen/batch-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            logger.info(f"[Stage5] DRY RUN — cascade branch would be: {branch}")
            return branch

        if not self._is_git_repo():
            logger.error(f"[Stage5] {self.repo_path} is not a git repository")
            return None

        if not self._is_clean_working_tree():
            logger.warning("[Stage5] Dirty working tree — stashing changes")
            self._git("stash", "push", "-m", "codegen-auto-stash: dirty tree before cascade")
            if not self._is_clean_working_tree():
                logger.error("[Stage5] Stash failed — please commit or stash manually")
                return None

        # Save original branch
        self._original_branch = (self._git("rev-parse", "--abbrev-ref", "HEAD") or "").strip()

        branch = f"codegen/batch-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        result = self._git("checkout", "-b", branch)
        if result is None:
            logger.error(f"[Stage5] Failed to create cascade branch: {branch}")
            return None

        logger.info(f"[Stage5] Created cascade branch: {branch}")
        return branch

    def cascade_write_and_commit(
        self,
        task_id: str,
        generated_files: list[GeneratedFile],
        validation: ValidationResult,
        cascade_branch: str,
        cascade_position: int,
        cascade_total: int,
        prior_task_ids: list[str],
        duration_seconds: float = 0.0,
        llm_calls: int = 0,
        total_tokens: int = 0,
        build_verification: BuildVerificationResult | None = None,
        degradation_reasons: list[str] | None = None,
    ) -> CodegenReport:
        """
        Write files and commit for a single task in cascade mode.

        Unlike run(), this does NOT create a branch or switch back afterwards.
        The caller is responsible for branch setup/teardown via
        setup_cascade_branch() and teardown_cascade().
        """
        valid_files = self._filter_valid_files(generated_files, validation)
        failed_count = len(generated_files) - len(valid_files)

        # Check failure threshold
        if len(generated_files) > 0 and failed_count / len(generated_files) > 0.5:
            logger.error(
                f"[Stage5] >50% files failed ({failed_count}/{len(generated_files)}), "
                f"skipping task {task_id} in cascade"
            )
            return self._build_cascade_report(
                task_id=task_id,
                status="failed",
                cascade_branch=cascade_branch,
                cascade_position=cascade_position,
                cascade_total=cascade_total,
                prior_task_ids=prior_task_ids,
                generated_files=generated_files,
                validation=validation,
                duration_seconds=duration_seconds,
                llm_calls=llm_calls,
                total_tokens=total_tokens,
                build_verification=build_verification,
                degradation_reasons=degradation_reasons,
            )

        if self.dry_run:
            logger.info(f"[Stage5] DRY RUN — cascade task {task_id}: skipping file writes")
            report = self._build_cascade_report(
                task_id=task_id,
                status="dry_run",
                cascade_branch=cascade_branch,
                cascade_position=cascade_position,
                cascade_total=cascade_total,
                prior_task_ids=prior_task_ids,
                generated_files=generated_files,
                validation=validation,
                duration_seconds=duration_seconds,
                llm_calls=llm_calls,
                total_tokens=total_tokens,
                dry_run=True,
                build_verification=build_verification,
                degradation_reasons=degradation_reasons,
            )
            self._write_report(report)
            return report

        # Build gate: skip commit if build verification failed
        if build_verification and not build_verification.skipped and not build_verification.all_passed:
            logger.warning(f"[Stage5] Build failed for {task_id} — skipping commit")
            return self._build_cascade_report(
                task_id=task_id,
                status="failed",
                cascade_branch=cascade_branch,
                cascade_position=cascade_position,
                cascade_total=cascade_total,
                prior_task_ids=prior_task_ids,
                generated_files=generated_files,
                validation=validation,
                duration_seconds=duration_seconds,
                llm_calls=llm_calls,
                total_tokens=total_tokens,
                build_verification=build_verification,
                degradation_reasons=degradation_reasons,
            )

        # Write files (no branch creation, no clean-tree check — we're on the cascade branch)
        files_changed = 0
        files_created = 0
        written_paths: list[str] = []
        for gf in valid_files:
            written = self._write_file(gf)
            if written:
                written_paths.append(gf.file_path)
                if gf.action == "create":
                    files_created += 1
                else:
                    files_changed += 1

        # Commit with task-specific message (do NOT switch back)
        commit_ok = self._git_commit(task_id, written_paths)

        if not commit_ok:
            logger.error(f"[Stage5] Git commit failed for cascade task {task_id}")

        report = self._build_cascade_report(
            task_id=task_id,
            status="failed" if not commit_ok else ("success" if failed_count == 0 else "partial"),
            branch_name=cascade_branch,
            cascade_branch=cascade_branch,
            cascade_position=cascade_position,
            cascade_total=cascade_total,
            prior_task_ids=prior_task_ids,
            generated_files=generated_files,
            validation=validation,
            files_changed=files_changed,
            files_created=files_created,
            files_failed=failed_count,
            duration_seconds=duration_seconds,
            llm_calls=llm_calls,
            total_tokens=total_tokens,
            build_verification=build_verification,
            degradation_reasons=degradation_reasons,
        )

        self._write_report(report)

        logger.info(
            f"[Stage5] Cascade {cascade_position}/{cascade_total}: {task_id} — "
            f"changed={files_changed}, created={files_created}, failed={failed_count}"
        )
        return report

    def teardown_cascade(self) -> None:
        """Switch back to the original branch after cascade processing."""
        original = getattr(self, "_original_branch", "")
        if original and original != "HEAD":
            self._git("checkout", original)
            logger.info(f"[Stage5] Cascade complete — switched back to: {original}")
        else:
            logger.info("[Stage5] Cascade complete — no original branch to restore")

    @staticmethod
    def _build_cascade_report(
        task_id: str,
        status: str = "failed",
        branch_name: str = "",
        cascade_branch: str = "",
        cascade_position: int = 0,
        cascade_total: int = 0,
        prior_task_ids: list[str] | None = None,
        generated_files: list[GeneratedFile] | None = None,
        validation: ValidationResult | None = None,
        files_changed: int = 0,
        files_created: int = 0,
        files_failed: int = 0,
        duration_seconds: float = 0.0,
        llm_calls: int = 0,
        total_tokens: int = 0,
        dry_run: bool = False,
        build_verification: BuildVerificationResult | None = None,
        degradation_reasons: list[str] | None = None,
    ) -> CodegenReport:
        """Build a CodegenReport with cascade fields populated."""
        validation_errors = []
        if validation:
            for r in validation.file_results:
                validation_errors.extend(f"{r.file_path}: {e}" for e in r.errors)

        return CodegenReport(
            task_id=task_id,
            branch_name=branch_name,
            status=status,
            files_changed=files_changed,
            files_created=files_created,
            files_failed=files_failed,
            generated_files=generated_files or [],
            validation_errors=validation_errors,
            duration_seconds=duration_seconds,
            llm_calls=llm_calls,
            total_tokens=total_tokens,
            dry_run=dry_run,
            build_verification=build_verification,
            cascade_branch=cascade_branch,
            cascade_position=cascade_position,
            cascade_total=cascade_total,
            prior_task_ids=prior_task_ids or [],
            degradation_reasons=degradation_reasons or [],
        )

    # =========================================================================
    # Git Operations
    # =========================================================================

    def _is_git_repo(self) -> bool:
        """Check if target path is a git repository."""
        return self._git("rev-parse", "--git-dir") is not None

    def _is_clean_working_tree(self) -> bool:
        """Check if working tree has no uncommitted changes (ignores untracked files)."""
        result = self._git("status", "--porcelain", "-uno")
        return result is not None and result.strip() == ""

    def _create_branch(self, task_id: str) -> str | None:
        """Create a new branch for codegen output."""
        branch_name = f"codegen/{task_id}"

        # Check if branch already exists
        existing = self._git("branch", "--list", branch_name)
        if existing and existing.strip():
            # Append timestamp
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            branch_name = f"codegen/{task_id}-{ts}"

        # Save current branch to switch back later
        self._original_branch = (self._git("rev-parse", "--abbrev-ref", "HEAD") or "").strip()

        result = self._git("checkout", "-b", branch_name)
        if result is None:
            logger.error(f"[Stage5] Failed to create branch: {branch_name}")
            return None

        logger.info(f"[Stage5] Created branch: {branch_name}")
        return branch_name

    def _git_add_files(self, file_paths: list[str]) -> None:
        """Stage specific files (not git add -A)."""
        for fp in file_paths:
            self._git("add", "--", fp)

    def _git_commit(self, task_id: str, file_paths: list[str]) -> bool:
        """Stage specific files and commit."""
        # Stage only the files we wrote
        self._git_add_files(file_paths)

        # Check if there are staged changes
        result = self._git("diff", "--cached", "--quiet")
        if result is not None:
            logger.info("[Stage5] No changes to commit")
            return True

        file_count = len(file_paths)
        msg = (
            f"[codegen] {task_id}: Auto-generated code changes\n\n"
            f"Generated by AICodeGenCrew Phase 5\n"
            f"Plan: knowledge/plan/{task_id}_plan.json\n"
            f"Files changed: {file_count}"
        )

        result = self._git("commit", "-m", msg)
        if result is None:
            logger.error("[Stage5] Git commit failed")
            return False

        logger.info(f"[Stage5] Committed {file_count} files")
        return True

    def _git_switch_back(self) -> None:
        """Switch back to the original branch."""
        original = getattr(self, "_original_branch", "")
        if original and original != "HEAD":
            self._git("checkout", original)
            logger.info(f"[Stage5] Switched back to: {original}")

    def _git(self, *args: str) -> str | None:
        """Run a git command in the target repo. Returns stdout or None on error."""
        try:
            result = subprocess.run(
                ["git", *list(args)],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                # diff --cached --quiet returns 1 when there ARE changes (not error)
                if args[:2] == ("diff", "--cached"):
                    return None
                logger.debug(f"[Stage5] git {' '.join(args)}: {result.stderr.strip()}")
                return None
            return result.stdout
        except Exception as e:
            logger.error(f"[Stage5] git {' '.join(args)} failed: {e}")
            return None

    # =========================================================================
    # File Operations
    # =========================================================================

    def _write_file(self, gf: GeneratedFile) -> bool:
        """Write a single file to the target repo."""
        try:
            path = Path(gf.file_path).resolve()

            # Sandbox: reject paths outside repo root
            if not str(path).startswith(str(self.repo_path.resolve())):
                logger.error(f"[Stage5] BLOCKED: path outside repo root: {gf.file_path}")
                return False

            if gf.action == "delete":
                if path.exists():
                    path.unlink()
                    logger.info(f"[Stage5] Deleted: {path}")
                return True

            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)

            path.write_text(gf.content, encoding="utf-8")
            logger.info(f"[Stage5] Wrote: {path} ({len(gf.content)} chars)")
            return True

        except Exception as e:
            logger.error(f"[Stage5] Failed to write {gf.file_path}: {e}")
            return False

    def _write_report(self, report: CodegenReport) -> None:
        """Write codegen report JSON."""
        self.report_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.report_dir / f"{report.task_id}_report.json"

        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report.model_dump(), f, indent=2, ensure_ascii=False)
            logger.info(f"[Stage5] Report written: {report_path}")
        except Exception as e:
            logger.error(f"[Stage5] Failed to write report: {e}")

    # =========================================================================
    # Helpers
    # =========================================================================

    @staticmethod
    def _filter_valid_files(
        generated_files: list[GeneratedFile],
        validation: ValidationResult,
    ) -> list[GeneratedFile]:
        """Filter to only valid files based on validation results."""
        invalid_paths = {r.file_path for r in validation.file_results if not r.is_valid}
        return [gf for gf in generated_files if gf.file_path not in invalid_paths]

    @staticmethod
    def _build_report(
        task_id: str,
        status: str = "failed",
        branch_name: str = "",
        generated_files: list[GeneratedFile] = None,
        validation: ValidationResult = None,
        files_changed: int = 0,
        files_created: int = 0,
        files_failed: int = 0,
        duration_seconds: float = 0.0,
        llm_calls: int = 0,
        total_tokens: int = 0,
        dry_run: bool = False,
        build_verification: BuildVerificationResult | None = None,
        degradation_reasons: list[str] | None = None,
    ) -> CodegenReport:
        """Build a CodegenReport."""
        validation_errors = []
        if validation:
            for r in validation.file_results:
                validation_errors.extend(f"{r.file_path}: {e}" for e in r.errors)

        if degradation_reasons and status == "success":
            status = "partial"

        return CodegenReport(
            task_id=task_id,
            branch_name=branch_name,
            status=status,
            files_changed=files_changed,
            files_created=files_created,
            files_failed=files_failed,
            generated_files=generated_files or [],
            validation_errors=validation_errors,
            duration_seconds=duration_seconds,
            llm_calls=llm_calls,
            total_tokens=total_tokens,
            dry_run=dry_run,
            build_verification=build_verification,
            degradation_reasons=degradation_reasons or [],
        )
