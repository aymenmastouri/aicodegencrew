"""AnalysisPipeline — deterministic data collection + parallel LLM calls for architecture analysis.

Replaces the CrewAI agent-based approach with:
1. Pre-collect all facts deterministically (pure Python, no agent loops)
2. 16 parallel LLM calls (one per analysis section) → 16 JSON files
3. Review LLM call — checks all sections for gaps, contradictions, weak analysis
4. Selective redo of flagged sections with review feedback
5. 1 synthesis LLM call → analyzed_architecture.json

Usage::

    pipeline = AnalysisPipeline(
        facts_dir="knowledge/extract",
        output_dir="knowledge/analyze",
    )
    result = pipeline.run()
    # result = {"status": "success|partial|failed", "phase": "analyze", "result": "<path>"}
"""

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Ensure .env is loaded even when called outside CLI subprocess
load_dotenv(override=True)

from ...shared import BasePipeline, LLMGenerator
from .data_collector import DataCollector
from .prompt_builder import SectionPromptBuilder, SynthesisPromptBuilder, SECTION_META
from .reviewer import AnalysisReviewer

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class SectionResult:
    """Result of a single analysis section LLM call."""

    section_id: str
    status: str  # "success", "failed", "skipped"
    output_file: str = ""
    duration_seconds: float = 0.0
    issues: list[str] = field(default_factory=list)


# =============================================================================
# PIPELINE
# =============================================================================


