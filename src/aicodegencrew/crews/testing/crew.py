"""Phase 6: Test Generation Crew.

Generates unit tests for source files produced by Phase 5 (Implement).

Architecture: Sequential per-file crews.
  For each generated source file:
    Agent(Test Generator) → Task(generate_test) → TestWriterTool(stage)
  Then: flush staging → write files to repo → write verify report.

Input:  knowledge/implement/{task_id}_report.json  (CodegenReport JSON)
Output: knowledge/verify/{task_id}_verify.json
        Test files written to target repo (not committed — no git branch management)

Supported languages: Java (JUnit 5 + Mockito) and TypeScript (Angular TestBed / Jasmine).
"""

import json
import os
import time
from pathlib import Path
from typing import Any

from crewai import Agent, Crew, Process, Task

from ...hybrid.code_generation.tools.code_reader_tool import EXT_TO_LANG, CodeReaderTool
from ...hybrid.code_generation.tools.test_writer_tool import TestWriterTool
from ...shared.utils.llm_factory import create_llm
from ...shared.utils.logger import setup_logger

logger = setup_logger(__name__)

# ── Model config ────────────────────────────────────────────────────────────
_CODEGEN_MODEL: str = os.getenv("CODEGEN_MODEL", os.getenv("MODEL", "gpt-oss-codegen-14b"))

# Languages we generate tests for (others skipped)
_TESTABLE_LANGS = {"java", "typescript"}


# =============================================================================
# Helpers
# =============================================================================


def _get_language(file_path: str) -> str:
    """Return language string for a file path."""
    ext = Path(file_path).suffix.lower()
    return EXT_TO_LANG.get(ext, "other")


def _is_test_file(file_path: str) -> bool:
    """Return True if the file is already a test/spec file (skip it)."""
    lower = file_path.replace("\\", "/").lower()
    stem = Path(file_path).stem.lower()
    return (
        stem.endswith("test")
        or stem.endswith("tests")
        or stem.endswith("spec")
        or ".spec." in lower
        or ".test." in lower
        or "/src/test/" in lower
        or "/__tests__/" in lower
    )


def _infer_test_path(source_path: str) -> str:
    """Infer the canonical test file path for a given source file.

    Java:       src/main/java/…/FooService.java  →  src/test/java/…/FooServiceTest.java
    TypeScript: src/app/foo/foo.component.ts     →  src/app/foo/foo.component.spec.ts
    """
    normalized = source_path.replace("\\", "/")
    p = Path(normalized)
    stem = p.stem
    ext = p.suffix.lower()

    if ext == ".java":
        if "/main/java/" in normalized:
            return normalized.replace("/main/java/", "/test/java/", 1).replace(
                f"/{stem}.java", f"/{stem}Test.java"
            )
        parent_fwd = str(p.parent).replace("\\", "/")
        return f"{parent_fwd}/{stem}Test.java"

    parent_fwd = str(p.parent).replace("\\", "/")
    if ext in (".ts", ".tsx"):
        return f"{parent_fwd}/{stem}.spec{ext}"

    return f"{parent_fwd}/{stem}.test{ext}"


def _framework_hint(source_path: str, language: str) -> str:
    """Return a concise test-framework instruction for the agent."""
    if language == "java":
        return (
            "JUnit 5 + Mockito. Use @ExtendWith(MockitoExtension.class), @Mock for "
            "dependencies, @InjectMocks for the SUT. Assert with AssertJ "
            "(org.assertj.core.api.Assertions.assertThat)."
        )
    # TypeScript
    lower = source_path.lower()
    if ".component." in lower or ".service." in lower or ".pipe." in lower:
        return (
            "Angular TestBed + Jasmine. Use TestBed.configureTestingModule(). "
            "For components: ComponentFixture + detectChanges(). "
            "For services: TestBed.inject(). Import jasmine types."
        )
    return "Jasmine or Jest. Use describe(), beforeEach(), it(), expect()."


def _make_task_description(
    source_path: str,
    source_content: str,
    test_path: str,
    language: str,
) -> str:
    truncated_content = source_content[:5000]
    if len(source_content) > 5000:
        truncated_content += "\n// ... (truncated — read full file with read_file tool)"

    framework = _framework_hint(source_path, language)
    stem = Path(source_path).stem

    return f"""TASK: Generate unit tests for the source file below.

SOURCE FILE : {source_path}
TEST FILE   : {test_path}
FRAMEWORK   : {framework}

--- SOURCE CODE (first 5000 chars) ---
{truncated_content}
--- END SOURCE CODE ---

STEPS:
1. Use read_file(file_path="{source_path}", include_siblings=True) to load the full
   source file and discover sibling files for naming/import patterns.
2. Identify all public methods / exported functions / @Component/@Injectable classes.
3. Write a COMPLETE test class/suite that covers:
   - Happy-path for each public method
   - Edge cases (null/undefined, empty collections, boundary values)
   - Error-handling / exception scenarios
4. Call write_test with:
     file_path="{test_path}"
     content=<complete test file — do NOT truncate>
     tested_component="{stem}"

IMPORTANT: You MUST call write_test to persist the result. Do not just describe tests.
"""


