"""Output Writer: Write generated code to target repo + git + report.

Moved from stages/stage5_output_writer.py — standalone module.

Duration: 2-5s (file I/O + git)

SAFETY:
- Never pushes to remote
- Never touches main/develop
- Cascade mode can auto-stash local changes before branch creation
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path

from ...shared.utils.logger import setup_logger
from .schemas import BuildVerificationResult, CodegenReport, GeneratedFile, ValidationResult

logger = setup_logger(__name__)


class OutputWriter:
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
        self._original_branch: str = ""

    def run(
        self,
        task_id: str,
        generated_files: list[GeneratedFile],
        validation: ValidationResult | None,
        duration_seconds: float = 0.0,
        llm_calls: int = 0,
        total_tokens: int = 0,
        build_verification: BuildVerificationResult | None = None,
        degradation_reasons: list[str] | None = None,
    ) -> CodegenReport:
        """Write files to target repo and generate report."""
        valid_files = self._filter_valid_files(generated_files, validation)
        failed_count = len(generated_files) - len(valid_files)

        # Safety gate: >50% failure threshold
        if len(generated_files) > 0 and failed_count / len(generated_files) > 0.5:
            logger.error(
                "[OutputWriter] >50%% files failed (%d/%d), aborting",
                failed_count, len(generated_files),
            )
            return self._build_report(
                task_id=task_id, status="failed",
                generated_files=generated_files, validation=validation,
                duration_seconds=duration_seconds, llm_calls=llm_calls,
                total_tokens=total_tokens, build_verification=build_verification,
                degradation_reasons=degradation_reasons,
            )

        # Build gate
        if build_verification and not build_verification.skipped and not build_verification.all_passed:
            logger.error("[OutputWriter] Build failed — aborting commit")
            return self._build_report(
                task_id=task_id, status="failed",
                generated_files=generated_files, validation=validation,
                duration_seconds=duration_seconds, llm_calls=llm_calls,
                total_tokens=total_tokens, build_verification=build_verification,
                degradation_reasons=degradation_reasons,
            )

        if self.dry_run:
            logger.info("[OutputWriter] DRY RUN — skipping file writes and git")
            report = self._build_report(
                task_id=task_id, status="dry_run",
                generated_files=generated_files, validation=validation,
                duration_seconds=duration_seconds, llm_calls=llm_calls,
                total_tokens=total_tokens, dry_run=True,
                build_verification=build_verification,
                degradation_reasons=degradation_reasons,
            )
            self._write_report(report)
            return report

        if not self._is_git_repo():
            logger.error("[OutputWriter] %s is not a git repository", self.repo_path)
            return self._build_report(
                task_id=task_id, status="failed",
                generated_files=generated_files, validation=validation,
                duration_seconds=duration_seconds, llm_calls=llm_calls,
                total_tokens=total_tokens, build_verification=build_verification,
                degradation_reasons=degradation_reasons,
            )

        if not self._is_clean_working_tree():
            logger.error("[OutputWriter] Target repo has uncommitted changes")
            return self._build_report(
                task_id=task_id, status="failed",
                generated_files=generated_files, validation=validation,
                duration_seconds=duration_seconds, llm_calls=llm_calls,
                total_tokens=total_tokens, build_verification=build_verification,
                degradation_reasons=degradation_reasons,
            )

        branch_name = self._create_branch(task_id)
        if not branch_name:
            return self._build_report(
                task_id=task_id, status="failed",
                generated_files=generated_files, validation=validation,
                duration_seconds=duration_seconds, llm_calls=llm_calls,
                total_tokens=total_tokens, degradation_reasons=degradation_reasons,
            )

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

        commit_ok = self._git_commit(task_id, written_paths)
        self._git_switch_back()

        report = self._build_report(
            task_id=task_id,
            status="failed" if not commit_ok else ("success" if failed_count == 0 else "partial"),
            branch_name=branch_name,
            generated_files=generated_files, validation=validation,
            files_changed=files_changed, files_created=files_created,
            files_failed=failed_count, duration_seconds=duration_seconds,
            llm_calls=llm_calls, total_tokens=total_tokens,
            build_verification=build_verification,
            degradation_reasons=degradation_reasons,
        )
        self._write_report(report)
        return report

    # ── Cascade mode ──────────────────────────────────────────────────────

    def setup_cascade_branch(self) -> str | None:
        if self.dry_run:
            branch = f"codegen/batch-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            logger.info("[OutputWriter] DRY RUN — cascade branch: %s", branch)
            return branch

        if not self._is_git_repo():
            return None

        if not self._is_clean_working_tree():
            self._git("stash", "push", "-m", "codegen-auto-stash")
            if not self._is_clean_working_tree():
                return None

        self._original_branch = (self._git("rev-parse", "--abbrev-ref", "HEAD") or "").strip()
        branch = f"codegen/batch-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        result = self._git("checkout", "-b", branch)
        if result is None:
            return None

        logger.info("[OutputWriter] Created cascade branch: %s", branch)
        return branch

    def cascade_write_and_commit(
        self,
        task_id: str,
        generated_files: list[GeneratedFile],
        validation: ValidationResult | None,
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
        valid_files = self._filter_valid_files(generated_files, validation)
        failed_count = len(generated_files) - len(valid_files)

        cascade_kwargs = dict(
            cascade_branch=cascade_branch,
            cascade_position=cascade_position,
            cascade_total=cascade_total,
            prior_task_ids=prior_task_ids,
        )

        if len(generated_files) > 0 and failed_count / len(generated_files) > 0.5:
            return self._build_cascade_report(
                task_id=task_id, status="failed",
                generated_files=generated_files, validation=validation,
                duration_seconds=duration_seconds, llm_calls=llm_calls,
                total_tokens=total_tokens, build_verification=build_verification,
                degradation_reasons=degradation_reasons, **cascade_kwargs,
            )

        if self.dry_run:
            report = self._build_cascade_report(
                task_id=task_id, status="dry_run",
                generated_files=generated_files, validation=validation,
                duration_seconds=duration_seconds, llm_calls=llm_calls,
                total_tokens=total_tokens, dry_run=True,
                build_verification=build_verification,
                degradation_reasons=degradation_reasons, **cascade_kwargs,
            )
            self._write_report(report)
            return report

        if build_verification and not build_verification.skipped and not build_verification.all_passed:
            return self._build_cascade_report(
                task_id=task_id, status="failed",
                generated_files=generated_files, validation=validation,
                duration_seconds=duration_seconds, llm_calls=llm_calls,
                total_tokens=total_tokens, build_verification=build_verification,
                degradation_reasons=degradation_reasons, **cascade_kwargs,
            )

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

        commit_ok = self._git_commit(task_id, written_paths)
        report = self._build_cascade_report(
            task_id=task_id,
            status="failed" if not commit_ok else ("success" if failed_count == 0 else "partial"),
            branch_name=cascade_branch,
            generated_files=generated_files, validation=validation,
            files_changed=files_changed, files_created=files_created,
            files_failed=failed_count, duration_seconds=duration_seconds,
            llm_calls=llm_calls, total_tokens=total_tokens,
            build_verification=build_verification,
            degradation_reasons=degradation_reasons, **cascade_kwargs,
        )
        self._write_report(report)
        return report

    def teardown_cascade(self) -> None:
        if self._original_branch and self._original_branch != "HEAD":
            self._git("checkout", self._original_branch)

    # ── Git ───────────────────────────────────────────────────────────────

    def _is_git_repo(self) -> bool:
        return self._git("rev-parse", "--git-dir") is not None

    def _is_clean_working_tree(self) -> bool:
        result = self._git("status", "--porcelain", "-uno")
        return result is not None and result.strip() == ""

    def _create_branch(self, task_id: str) -> str | None:
        branch_name = f"codegen/{task_id}"
        existing = self._git("branch", "--list", branch_name)
        if existing and existing.strip():
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            branch_name = f"codegen/{task_id}-{ts}"

        self._original_branch = (self._git("rev-parse", "--abbrev-ref", "HEAD") or "").strip()
        result = self._git("checkout", "-b", branch_name)
        if result is None:
            return None

        return branch_name

    def _git_commit(self, task_id: str, file_paths: list[str]) -> bool:
        for fp in file_paths:
            self._git("add", "--", fp)

        result = self._git("diff", "--cached", "--quiet")
        if result is not None:
            return True

        msg = (
            f"[codegen] {task_id}: Auto-generated code changes\n\n"
            f"Generated by AICodeGenCrew Phase 5\n"
            f"Files changed: {len(file_paths)}"
        )
        result = self._git("commit", "-m", msg)
        return result is not None

    def _git_switch_back(self) -> None:
        if self._original_branch and self._original_branch != "HEAD":
            self._git("checkout", self._original_branch)

    def _git(self, *args: str) -> str | None:
        try:
            result = subprocess.run(
                ["git", *list(args)],
                cwd=str(self.repo_path),
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                if args[:2] == ("diff", "--cached"):
                    return None
                return None
            return result.stdout
        except Exception:
            return None

    # ── File I/O ──────────────────────────────────────────────────────────

    def _write_file(self, gf: GeneratedFile) -> bool:
        try:
            repo_root = self.repo_path.resolve()
            raw_path = Path(gf.file_path)
            path = (raw_path if raw_path.is_absolute() else (repo_root / raw_path)).resolve()
            try:
                path.relative_to(repo_root)
            except ValueError:
                logger.error("[OutputWriter] BLOCKED: path outside repo: %s", gf.file_path)
                return False

            if gf.action == "delete":
                if path.exists():
                    path.unlink()
                return True

            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(gf.content, encoding="utf-8")
            return True
        except Exception as e:
            logger.error("[OutputWriter] Failed to write %s: %s", gf.file_path, e)
            return False

    def _write_report(self, report: CodegenReport) -> None:
        self.report_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.report_dir / f"{report.task_id}_report.json"
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report.model_dump(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("[OutputWriter] Failed to write report: %s", e)

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _filter_valid_files(
        generated_files: list[GeneratedFile],
        validation: ValidationResult | None,
    ) -> list[GeneratedFile]:
        if validation is None:
            return generated_files
        invalid_paths = {r.file_path for r in validation.file_results if not r.is_valid}
        return [gf for gf in generated_files if gf.file_path not in invalid_paths]

    @staticmethod
    def _build_report(
        task_id: str, status: str = "failed", branch_name: str = "",
        generated_files: list[GeneratedFile] | None = None,
        validation: ValidationResult | None = None,
        files_changed: int = 0, files_created: int = 0, files_failed: int = 0,
        duration_seconds: float = 0.0, llm_calls: int = 0, total_tokens: int = 0,
        dry_run: bool = False, build_verification: BuildVerificationResult | None = None,
        degradation_reasons: list[str] | None = None,
    ) -> CodegenReport:
        validation_errors = []
        if validation:
            for r in validation.file_results:
                validation_errors.extend(f"{r.file_path}: {e}" for e in r.errors)

        if degradation_reasons and status == "success":
            status = "partial"

        return CodegenReport(
            task_id=task_id, branch_name=branch_name, status=status,
            files_changed=files_changed, files_created=files_created,
            files_failed=files_failed, generated_files=generated_files or [],
            validation_errors=validation_errors, duration_seconds=duration_seconds,
            llm_calls=llm_calls, total_tokens=total_tokens, dry_run=dry_run,
            build_verification=build_verification,
            degradation_reasons=degradation_reasons or [],
        )

    @staticmethod
    def _build_cascade_report(
        task_id: str, status: str = "failed", branch_name: str = "",
        cascade_branch: str = "", cascade_position: int = 0,
        cascade_total: int = 0, prior_task_ids: list[str] | None = None,
        generated_files: list[GeneratedFile] | None = None,
        validation: ValidationResult | None = None,
        files_changed: int = 0, files_created: int = 0, files_failed: int = 0,
        duration_seconds: float = 0.0, llm_calls: int = 0, total_tokens: int = 0,
        dry_run: bool = False, build_verification: BuildVerificationResult | None = None,
        degradation_reasons: list[str] | None = None,
    ) -> CodegenReport:
        validation_errors = []
        if validation:
            for r in validation.file_results:
                validation_errors.extend(f"{r.file_path}: {e}" for e in r.errors)

        return CodegenReport(
            task_id=task_id, branch_name=branch_name, status=status,
            files_changed=files_changed, files_created=files_created,
            files_failed=files_failed, generated_files=generated_files or [],
            validation_errors=validation_errors, duration_seconds=duration_seconds,
            llm_calls=llm_calls, total_tokens=total_tokens, dry_run=dry_run,
            build_verification=build_verification,
            cascade_branch=cascade_branch, cascade_position=cascade_position,
            cascade_total=cascade_total, prior_task_ids=prior_task_ids or [],
            degradation_reasons=degradation_reasons or [],
        )