class AnalysisPipeline(BasePipeline):
    """Orchestrates the 16-section analysis pipeline.

    Flow:
        1. DataCollector.load() — read all fact files once
        2. Load checkpoint (resume support)
        3. 16 parallel LLM calls via ThreadPoolExecutor(max_workers=8)
        4. Review LLM call — cross-check sections for gaps & contradictions
        5. Selective redo of flagged sections with review feedback
        6. Synthesis LLM call
        7. Write analyzed_architecture.json
        8. Return {"status": ..., "phase": "analyze", "result": ...}
    """

    # Mapping section_id → output filename (relative to output_dir/analysis/)
    SECTION_OUTPUT_FILES: dict[str, str] = {
        "01": "analysis/01_macro_architecture.json",
        "02": "analysis/02_backend_pattern.json",
        "03": "analysis/03_frontend_pattern.json",
        "04": "analysis/04_architecture_quality.json",
        "05": "analysis/05_domain_model.json",
        "06": "analysis/06_business_capabilities.json",
        "07": "analysis/07_bounded_contexts.json",
        "08": "analysis/08_state_machines.json",
        "09": "analysis/09_workflow_engines.json",
        "10": "analysis/10_saga_patterns.json",
        "11": "analysis/11_runtime_scenarios.json",
        "12": "analysis/12_api_design.json",
        "13": "analysis/13_complexity.json",
        "14": "analysis/14_technical_debt.json",
        "15": "analysis/15_security.json",
        "16": "analysis/16_operational_readiness.json",
    }

    def __init__(
        self,
        facts_dir: str | Path = "knowledge/extract",
        output_dir: str | Path = "knowledge/analyze",
        chroma_dir: str | None = None,
    ):
        self.output_dir = Path(output_dir)
        self._analysis_dir = self.output_dir / "analysis"
        self._checkpoint_path = self.output_dir / ".checkpoint_analysis.json"

        self._collector = DataCollector(
            facts_dir=facts_dir,
            chroma_dir=chroma_dir,
        )
        self._section_prompt_builder = SectionPromptBuilder()
        self._synthesis_prompt_builder = SynthesisPromptBuilder()
        self._generator = LLMGenerator()
        self._reviewer = AnalysisReviewer(collector=self._collector, generator=self._generator)

    # =========================================================================
    # PUBLIC ENTRY POINT
    # =========================================================================

    def run(self) -> dict:
        """Run the full analysis pipeline.

        Returns:
            Dict with keys: status ("success"|"partial"|"failed"), phase ("analyze"),
            result (path to analyzed_architecture.json).
        """
        start = time.time()
        logger.info("=" * 60)
        logger.info("[AnalysisPipeline] Starting analysis generation")
        logger.info("=" * 60)

        # Validate prerequisites
        self._validate_prerequisites()

        # Load facts
        self._collector.load()

        # Ensure output directories exist
        self._analysis_dir.mkdir(parents=True, exist_ok=True)

        # Load checkpoint (resume support)
        completed = self._load_checkpoint()

        # ── Phase 1: 16 parallel section LLM calls ───────────────────────────
        section_ids = list(self.SECTION_OUTPUT_FILES.keys())
        pending = [sid for sid in section_ids if sid not in completed]

        all_results: list[SectionResult] = []

        if pending:
            logger.info(
                "[AnalysisPipeline] Running %d section(s) in parallel (max_workers=8)",
                len(pending),
            )
            with ThreadPoolExecutor(max_workers=8) as executor:
                future_map = {
                    executor.submit(self._run_section, sid): sid
                    for sid in pending
                }
                for future in as_completed(future_map):
                    sid = future_map[future]
                    try:
                        result = future.result()
                    except Exception as exc:
                        logger.error("[AnalysisPipeline] Section %s raised: %s", sid, exc)
                        result = SectionResult(
                            section_id=sid,
                            status="failed",
                            issues=[str(exc)],
                        )
                    all_results.append(result)
                    if result.status in ("success",):
                        self._save_checkpoint(sid, completed)

        # Add skipped results for already-completed sections
        for sid in section_ids:
            if sid in completed:
                all_results.append(SectionResult(section_id=sid, status="skipped"))

        # Sort results by section_id for clean logging
        all_results.sort(key=lambda r: r.section_id)

        # ── Phase 1b: Review + selective redo ─────────────────────────────────
        self._review_and_redo_sections(all_results, completed)

        # ── Phase 2: Synthesis ────────────────────────────────────────────────
        synthesis_result = self._run_synthesis()

        # Determine overall status
        failed_sections = [r for r in all_results if r.status == "failed"]
        output_path = str(self.output_dir / "analyzed_architecture.json")
        total_duration = time.time() - start

        if synthesis_result == "success" and not failed_sections:
            status = "success"
            self._clear_checkpoint()
        elif Path(output_path).exists():
            status = "partial"
        else:
            status = "failed"

        logger.info("=" * 60)
        logger.info(
            "[AnalysisPipeline] %s: %d sections, synthesis=%s (%.1fs)",
            status.upper(),
            len(all_results),
            synthesis_result,
            total_duration,
        )
        logger.info("=" * 60)

        return {
            "status": status,
            "phase": "analyze",
            "result": output_path,
        }

    # =========================================================================
    # REVIEW + SELECTIVE REDO
    # =========================================================================

    def _review_and_redo_sections(
        self, all_results: list[SectionResult], completed: set[str]
    ) -> None:
        """Review all sections and redo those flagged by the reviewer.

        Reads all section output files, sends them to the AnalysisReviewer,
        and re-generates any sections the reviewer flags with specific feedback.
        Each flagged section gets ONE redo attempt with the review feedback
        injected into the prompt.
        """
        # Collect existing section outputs
        section_outputs: dict[str, str] = {}
        for sid, rel_path in self.SECTION_OUTPUT_FILES.items():
            path = self.output_dir / rel_path
            if path.exists():
                section_outputs[sid] = path.read_text(encoding="utf-8")

        if not section_outputs:
            logger.info("[AnalysisPipeline] No sections to review (all failed)")
            return

        # Run review
        review = self._reviewer.review(section_outputs)

        # Log review results
        if review.gaps:
            logger.info("[AnalysisPipeline] Review gaps: %s", review.gaps)
        if review.contradictions:
            logger.warning("[AnalysisPipeline] Review contradictions: %s", review.contradictions)

        # Write review report for transparency
        review_report_path = self.output_dir / "analysis" / "_review_report.json"
        try:
            report = {
                "quality_score": review.quality_score,
                "sections_to_redo": review.sections_to_redo,
                "gaps": review.gaps,
                "contradictions": review.contradictions,
            }
            review_report_path.write_text(
                json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass  # Non-critical

        if not review.sections_to_redo:
            logger.info(
                "[AnalysisPipeline] Review passed (score=%d) — no sections to redo",
                review.quality_score,
            )
            return

        # Redo flagged sections with review feedback
        logger.info(
            "[AnalysisPipeline] Review (score=%d) — redoing %d section(s): %s",
            review.quality_score,
            len(review.sections_to_redo),
            sorted(review.sections_to_redo.keys()),
        )

        for sid, issues in review.sections_to_redo.items():
            if sid not in self.SECTION_OUTPUT_FILES:
                logger.warning("[AnalysisPipeline] Review flagged unknown section: %s", sid)
                continue

            result = self._redo_section_with_feedback(sid, issues)

            # Update the result in all_results
            for i, r in enumerate(all_results):
                if r.section_id == sid:
                    all_results[i] = result
                    break
            else:
                all_results.append(result)

            if result.status == "success":
                self._save_checkpoint(sid, completed)

    def _redo_section_with_feedback(
        self, section_id: str, issues: list[str]
    ) -> SectionResult:
        """Re-generate a single section with review feedback injected.

        Args:
            section_id: Section to redo (e.g. "04").
            issues: Specific issues from the reviewer.

        Returns:
            SectionResult from the redo attempt.
        """
        start = time.time()
        meta = SECTION_META[section_id]
        output_rel = self.SECTION_OUTPUT_FILES[section_id]
        output_path = self.output_dir / output_rel

        logger.info("[Section] %s — REDO with review feedback: %s", section_id, issues[:3])

        try:
            # Read previous output
            previous_output = ""
            if output_path.exists():
                previous_output = output_path.read_text(encoding="utf-8")

            # Collect data + build original prompt
            data = self._collector.collect_section_data(section_id)
            messages = self._section_prompt_builder.build({**data, "section_id": section_id})

            # Use retry_with_feedback to inject review issues
            content = self._generator.retry_with_feedback(messages, previous_output, issues)

            # Parse and repair JSON
            content = self._extract_and_repair_json(content)

            # Write output
            output_path.write_text(content, encoding="utf-8")

            duration = time.time() - start
            logger.info(
                "[Section] %s — redo success (%d chars, %.1fs)",
                section_id,
                len(content),
                duration,
            )
            return SectionResult(
                section_id=section_id,
                status="success",
                output_file=output_rel,
                duration_seconds=duration,
            )

        except Exception as exc:
            duration = time.time() - start
            logger.error("[Section] %s — redo FAILED: %s", section_id, exc, exc_info=True)
            return SectionResult(
                section_id=section_id,
                status="failed",
                duration_seconds=duration,
                issues=[f"redo failed: {exc}"],
            )

    # =========================================================================
    # SECTION EXECUTION
    # =========================================================================

    def _run_section(self, section_id: str) -> SectionResult:
        """Collect data → build prompt → LLM call → parse JSON → write file.

        Args:
            section_id: Two-digit section ID e.g. "01".

        Returns:
            SectionResult with status and timing.
        """
        start = time.time()
        meta = SECTION_META[section_id]
        output_rel = self.SECTION_OUTPUT_FILES[section_id]
        output_path = self.output_dir / output_rel

        logger.info("[Section] %s — %s", section_id, meta["title"])

        try:
            # Step 1: Collect data
            data = self._collector.collect_section_data(section_id)

            # Step 2: Build prompt
            messages = self._section_prompt_builder.build({**data, "section_id": section_id})

            # Step 3: LLM call
            content = self._llm_call(messages)

            # Step 4: Parse and repair JSON
            content = self._extract_and_repair_json(content)

            # Step 5: Write output file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")

            duration = time.time() - start
            logger.info(
                "[Section] %s — success (%d chars, %.1fs)",
                section_id,
                len(content),
                duration,
            )
            return SectionResult(
                section_id=section_id,
                status="success",
                output_file=output_rel,
                duration_seconds=duration,
            )

        except Exception as exc:
            duration = time.time() - start
            logger.error("[Section] %s — FAILED: %s", section_id, exc, exc_info=True)
            return SectionResult(
                section_id=section_id,
                status="failed",
                duration_seconds=duration,
                issues=[str(exc)],
            )

    # =========================================================================
    # SYNTHESIS
    # =========================================================================

    _SYNTHESIS_MAX_RETRIES = 2

    def _run_synthesis(self) -> str:
        """Read all 16 section files → synthesis LLM call → write analyzed_architecture.json.

        Retries up to _SYNTHESIS_MAX_RETRIES times if JSON parsing fails.

        Returns:
            "success" or "failed".
        """
        logger.info("[AnalysisPipeline] Running synthesis...")
        start = time.time()

        try:
            # Collect existing section outputs
            sections: dict[str, str] = {}
            for sid, rel_path in self.SECTION_OUTPUT_FILES.items():
                path = self.output_dir / rel_path
                if path.exists():
                    sections[path.name] = path.read_text(encoding="utf-8")
                else:
                    logger.warning("[AnalysisPipeline] Missing section file: %s", rel_path)

            if not sections:
                raise RuntimeError("No section output files found — cannot synthesise")

            # Build synthesis prompt
            messages = self._synthesis_prompt_builder.build({"sections": sections})

            # LLM call with retry on JSON parse failure
            content = None
            last_error = None
            for attempt in range(1 + self._SYNTHESIS_MAX_RETRIES):
                try:
                    if attempt == 0:
                        raw = self._llm_call(messages)
                    else:
                        logger.info(
                            "[AnalysisPipeline] Synthesis retry %d/%d (previous: %s)",
                            attempt, self._SYNTHESIS_MAX_RETRIES, last_error,
                        )
                        raw = self._generator.retry_with_feedback(
                            messages, raw, [
                                f"Your previous output was not valid JSON: {last_error}",
                                "Output ONLY valid JSON. No markdown fences. No trailing text.",
                            ],
                        )
                    content = self._extract_and_repair_json(raw)
                    break  # Success
                except ValueError as exc:
                    last_error = str(exc)
                    if attempt >= self._SYNTHESIS_MAX_RETRIES:
                        raise

            # Validate required keys — retry if missing
            missing = self._get_missing_keys(content)
            if missing and attempt < self._SYNTHESIS_MAX_RETRIES:
                logger.warning(
                    "[AnalysisPipeline] Synthesis missing keys %s — retrying",
                    sorted(missing),
                )
                raw = self._generator.retry_with_feedback(
                    messages, content, [
                        "Your output is missing these REQUIRED top-level keys: " + ", ".join(sorted(missing)),
                        "Add them with real data from the partial results. Do NOT omit any key.",
                    ],
                )
                try:
                    content = self._extract_and_repair_json(raw)
                except ValueError:
                    pass  # Keep the previous content

            # Inject schema version
            try:
                data = json.loads(content)
                from ...shared.schema_version import add_schema_version

                data = add_schema_version(data, "analyze")
                content = json.dumps(data, indent=2, ensure_ascii=False)
            except Exception as ver_exc:
                logger.warning("[AnalysisPipeline] Could not inject schema version: %s", ver_exc)

            # Write output
            output_path = self.output_dir / "analyzed_architecture.json"
            output_path.write_text(content, encoding="utf-8")

            duration = time.time() - start
            missing = self._get_missing_keys(content)
            if not missing:
                logger.info(
                    "[AnalysisPipeline] Synthesis complete (%d chars, %.1fs)",
                    len(content), duration,
                )
                return "success"
            else:
                logger.warning(
                    "[AnalysisPipeline] Synthesis partial — missing keys %s (%d chars, %.1fs)",
                    sorted(missing), len(content), duration,
                )
                return "success"  # File was written; downstream handles partial data

        except Exception as exc:
            duration = time.time() - start
            logger.error("[AnalysisPipeline] Synthesis FAILED (%.1fs): %s", duration, exc, exc_info=True)
            return "failed"

    # =========================================================================
    # LLM CALL
    # =========================================================================

    def _llm_call(self, messages: list[dict]) -> str:
        """Delegate to the shared LLMGenerator.

        All LLM configuration (model, temperature, top_p, top_k, …) is
        centralized in ``shared/llm_generator.py``.
        """
        return self._generator.generate(messages)

    # =========================================================================
    # JSON REPAIR
    # =========================================================================

    def _extract_and_repair_json(self, content: str) -> str:
        """Strip markdown fences, attempt direct parse, repair truncated JSON if needed.

        Handles:
        - Markdown code fences (```json ... ```)
        - Trailing text after JSON (explanation after the closing brace)
        - Missing commas between properties/elements
        - Truncated JSON (unclosed brackets/braces)
        - Trailing commas

        Args:
            content: Raw LLM output string.

        Returns:
            Pretty-printed valid JSON string.

        Raises:
            ValueError: When the content cannot be parsed or repaired.
        """
        text = content.strip()

        # Strip markdown code fences
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # Try direct parse
        try:
            data = json.loads(text, strict=False)
            return json.dumps(data, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            pass

        # Strip trailing text after the last closing brace/bracket
        # (LLM sometimes adds explanation after the JSON)
        last_brace = max(text.rfind("}"), text.rfind("]"))
        if last_brace > 0 and last_brace < len(text) - 1:
            trimmed = text[: last_brace + 1]
            try:
                data = json.loads(trimmed, strict=False)
                logger.info("[AnalysisPipeline] Trimmed trailing text (%d → %d chars)", len(text), len(trimmed))
                return json.dumps(data, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                pass

        # Fix missing commas: }\n{ or ]\n[ or "\n" between properties
        fixed = re.sub(r'"\s*\n(\s*)"', r'",\n\1"', text)
        fixed = re.sub(r'}\s*\n(\s*)"', r'},\n\1"', fixed)
        fixed = re.sub(r']\s*\n(\s*)"', r'],\n\1"', fixed)
        fixed = re.sub(r'}\s*\n(\s*){', r'},\n\1{', fixed)
        fixed = re.sub(r']\s*\n(\s*)\[', r'],\n\1[', fixed)
        # Fix: true/false/null/number followed by newline + "key"
        fixed = re.sub(r'(true|false|null|\d+)\s*\n(\s*)"', r'\1,\n\2"', fixed)
        if fixed != text:
            try:
                data = json.loads(fixed, strict=False)
                logger.info("[AnalysisPipeline] Fixed missing commas (%d replacements)", text.count('\n') - fixed.count('\n') + (len(fixed) - len(text)))
                return json.dumps(data, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                pass
            text = fixed  # Use the comma-fixed version for further repair

        # Attempt to repair truncated JSON by closing open structures
        repaired = text.rstrip()
        in_string = False
        escape_next = False
        stack: list[str] = []
        for ch in repaired:
            if escape_next:
                escape_next = False
                continue
            if ch == "\\" and in_string:
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch in ("{", "["):
                stack.append(ch)
            elif ch == "}" and stack and stack[-1] == "{":
                stack.pop()
            elif ch == "]" and stack and stack[-1] == "[":
                stack.pop()

        if in_string:
            repaired += '"'
        repaired = re.sub(r",\s*$", "", repaired)
        for opener in reversed(stack):
            repaired += "]" if opener == "[" else "}"

        try:
            data = json.loads(repaired, strict=False)
            logger.info("[AnalysisPipeline] Repaired truncated JSON (%d → %d chars)", len(text), len(repaired))
            return json.dumps(data, indent=2, ensure_ascii=False)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Could not parse or repair JSON: {exc}") from exc

    # =========================================================================
    # VALIDATION
    # =========================================================================

    _REQUIRED_KEYS = {
        "system",
        "macro_architecture",
        "micro_architecture",
        "architecture_quality",
        "domain",
        "workflows",
        "api",
        "quality",
        "overall_grade",
        "executive_summary",
    }

    def _get_missing_keys(self, content: str) -> set[str]:
        """Return required top-level keys missing from synthesized output."""
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return self._REQUIRED_KEYS
        if not isinstance(data, dict):
            return self._REQUIRED_KEYS
        return self._REQUIRED_KEYS - set(data.keys())

    # =========================================================================
    # PREREQUISITE CHECK
    # =========================================================================

    def _validate_prerequisites(self) -> None:
        """Ensure architecture_facts.json exists before running."""
        facts_path = self._collector._facts_dir / "architecture_facts.json"
        if not facts_path.exists():
            raise FileNotFoundError(
                f"Phase 1 output not found: {facts_path}. Run 'extract' phase first."
            )

    # =========================================================================
    # CHECKPOINT
    # =========================================================================

    def _load_checkpoint(self) -> set[str]:
        """Load completed section IDs from checkpoint file."""
        if not self._checkpoint_path.exists():
            return set()
        try:
            data = json.loads(self._checkpoint_path.read_text(encoding="utf-8"))
            completed = set(data.get("completed", []))
            if completed:
                logger.info(
                    "[AnalysisPipeline] Resuming: %d section(s) already done: %s",
                    len(completed),
                    sorted(completed),
                )
            return completed
        except Exception:
            return set()

    def _save_checkpoint(self, section_id: str, completed: set[str]) -> None:
        """Persist a completed section ID to the checkpoint file (thread-safe via atomic write)."""
        completed.add(section_id)
        data = {"completed": sorted(completed)}
        # Write to temp file then rename for atomicity on most platforms
        tmp = self._checkpoint_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self._checkpoint_path)

    def _clear_checkpoint(self) -> None:
        """Remove checkpoint file on full success."""
        if self._checkpoint_path.exists():
            self._checkpoint_path.unlink()
            logger.info("[AnalysisPipeline] Checkpoint cleared (all sections completed)")
