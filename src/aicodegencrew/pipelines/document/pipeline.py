"""DocumentPipeline — deterministic data collection + single LLM call per chapter.

Replaces CrewAI agent-based approach. No agents, no tool loops, no iterations.
Each chapter: collect data → build prompt → 1 LLM call → validate → write.

Usage:
    pipeline = DocumentPipeline(
        facts_path="knowledge/extract/architecture_facts.json",
        analyzed_path="knowledge/analyze/analyzed_architecture.json",
        output_dir="knowledge/document",
    )
    result = pipeline.run()
"""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ...shared import BasePipeline, LLMGenerator
from .data_collector import DataCollector
from .data_recipes import ARC42_RECIPES, C4_RECIPES, MERGE_GROUPS, ChapterRecipe
from .prompt_builder import PromptBuilder
from .validator import ChapterValidator

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2  # Max retry-with-feedback attempts per chapter


@dataclass
class ChapterResult:
    """Result of a single chapter generation."""

    chapter_id: str
    status: str  # "success", "partial", "failed", "skipped"
    duration_seconds: float = 0.0
    output_file: str = ""
    char_count: int = 0
    token_usage: dict[str, int] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Result of the entire document generation pipeline."""

    status: str  # "success", "partial", "failed"
    chapters: list[ChapterResult] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    degradation_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "total_duration": f"{self.total_duration_seconds:.1f}s",
            "chapters_completed": sum(1 for c in self.chapters if c.status == "success"),
            "chapters_partial": sum(1 for c in self.chapters if c.status == "partial"),
            "chapters_failed": sum(1 for c in self.chapters if c.status == "failed"),
            "chapters_total": len(self.chapters),
            "degradation_reasons": self.degradation_reasons,
        }


class DocumentPipeline(BasePipeline):
    """Orchestrates document generation for all chapters.

    Flow per chapter:
        1. DataCollector: gather facts, RAG results, components
        2. PromptBuilder: construct structured prompt
        3. LLMGenerator: single LLM call
        4. Validator: check output quality
        5. Write to disk + checkpoint
    """

    def __init__(
        self,
        facts_path: str | Path = "knowledge/extract/architecture_facts.json",
        analyzed_path: str | Path = "knowledge/analyze/analyzed_architecture.json",
        output_dir: str | Path = "knowledge/document",
        chroma_dir: str | None = None,
    ):
        self.output_dir = Path(output_dir)
        self.collector = DataCollector(
            facts_path=facts_path,
            analyzed_path=analyzed_path,
            chroma_dir=chroma_dir,
        )
        self.prompt_builder = PromptBuilder()
        self.validator = ChapterValidator()
        self._checkpoint_path = self.output_dir / ".checkpoint_pipeline.json"

    def run(self) -> dict:
        """Run the full document generation pipeline.

        Returns:
            Dict with status, chapter counts, duration.
        """
        start = time.time()
        logger.info("=" * 60)
        logger.info("[DocumentPipeline] Starting document generation")
        logger.info("=" * 60)

        # Validate prerequisites
        self._validate_prerequisites()

        # Load all source data
        self.collector.load()

        # Load checkpoint for resume
        completed = self._load_checkpoint()

        # Ensure output directories exist
        (self.output_dir / "arc42").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "c4").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "quality").mkdir(parents=True, exist_ok=True)

        all_results: list[ChapterResult] = []
        degradation_reasons: list[str] = []

        # Phase A: C4 Documents
        logger.info("[DocumentPipeline] Phase A: C4 Documents (%d chapters)", len(C4_RECIPES))
        for recipe in C4_RECIPES:
            if recipe.id in completed:
                logger.info("[DocumentPipeline] Skipping %s (checkpoint)", recipe.id)
                all_results.append(ChapterResult(chapter_id=recipe.id, status="skipped"))
                continue

            result = self._generate_chapter(recipe)
            all_results.append(result)

            if result.status == "success":
                self._save_checkpoint(recipe.id, completed)
            elif result.status == "partial":
                degradation_reasons.append(f"{recipe.id}: {'; '.join(result.issues)}")
                self._save_checkpoint(recipe.id, completed)
            else:
                degradation_reasons.append(f"{recipe.id}: generation failed")

        # Phase B: Arc42 Documents
        logger.info("[DocumentPipeline] Phase B: Arc42 Documents (%d chapters)", len(ARC42_RECIPES))
        for recipe in ARC42_RECIPES:
            if recipe.id in completed:
                logger.info("[DocumentPipeline] Skipping %s (checkpoint)", recipe.id)
                all_results.append(ChapterResult(chapter_id=recipe.id, status="skipped"))
                continue

            result = self._generate_chapter(recipe)
            all_results.append(result)

            if result.status == "success":
                self._save_checkpoint(recipe.id, completed)
            elif result.status == "partial":
                degradation_reasons.append(f"{recipe.id}: {'; '.join(result.issues)}")
                self._save_checkpoint(recipe.id, completed)
            else:
                degradation_reasons.append(f"{recipe.id}: generation failed")

        # Phase C: Merge split chapters
        logger.info("[DocumentPipeline] Phase C: Merging split chapters")
        self._merge_chapters()

        # Phase D: Quality report
        logger.info("[DocumentPipeline] Phase D: Quality summary")
        self._write_quality_report(all_results)

        # Cleanup checkpoint on full success
        total_duration = time.time() - start
        failed_count = sum(1 for r in all_results if r.status == "failed")
        written_count = sum(1 for r in all_results if r.status in ("success", "partial", "skipped"))

        # A "partial" chapter = content generated + written, only validator had warnings.
        # That is NOT a failure — the document exists and is useful. Only truly "failed"
        # chapters (exception, no content) should degrade the pipeline status.
        if failed_count == 0:
            status = "success"
            self._clear_checkpoint()
        elif written_count > 0:
            status = "partial"
        else:
            status = "failed"

        total_count = len(all_results)
        partial_count = sum(1 for r in all_results if r.status == "partial")
        logger.info("=" * 60)
        logger.info(
            "[DocumentPipeline] %s: %d/%d chapters written (%d with quality warnings, %s)",
            status.upper(),
            written_count,
            total_count,
            partial_count,
            f"{total_duration:.1f}s",
        )
        logger.info("=" * 60)

        return PipelineResult(
            status=status,
            chapters=all_results,
            total_duration_seconds=total_duration,
            degradation_reasons=degradation_reasons,
        ).to_dict()

    def _generate_chapter(self, recipe: ChapterRecipe) -> ChapterResult:
        """Generate a single chapter: collect → prompt → LLM → validate → write."""
        start = time.time()
        logger.info("[Chapter] %s — %s", recipe.id, recipe.title)

        try:
            # Step 1: Collect data
            data = self.collector.collect(recipe)

            # Step 2: Build prompt
            messages = self.prompt_builder.build({**data, "recipe": recipe})

            # Step 3: Generate with LLM (fences stripped via generate_text)
            generator = LLMGenerator()
            content = generator.generate_text(messages)

            # Step 4: Validate
            validation = self.validator.validate(content, recipe, data)

            # Step 4b: Retry with feedback if validation failed (max 2 attempts)
            attempts = 0
            while not validation.passed and attempts < _MAX_RETRIES:
                attempts += 1
                logger.info("[Chapter] %s — retry %d with feedback: %s", recipe.id, attempts, validation.issues)
                content = generator.retry_with_feedback_text(messages, content, validation.issues)
                validation = self.validator.validate(content, recipe, data)

            # Step 5: Write to disk
            output_path = self.output_dir / recipe.output_file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")

            duration = time.time() - start
            status = "success" if validation.passed else "partial"

            logger.info(
                "[Chapter] %s — %s (%d chars, %.1fs)",
                recipe.id,
                status,
                len(content),
                duration,
            )

            return ChapterResult(
                chapter_id=recipe.id,
                status=status,
                duration_seconds=duration,
                output_file=recipe.output_file,
                char_count=len(content),
                issues=validation.issues,
            )

        except Exception as exc:
            duration = time.time() - start
            logger.error("[Chapter] %s — FAILED: %s", recipe.id, exc, exc_info=True)
            return ChapterResult(
                chapter_id=recipe.id,
                status="failed",
                duration_seconds=duration,
                issues=[str(exc)],
            )

    def _merge_chapters(self) -> None:
        """Merge split chapter parts into final files."""
        for target_file, part_files in MERGE_GROUPS.items():
            target_path = self.output_dir / target_file
            parts = []
            for part_file in part_files:
                part_path = self.output_dir / part_file
                if part_path.exists():
                    parts.append(part_path.read_text(encoding="utf-8"))

            if parts:
                merged = "\n\n".join(parts)
                target_path.write_text(merged, encoding="utf-8")
                logger.info("[Merge] %s ← %d parts (%d chars)", target_file, len(parts), len(merged))

    def _write_quality_report(self, results: list[ChapterResult]) -> None:
        """Write a quality summary report."""
        report_path = self.output_dir / "quality" / "pipeline-report.md"
        lines = [
            "# Document Generation Quality Report",
            "",
            "| Chapter | Status | Chars | Duration | Issues |",
            "|---------|--------|-------|----------|--------|",
        ]
        for r in results:
            issues = "; ".join(r.issues) if r.issues else "-"
            lines.append(
                f"| {r.chapter_id} | {r.status} | {r.char_count} | {r.duration_seconds:.1f}s | {issues} |"
            )

        success = sum(1 for r in results if r.status == "success")
        partial = sum(1 for r in results if r.status == "partial")
        failed = sum(1 for r in results if r.status == "failed")
        lines.extend([
            "",
            f"**Summary:** {success} success, {partial} partial, {failed} failed out of {len(results)} chapters",
        ])

        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(lines), encoding="utf-8")

    def _validate_prerequisites(self) -> None:
        """Check that Phase 1 and Phase 2 outputs exist."""
        facts_path = self.collector._facts_path
        analyzed_path = self.collector._analyzed_path

        if not facts_path.exists():
            raise FileNotFoundError(
                f"Phase 1 output not found: {facts_path}. Run 'extract' phase first."
            )
        if not analyzed_path.exists():
            raise FileNotFoundError(
                f"Phase 2 output not found: {analyzed_path}. Run 'analyze' phase first."
            )

    # ── Checkpoint Management ──

    def _load_checkpoint(self) -> set[str]:
        """Load completed chapter IDs from checkpoint file."""
        if not self._checkpoint_path.exists():
            return set()
        try:
            data = json.loads(self._checkpoint_path.read_text(encoding="utf-8"))
            completed = set(data.get("completed", []))
            if completed:
                logger.info("[Checkpoint] Resuming: %d chapters already done", len(completed))
            return completed
        except Exception:
            return set()

    def _save_checkpoint(self, chapter_id: str, completed: set[str]) -> None:
        """Save chapter completion to checkpoint."""
        completed.add(chapter_id)
        data = {"completed": sorted(completed)}
        self._checkpoint_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _clear_checkpoint(self) -> None:
        """Remove checkpoint file on full success."""
        if self._checkpoint_path.exists():
            self._checkpoint_path.unlink()
            logger.info("[Checkpoint] Cleared (all chapters completed)")