# =============================================================================
# TestingCrew
# =============================================================================


class TestingCrew:
    """Test Generation Crew — Phase 6.

    Reads Phase 5 implement reports, generates unit tests for every produced
    source file, writes them to the target repo, and saves verify reports.

    Usage (via orchestrator):
        crew = TestingCrew(repo_path="C:/uvz", ...)
        orchestrator.register("verify", crew)

    Direct usage:
        crew = TestingCrew(repo_path="C:/uvz")
        result = crew.run()
    """

    def __init__(
        self,
        repo_path: str,
        implement_dir: str = "knowledge/implement",
        output_dir: str = "knowledge/verify",
        dry_run: bool = False,
    ):
        self.repo_path = repo_path
        self.implement_dir = Path(implement_dir)
        self.output_dir = Path(output_dir)
        self.dry_run = dry_run

    # ── Orchestrator interface ────────────────────────────────────────────

    def kickoff(self, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        """Orchestrator-compatible kickoff — called by SDLCOrchestrator."""
        return self.run()

    # ── Main entry point ─────────────────────────────────────────────────

    def run(self) -> dict[str, Any]:
        """Scan implement reports and generate tests for each succeeded task."""
        report_files = sorted(self.implement_dir.glob("*_report.json"))

        if not report_files:
            logger.info("[TestingCrew] No implement reports found in %s — skipping", self.implement_dir)
            return {
                "status": "skipped",
                "phase": "verify",
                "message": f"No implement reports found in {self.implement_dir}",
            }

        logger.info("[TestingCrew] Found %d implement report(s)", len(report_files))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        all_results: list[dict] = []
        for rf in report_files:
            try:
                report = json.loads(rf.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error("[TestingCrew] Could not read %s: %s", rf.name, e)
                continue

            task_status = report.get("status", "")
            if task_status not in ("success", "partial"):
                logger.info(
                    "[TestingCrew] Skipping %s (implement status=%s)", rf.stem, task_status
                )
                continue

            t0 = time.monotonic()
            try:
                result = self._run_for_task(report)
            except Exception as e:
                logger.error("[TestingCrew] Unexpected error for %s: %s", rf.stem, e)
                result = {
                    "task_id": report.get("task_id", rf.stem),
                    "status": "failed",
                    "error": str(e),
                }
            result["duration_seconds"] = round(time.monotonic() - t0, 2)
            all_results.append(result)

        # Write combined summary
        self._write_summary(all_results)

        succeeded = sum(1 for r in all_results if r.get("status") in ("success", "partial"))
        return {
            "status": "success" if succeeded > 0 else ("skipped" if not all_results else "failed"),
            "phase": "verify",
            "tasks_processed": len(all_results),
            "tasks_succeeded": succeeded,
            "dry_run": self.dry_run,
        }

    # ── Per-task processing ───────────────────────────────────────────────

    def _run_for_task(self, report: dict) -> dict[str, Any]:
        """Generate tests for all testable files in one implement report."""
        task_id = report.get("task_id", "unknown")
        generated_files: list[dict] = report.get("generated_files", [])

        testable = [
            f
            for f in generated_files
            if (
                f.get("action") != "delete"
                and not f.get("error")
                and _get_language(f.get("file_path", "")) in _TESTABLE_LANGS
                and not _is_test_file(f.get("file_path", ""))
            )
        ]

        if not testable:
            logger.info("[TestingCrew] %s: no testable source files", task_id)
            result = {"task_id": task_id, "status": "skipped", "message": "No testable files"}
            self._write_task_report(task_id, result)
            return result

        logger.info("[TestingCrew] %s: generating tests for %d file(s)", task_id, len(testable))

        # Shared staging dict — same instance passed to all TestWriterTool instances
        staging: dict[str, dict] = {}
        reader = CodeReaderTool(repo_path=self.repo_path)

        files_tested: list[str] = []
        files_failed: list[str] = []

        for file_info in testable:
            source_path = file_info.get("file_path", "")
            try:
                writer = TestWriterTool(repo_path=self.repo_path, staging=staging)
                ok = self._generate_test(file_info, reader, writer)
                (files_tested if ok else files_failed).append(source_path)
            except Exception as e:
                logger.error("[TestingCrew] Failed for %s: %s", source_path, e)
                files_failed.append(source_path)

        # Flush staged test files to disk
        test_files_written: list[str] = []
        if not self.dry_run and staging:
            test_files_written = self._write_test_files(staging)
        elif self.dry_run:
            test_files_written = list(staging.keys())
            logger.info("[TestingCrew] DRY RUN — %d test files staged (not written)", len(staging))

        result = {
            "task_id": task_id,
            "status": "success" if files_tested else "failed",
            "files_tested": files_tested,
            "test_files_written": test_files_written,
            "files_failed": files_failed,
            "dry_run": self.dry_run,
        }
        self._write_task_report(task_id, result)
        return result

    # ── LLM crew per file ─────────────────────────────────────────────────

    def _generate_test(
        self,
        file_info: dict,
        reader: CodeReaderTool,
        writer: TestWriterTool,
    ) -> bool:
        """Spin up a single-agent crew to generate tests for one source file."""
        source_path = file_info.get("file_path", "")
        source_content = file_info.get("content", "")
        language = _get_language(source_path)
        test_path = _infer_test_path(source_path)

        logger.info("[TestingCrew] Generating %s → %s", Path(source_path).name, Path(test_path).name)

        agent = Agent(
            role="Test Generator",
            goal=(
                "Generate complete, runnable unit tests for the given source file "
                "and persist them using the write_test tool."
            ),
            backstory=(
                "You are a senior test engineer who specialises in JUnit 5 / Mockito "
                "(Java) and Angular TestBed / Jasmine (TypeScript). "
                "You always call write_test to save the generated test file — "
                "never just describe the tests."
            ),
            tools=[reader, writer],
            llm=create_llm(model_override=_CODEGEN_MODEL),
            verbose=True,
            max_iter=4,
            max_retry_limit=1,
        )

        description = _make_task_description(source_path, source_content, test_path, language)
        task = Task(
            description=description,
            expected_output=(
                f"Complete test file written to {test_path} via write_test tool, "
                "covering happy paths, edge cases, and error handling."
            ),
            agent=agent,
        )

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )

        staged_before = set(writer.staging.keys())
        try:
            crew.kickoff()
        except Exception as e:
            logger.error("[TestingCrew] Crew failed for %s: %s", source_path, e)
            return False

        # Verify the agent actually wrote something
        staged_after = set(writer.staging.keys())
        new_files = staged_after - staged_before
        if new_files:
            logger.info("[TestingCrew] Staged %d test file(s): %s", len(new_files), new_files)
            return True

        logger.warning("[TestingCrew] Agent did not call write_test for %s", source_path)
        return False

    # ── File I/O ──────────────────────────────────────────────────────────

    def _write_test_files(self, staging: dict[str, dict]) -> list[str]:
        """Write staged test files to the target repository."""
        written: list[str] = []
        repo = Path(self.repo_path).resolve()

        for file_path, entry in staging.items():
            try:
                raw = Path(file_path.replace("\\", "/"))
                target = (raw if raw.is_absolute() else repo / raw).resolve()
                try:
                    target.relative_to(repo)
                except ValueError:
                    logger.warning("[TestingCrew] BLOCKED: path outside repo: %s", file_path)
                    continue

                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(entry["content"], encoding="utf-8")
                written.append(file_path)
                logger.info("[TestingCrew] Wrote: %s", file_path)
            except Exception as e:
                logger.error("[TestingCrew] Failed writing %s: %s", file_path, e)

        return written

    def _write_task_report(self, task_id: str, result: dict) -> None:
        """Write per-task verify report to knowledge/verify/."""
        from ...shared.schema_version import add_schema_version

        self.output_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.output_dir / f"{task_id}_verify.json"
        try:
            report_path.write_text(
                json.dumps(add_schema_version(result, "verify"), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error("[TestingCrew] Failed writing verify report: %s", e)

    def _write_summary(self, all_results: list[dict]) -> None:
        """Write combined verify summary to knowledge/verify/summary.json."""
        from ...shared.schema_version import add_schema_version

        self.output_dir.mkdir(parents=True, exist_ok=True)
        summary_path = self.output_dir / "summary.json"
        try:
            summary_path.write_text(
                json.dumps(add_schema_version({"tasks": all_results}, "verify"), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error("[TestingCrew] Failed writing summary: %s", e)
