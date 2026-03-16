"""TriagePipeline — deterministic analysis + LLM synthesis.

Architecture: deterministic scan → LLM synthesis (Pipeline + LLM pattern).

  1. Deterministic phase (no LLM, <5s):
       - Classify issue (bug | feature | refactor | investigation)
       - Find entry-point components (multi-signal matching)
       - Calculate blast radius (BFS on relation graph)
       - Find similar code/issues (Qdrant vector search)
       - Check test coverage for affected components
       - Assess risk (security, error handling, quality)

  2. LLM synthesis phase:
       - Single LLMGenerator call (no agent overhead)
       - Produces dual output: customer summary + developer brief

Input:  issue title/description OR task file
        knowledge/discover/  (symbols, evidence)
        knowledge/extract/   (architecture_facts)
        knowledge/analyze/   (analyzed_architecture, optional)
        knowledge/document/  (arc42, c4, optional)

Output: knowledge/triage/{issue_id}_findings.json
        knowledge/triage/{issue_id}_customer.md
        knowledge/triage/{issue_id}_developer.md
        knowledge/triage/{issue_id}_triage.json
        knowledge/triage/summary.json
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from ...shared import BasePipeline, LLMGenerator
from ...shared.paths import DISCOVER_DIR, get_discover_dir
from ...shared.schema_version import add_schema_version
from ...shared.utils.env_flags import get_bool_env
from ...shared.utils.logger import setup_logger
from .blast_radius import calculate_blast_radius
from .classifier import classify_issue
from .context_builder import KnowledgeLoader
from .duplicate_detector import find_duplicates
from .entry_point_finder import find_entry_points
from .risk_assessor import assess_risk
from .schemas import TriageRequest
from .test_coverage import check_test_coverage

logger = setup_logger(__name__)


class TriagePipeline(BasePipeline):
    """TriagePipeline — deterministic analysis + LLM synthesis.

    Usage (via orchestrator)::

        crew = TriagePipeline()
        orchestrator.register("triage", crew)

    Direct usage::

        crew = TriagePipeline(knowledge_dir="knowledge")
        result = crew.run(TriageRequest(issue_id="BUG-123", title="...", description="..."))

    Quick (deterministic only)::

        result = crew.triage_quick(title="...", description="...")
    """

    def __init__(
        self,
        knowledge_dir: str = "knowledge",
        chroma_dir: str | None = None,
    ):
        self.knowledge_dir = Path(knowledge_dir)
        self.facts_dir = str(self.knowledge_dir / "extract")
        self.output_dir = self.knowledge_dir / "triage"
        self.chroma_dir = chroma_dir or get_discover_dir()
        self._loader = KnowledgeLoader(knowledge_dir)
        self._generator = LLMGenerator()

    # ── Orchestrator interface ──────────────────────────────────────────

    def kickoff(self, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        """Orchestrator-compatible kickoff — called by SDLCOrchestrator.

        Expects ``inputs`` to contain a TriageRequest-compatible dict or
        falls back to a no-op summary if no request is provided.
        """
        if not inputs:
            return {"status": "skipped", "phase": "triage", "message": "No triage request provided"}

        # Accept either a TriageRequest or a raw dict
        req_data = inputs.get("triage_request", inputs)
        if isinstance(req_data, TriageRequest):
            request = req_data
        else:
            request = TriageRequest(**req_data)

        return self.run(request)

    # ── Main entry point ────────────────────────────────────────────────

    def run(self, request: TriageRequest) -> dict[str, Any]:
        """Run full triage: deterministic analysis + LLM synthesis."""
        t0 = time.monotonic()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        issue_id = request.issue_id

        # ── Load all available context ──────────────────────────────────
        knowledge = self._loader.load_available_context()

        # ── Parse task file if provided ─────────────────────────────────
        task_info = self._parse_task_file(request)
        title = task_info.get("title") or request.title
        description = task_info.get("description") or request.description

        # ── Load supplementary context ──────────────────────────────────
        supplementary = self._load_supplementary(request.supplementary_files)

        # ── Phase 1: Deterministic analysis ─────────────────────────────
        log_context = supplementary.get("logs", "")

        classification = classify_issue(title, description, log_context or None)

        entry_points = find_entry_points(
            title, description, knowledge,
            classification_type=classification.get("type", "bug"),
        )

        blast_radius = calculate_blast_radius(entry_points, knowledge)

        duplicates = find_duplicates(title, description, self.chroma_dir)

        affected = blast_radius.get("affected", [])
        test_cov = check_test_coverage(affected, knowledge)

        risk = assess_risk(affected, knowledge)

        findings = {
            "classification": classification,
            "entry_points": entry_points,
            "blast_radius": blast_radius,
            "duplicates": duplicates,
            "test_coverage": test_cov,
            "risk_assessment": risk,
        }
        self._write_json(findings, f"{issue_id}_findings.json")

        # ── Determine if this is a bug ──────────────────────────────────
        task_type = task_info.get("task_type", "")
        is_bug = task_type in ("bugfix", "bug") or classification.get("type") == "bug"

        # ── Assemble analysis inputs ─────────────────────────────────────
        analysis_inputs = self._assemble_analysis_inputs(entry_points, blast_radius)

        # ── Phase 2: LLM synthesis ──────────────────────────────────────
        llm_result = None
        llm_status = "failed"  # "success" | "partial" | "failed"
        llm_error: str | None = None

        # Pre-check: is LLM server reachable?
        from ...shared.utils.llm_factory import check_llm_connectivity
        reachable, health_msg = check_llm_connectivity(timeout=10)
        if not reachable:
            llm_error = f"LLM server unreachable: {health_msg}"
            logger.error("[TriagePipeline] %s — skipping LLM synthesis entirely", llm_error)
        else:
            logger.info("[TriagePipeline] LLM health check: %s", health_msg)
            try:
                llm_result = self._run_llm_synthesis(
                    title, description, task_info, findings, supplementary,
                    is_bug=is_bug,
                    analysis_inputs=analysis_inputs,
                )
                if llm_result is not None:
                    llm_status = "success"
                else:
                    llm_error = "LLM returned no parseable JSON output"
                    logger.error("[TriagePipeline] LLM synthesis returned None — no JSON in output")
            except Exception as e:
                llm_error = str(e)
                logger.error(
                    "[TriagePipeline] LLM synthesis FAILED (is LLM server reachable?): %s", e,
                )

        # ── Quality gate ────────────────────────────────────────────────
        quality_threshold = int(os.environ.get("TRIAGE_QUALITY_THRESHOLD", "50"))
        if llm_result:
            quality = self._score_triage_quality(llm_result)
            if quality["score"] < quality_threshold:
                logger.warning(
                    "[TriagePipeline] Quality score %d < threshold %d — partial: %s",
                    quality["score"], quality_threshold, quality["warnings"],
                )
                llm_status = "partial"  # downgrade: LLM ran but output is poor
            elif quality["warnings"]:
                logger.info("[TriagePipeline] Quality score %d — warnings: %s", quality["score"], quality["warnings"])

        # ── Write outputs ───────────────────────────────────────────────
        customer = {}
        developer = {}
        if llm_result:
            customer = llm_result.get("customer_summary", {})
            developer = llm_result.get("developer_context", {})

        # ── Classification override: LLM has final say ─────────────────
        if customer:
            llm_is_bug = customer.get("is_bug", None)
            det_type = classification.get("type", "")
            if llm_is_bug is False and det_type == "bug":
                # Pick the next-best type from deterministic scores
                det_scores = classification.get("scores", {})
                alt_type = "feature"  # fallback
                if det_scores:
                    non_bug = {k: v for k, v in det_scores.items() if k != "bug"}
                    if non_bug:
                        alt_type = max(non_bug, key=non_bug.get)  # type: ignore[arg-type]
                        if non_bug[alt_type] == 0:
                            alt_type = "feature"
                logger.info(
                    "[TriagePipeline] LLM overrides classification: %s → %s "
                    "(is_bug=False, confidence=%.2f)",
                    det_type, alt_type, developer.get("classification_confidence", -1),
                )
                classification = {
                    **classification,
                    "type": alt_type,
                    "overridden_from": det_type,
                    "override_reason": "LLM assessment: not a bug",
                }
                findings["classification"] = classification

        if customer:
            self._write_markdown(
                self._format_customer_md(customer, issue_id),
                f"{issue_id}_customer.md",
            )
        if developer:
            self._write_markdown(
                self._format_developer_md(developer, issue_id),
                f"{issue_id}_developer.md",
            )

        triage_result = {
            "issue_id": issue_id,
            "classification": classification,
            "customer_summary": customer,
            "developer_context": developer,
            "findings": findings,
        }
        self._write_json(triage_result, f"{issue_id}_triage.json")

        duration = round(time.monotonic() - t0, 2)

        # Build triage_context for downstream phases (Plan reads this)
        triage_context: dict[str, Any] = {
            "classification_type": classification.get("type", "unknown"),
            "classification_confidence": classification.get("confidence", 0),
            "llm_status": llm_status,  # "success" | "partial" | "failed"
        }
        if llm_status != "failed":
            # Only populate LLM-derived fields when LLM actually produced output
            triage_context.update({
                "big_picture": developer.get("big_picture", ""),
                "scope_boundary": developer.get("scope_boundary", ""),
                "classification_assessment": developer.get("classification_assessment", ""),
                "affected_components": developer.get("affected_components", []),
                "context_boundaries": [
                    {
                        "category": cb.get("category", ""),
                        "boundary": cb.get("boundary", ""),
                        "severity": cb.get("severity", "info"),
                        "source_facts": cb.get("source_facts", []),
                    }
                    for cb in developer.get("context_boundaries", [])
                ] if developer else [],
                "architecture_notes": developer.get("architecture_notes", ""),
                "anticipated_questions": developer.get("anticipated_questions", []),
            })
        else:
            # LLM failed — build fallback triage_context from deterministic results
            # so Plan phase can still work with partial information
            triage_context["llm_error"] = llm_error or "LLM synthesis failed"
            triage_context.update(
                self._build_deterministic_fallback(
                    classification, entry_points, blast_radius, risk,
                )
            )

        summary = {
            "status": llm_status,  # "success" | "partial" | "failed"
            "phase": "triage",
            "issue_id": issue_id,
            "classification": classification.get("type", "unknown"),
            "risk_level": risk.get("risk_level", "unknown"),
            "entry_points_found": len(entry_points),
            "blast_radius_count": blast_radius.get("component_count", 0),
            "llm_synthesis": llm_status == "success",
            "llm_status": llm_status,
            "duration_seconds": duration,
            "triage_context": triage_context,
        }
        if llm_error:
            summary["llm_error"] = llm_error
        self._write_json(summary, "summary.json")

        if llm_status == "failed":
            logger.error(
                "[TriagePipeline] INCOMPLETE — LLM synthesis FAILED for %s. "
                "Deterministic analysis saved but developer_context is EMPTY. "
                "Check LLM server connectivity. Error: %s",
                issue_id, llm_error,
            )
        elif llm_status == "partial":
            logger.warning(
                "[TriagePipeline] Done (partial) — LLM output below quality threshold for %s",
                issue_id,
            )
        else:
            logger.info(
                "[TriagePipeline] Done — type=%s, risk=%s, entry_points=%d, duration=%.1fs",
                classification.get("type"), risk.get("risk_level"),
                len(entry_points), duration,
            )
        return summary

    # ── Quick (deterministic only) ──────────────────────────────────────

    def triage_quick(self, title: str, description: str) -> dict[str, Any]:
        """Deterministic-only triage — no LLM, <2s."""
        t0 = time.monotonic()
        knowledge = self._loader.load_available_context()

        classification = classify_issue(title, description)
        entry_points = find_entry_points(
            title, description, knowledge,
            classification_type=classification.get("type", "bug"),
        )
        blast_radius = calculate_blast_radius(entry_points, knowledge)
        affected = blast_radius.get("affected", [])
        test_cov = check_test_coverage(affected, knowledge)
        risk = assess_risk(affected, knowledge)

        duration = round(time.monotonic() - t0, 2)
        return {
            "status": "success",
            "mode": "quick",
            "classification": classification,
            "entry_points": entry_points,
            "blast_radius": blast_radius,
            "test_coverage": test_cov,
            "risk_assessment": risk,
            "duration_seconds": duration,
        }

    # ── Task file parsing ───────────────────────────────────────────────

    def _parse_task_file(self, request: TriageRequest) -> dict[str, str]:
        """Parse task file if provided, returning title + description."""
        if not request.task_file:
            return {"title": request.title, "description": request.description}

        try:
            from ...pipelines.plan.stages.stage1_input_parser import InputParserStage

            parser = InputParserStage()
            task_input = parser.run(request.task_file)
            return {
                "title": task_input.summary or request.title,
                "description": task_input.description or request.description,
                "task_id": task_input.task_id,
                "task_type": task_input.task_type,
                "priority": task_input.priority,
                "labels": ", ".join(task_input.labels),
                "acceptance_criteria": "\n".join(task_input.acceptance_criteria),
            }
        except Exception as e:
            logger.warning("[TriagePipeline] Task file parse failed: %s", e)
            return {"title": request.title, "description": request.description}

    # ── Supplementary context ───────────────────────────────────────────

    def _load_supplementary(self, files: dict[str, list[str]]) -> dict[str, str]:
        """Load supplementary files (requirements, logs) as text snippets.

        Supports plain text files and PDFs (via pymupdf text extraction).
        """
        context: dict[str, str] = {}
        max_chars = 3000
        for category, paths in files.items():
            parts: list[str] = []
            for fp in paths:
                p = Path(fp)
                if not p.exists():
                    continue
                try:
                    if p.suffix.lower() == ".pdf":
                        text = self._extract_pdf_text(p, max_chars)
                    else:
                        text = p.read_text(encoding="utf-8", errors="replace")[:max_chars]
                    if text.strip():
                        parts.append(f"--- {p.name} ---\n{text}")
                except Exception as e:
                    logger.warning("[TriagePipeline] Failed to load supplementary %s: %s", p.name, e)
            if parts:
                context[category] = "\n\n".join(parts)[:max_chars]
        return context

    @staticmethod
    def _extract_pdf_text(path: Path, max_chars: int = 3000) -> str:
        """Extract text from a PDF file using pymupdf."""
        try:
            import pymupdf
        except ImportError:
            logger.warning("[TriagePipeline] pymupdf not installed — cannot extract PDF text")
            return ""

        try:
            doc = pymupdf.open(str(path))
            pages: list[str] = []
            total = 0
            for page in doc:
                text = page.get_text() or ""
                pages.append(text)
                total += len(text)
                if total >= max_chars:
                    break
            doc.close()
            result = "\n\n".join(pages)
            return result[:max_chars]
        except Exception as e:
            logger.warning("[TriagePipeline] PDF extraction failed for %s: %s", path.name, e)
            return ""

    # ── Analysis inputs assembly ─────────────────────────────────────────

    def _assemble_analysis_inputs(
        self, entry_points: list[dict], blast_radius: dict,
    ) -> str:
        """Assemble analysis inputs from knowledge/extract/ for prompt injection.

        Loads dimension files, filters to affected area, and formats with
        analysis instructions so the LLM produces insights, not data copies.
        """
        extract_dir = self.knowledge_dir / "extract"
        if not extract_dir.exists():
            return ""

        # Collect affected component/container names for filtering
        affected_names: set[str] = set()
        affected_files: set[str] = set()
        for ep in entry_points:
            if isinstance(ep, dict):
                affected_names.add(ep.get("component", "").lower())
                if ep.get("file_path"):
                    affected_files.add(ep["file_path"].lower())
            elif hasattr(ep, "component"):
                affected_names.add(ep.component.lower())
        for item in blast_radius.get("affected", []):
            name = item.get("component", "") if isinstance(item, dict) else ""
            affected_names.add(name.lower())
        affected_containers: set[str] = {
            c.lower() for c in blast_radius.get("containers_affected", [])
        }
        affected_names.discard("")

        sections: list[str] = []
        max_total = 5000

        # 1. Technology Stack
        self._add_analysis_section(
            sections, extract_dir / "tech_versions.json",
            "Technology Stack",
            "(What CONSTRAINTS do these versions impose on this issue? Do NOT just list them.)",
            max_items=15,
            formatter=lambda items: "\n".join(
                f"  - {t['technology']} {t.get('version', '?')} ({t.get('category', '')})"
                f" — source: tech_versions.json"
                for t in items
            ),
        )

        # 2. Components (filtered to affected)
        self._add_analysis_section(
            sections, extract_dir / "components.json",
            "Components (affected area)",
            "(What PATTERNS and LAYERS are these components in? What constraints arise?)",
            key="components",
            filter_fn=lambda c: (
                c.get("name", "").lower() in affected_names
                or c.get("container", "").lower() in affected_containers
            ),
            max_items=20,
            formatter=lambda items: "\n".join(
                f"  - {c['name']} [{c.get('stereotype', '')}] "
                f"layer={c.get('layer', '?')}, container={c.get('container', '?')}"
                f" — source: components.json"
                for c in items
            ),
        )

        # 3. Relations (filtered to affected — source OR target)
        self._add_analysis_section(
            sections, extract_dir / "relations.json",
            "Relations (affected area)",
            "(What DEPENDENCY CHAINS exist? What could BREAK if these components change?)",
            key="relations",
            filter_fn=lambda r: any(
                name in r.get("from", "").lower() or name in r.get("to", "").lower()
                for name in affected_names
            ) if affected_names else False,
            max_items=15,
            formatter=lambda items: "\n".join(
                f"  - {r['from'].split('.')[-1]} -> {r['to'].split('.')[-1]} ({r.get('type', '?')})"
                f" — source: relations.json"
                for r in items
            ),
        )

        # 4. Interfaces (filtered to affected components)
        self._add_analysis_section(
            sections, extract_dir / "interfaces.json",
            "Interfaces (affected area)",
            "(What API CONTRACTS exist? What integration boundaries must be respected?)",
            key="interfaces",
            filter_fn=lambda i: (
                i.get("component", "").lower() in affected_names
                or i.get("source", "").lower() in affected_names
            ),
            max_items=10,
            formatter=lambda items: "\n".join(
                f"  - {i.get('name', '?')} ({i.get('type', '?')}): "
                f"{i.get('description', '')[:100]}"
                f" — source: interfaces.json"
                for i in items
            ),
        )

        # 5. Dependencies (filtered to affected containers)
        self._add_analysis_section(
            sections, extract_dir / "dependencies.json",
            "Dependencies (runtime)",
            "(What LIBRARY RISKS exist? Version conflicts, deprecations?)",
            key="dependencies",
            filter_fn=lambda d: d.get("scope") == "runtime",
            max_items=10,
            formatter=lambda items: "\n".join(
                f"  - {d['name']} {d.get('version', '?')} ({d.get('type', '')})"
                f" — source: dependencies.json"
                for d in items
            ),
        )

        # 6. Security details (filtered by class name proximity)
        self._add_analysis_section(
            sections, extract_dir / "security_details.json",
            "Security Configuration",
            "(What SECURITY MECHANISMS are in play? What must NOT be bypassed?)",
            filter_fn=lambda s: any(
                name in s.get("class_name", "").lower()
                or name in s.get("file_path", "").lower()
                for name in affected_names
            ) if affected_names else False,
            max_items=8,
            formatter=lambda items: "\n".join(
                f"  - {s.get('name', '?')} ({s.get('security_type', '?')})"
                f" — source: security_details.json"
                for s in items
            ),
        )

        # 7. Workflows (filtered by file proximity)
        self._add_analysis_section(
            sections, extract_dir / "workflows.json",
            "Workflows",
            "(What BUSINESS FLOWS could be affected? State transitions to preserve?)",
            key="workflows",
            filter_fn=lambda w: any(
                name in w.get("file_path", "").lower()
                or name in w.get("name", "").lower()
                for name in affected_names
            ) if affected_names else False,
            max_items=5,
            formatter=lambda items: "\n".join(
                f"  - {w.get('name', '?')} ({w.get('workflow_type', '?')}): "
                f"states={w.get('states', [])}"
                f" — source: workflows.json"
                for w in items
            ),
        )

        # 8. Error handling
        self._add_analysis_section(
            sections, extract_dir / "error_handling.json",
            "Error Handling",
            "(What error handling patterns MUST be followed?)",
            key="strategies",
            max_items=5,
            formatter=lambda items: "\n".join(
                f"  - {e.get('pattern', e.get('name', '?'))}: "
                f"{e.get('description', '')[:100]}"
                f" — source: error_handling.json"
                for e in items
            ),
        )

        # 9. Architecture overview (always, compact)
        analyze_dir = self.knowledge_dir / "analyze"
        arch_file = analyze_dir / "analyzed_architecture.json"
        if arch_file.exists():
            try:
                arch = json.loads(arch_file.read_text(encoding="utf-8"))
                stats = arch.get("system", {}).get("statistics", {})
                if stats:
                    by_layer = stats.get("by_layer", {})
                    layers_str = ", ".join(f"{k}={v}" for k, v in by_layer.items() if v)
                    sections.append(
                        f"=== ANALYSIS INPUT: Architecture Overview ===\n"
                        f"(What is the OVERALL SHAPE of the system?)\n"
                        f"  - {stats.get('containers', 0)} containers, "
                        f"{stats.get('components', 0)} components, "
                        f"{stats.get('interfaces', 0)} interfaces\n"
                        f"  - Layers: {layers_str}\n"
                        f"  - Tests: {stats.get('tests', 0)}, "
                        f"Security configs: {stats.get('security_details', 0)}"
                        f" — source: analyzed_architecture.json"
                    )
            except Exception:
                pass

        result = "\n\n".join(sections)
        if len(result) > max_total:
            result = result[:max_total] + "\n  ... (truncated)"
        return result

    @staticmethod
    def _add_analysis_section(
        sections: list[str],
        file_path: Path,
        title: str,
        analysis_hint: str,
        key: str | None = None,
        filter_fn=None,
        max_items: int = 10,
        formatter=None,
    ) -> None:
        """Load a dimension file and append a formatted analysis section."""
        if not file_path.exists():
            return
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            return

        items = data if isinstance(data, list) else data.get(key or title.lower(), [])
        if not isinstance(items, list):
            return
        if filter_fn:
            items = [i for i in items if filter_fn(i)]
        items = items[:max_items]
        if not items:
            return

        try:
            body = formatter(items) if formatter else json.dumps(items, indent=2, ensure_ascii=False, default=str)
        except Exception:
            return
        sections.append(f"=== ANALYSIS INPUT: {title} ===\n{analysis_hint}\n{body}")

    # ── LLM synthesis ───────────────────────────────────────────────────

    def _run_llm_synthesis(
        self,
        title: str,
        description: str,
        task_info: dict,
        findings: dict,
        supplementary: dict[str, str],
        *,
        is_bug: bool = False,
        analysis_inputs: str = "",
    ) -> dict | None:
        """Run direct litellm call for triage synthesis.

        Replaces the 2-agent mini-crew with a single LLM completion call.
        System prompt uses the analyst agent backstory; user prompt uses the
        triage task description (with all deterministic findings injected).
        """
        task_context = f"Title: {title}\nDescription: {description}"
        if task_info.get("priority"):
            task_context += f"\nPriority: {task_info['priority']}"
        if task_info.get("labels"):
            task_context += f"\nLabels: {task_info['labels']}"
        if task_info.get("acceptance_criteria"):
            task_context += f"\nAcceptance Criteria:\n{task_info['acceptance_criteria']}"

        findings_json = json.dumps(findings, indent=2, ensure_ascii=False, default=str)
        supplementary_text = "\n\n".join(f"[{k}]\n{v}" for k, v in supplementary.items())

        # System message: analyst agent backstory (GOLDEN RULES + orientation)
        system_message = (
            "You are a senior software architect / tech lead who helps developers "
            "understand the WHY before they dive into code. Your goal: after reading "
            "your output, a developer should feel oriented — not lost.\n\n"
            "GOLDEN RULES:\n"
            "1. NORTH STAR (big_picture): What is this project? Who uses it? "
            "What problem does THIS task solve? Why NOW? What if we don't do it?\n"
            "2. ARCHITECTURE WALKTHROUGH (architecture_notes): Show WHERE the work fits. "
            "Container → Layer → Component → Neighbors. Like drawing on a whiteboard.\n"
            "3. WHY, NOT JUST WHAT: Customer summary explains WHY this is needed, "
            "not just what needs to happen.\n"
            "4. ANTICIPATED QUESTIONS: Think like a developer seeing this for the "
            "first time. Answer their obvious questions BEFORE they ask.\n"
            "5. Context Boundaries are ANALYSIS, not data. For every fact you cite, "
            "explain what it MEANS for this specific issue.\n"
            "6. For bugs: critically assess if the classification is correct.\n"
            "7. NEVER propose solutions or action steps — that is the Plan phase's job.\n"
            "8. Use the pre-loaded analysis inputs to verify architectural context."
        )

        # Build bug-vs-feature specific steps text
        if is_bug:
            steps = """\
STEPS:
1. Review the classification, deterministic findings, AND the SUPPLEMENTARY CONTEXT (requirements, references, logs) carefully.
2. VALIDATE: Is this really a bug? Build a structured argument:
   a) List evidence FOR it being a bug (error logs, stack traces, spec violations, reference documents).
   b) List evidence AGAINST (user error, missing feature, config issue, working as designed).
   c) Check supplementary references (PDFs, requirements docs) — do they confirm or contradict the bug claim?
   d) Rate your confidence and explain your reasoning.
3. Review the ANALYSIS INPUTS below — they contain raw facts from the codebase.
4. For EACH relevant fact: What does it MEAN for this issue? What constraint, risk, or boundary does it create?
5. Provide the BIG PICTURE (North Star): What is this project? Who is the customer? What problem does this solve? Why is this task needed NOW?
6. ARCHITECTURE WALKTHROUGH: Where does this piece fit? Which container, which layer, what neighbors?
7. Define the SCOPE: What parts of the system are involved (IN)? What is NOT involved (OUT)?
8. ANTICIPATED QUESTIONS: What would a developer ask before starting? Answer 3-5 obvious questions.
9. Produce JSON output."""
        else:
            steps = """\
STEPS:
1. Review the issue context, deterministic findings, AND the SUPPLEMENTARY CONTEXT (requirements, references, logs).
2. Review the ANALYSIS INPUTS below — they contain raw facts from the codebase.
3. For EACH relevant fact: What does it MEAN for this issue? What constraint, risk, or boundary does it create?
4. Provide the BIG PICTURE (North Star): What is this project? Who is the customer? What problem does this solve? Why is this task needed NOW? What happens if we DON'T do it?
5. ARCHITECTURE WALKTHROUGH: Where does this piece fit in the architecture? Which container, which layer? What are the neighbors? The developer should know WHERE their work fits.
6. Define the SCOPE: What parts of the system need attention (IN)? What is out of scope (OUT)?
7. ANTICIPATED QUESTIONS: What would a developer ask before starting work? Think like a junior dev seeing this ticket for the first time. Answer 3-5 obvious questions.
8. Produce JSON output."""

        analysis_block = f"""
--- ANALYSIS INPUTS (DO NOT REPEAT — ANALYZE!) ---
The following are RAW FACTS from the codebase. Your job is to ANALYZE what they MEAN
for this specific issue, NOT to copy them into your output.

ANALYSIS RULE: For each fact, explain what it MEANS for this issue.
Example: "ServiceB delegates to ServiceA via internal API — changes here must
verify the cross-boundary contract."

{analysis_inputs or "(none available)"}
--- END ANALYSIS INPUTS ---
""" if analysis_inputs else ""

        # User message: triage task description with all injected context
        user_message = f"""TASK: Analyse Issue Context and Produce Dual Output

You must analyse the issue and findings below, then produce a JSON response
with two sections: `customer_summary` and `developer_context`.

Your output serves ONE PURPOSE: after reading it, a developer should UNDERSTAND
the task deeply before writing a single line of code. No guessing, no ambiguity.

--- ISSUE CONTEXT ---
{task_context}
--- END ISSUE CONTEXT ---

--- SUPPLEMENTARY CONTEXT (requirements, logs) ---
{supplementary_text or "(none)"}
--- END SUPPLEMENTARY ---

--- DETERMINISTIC FINDINGS ---
{findings_json}
--- END FINDINGS ---
{analysis_block}
{steps}

OUTPUT FORMAT (strict JSON):
{{
  "customer_summary": {{
    "summary": "Plain-language explanation INCLUDING why this is needed. Not just WHAT, but WHY and what happens if we don't do it.",
    "impact_level": "low|medium|high|critical",
    "is_bug": true/false,
    "workaround": "Suggested workaround if any, or empty string",
    "eta_category": "quick-fix|short|medium|long|unknown"
  }},
  "developer_context": {{
    "big_picture": "NORTH STAR — answer these: (1) What is this project/system about? (2) Who uses it? (3) What problem does THIS task solve? (4) Why is it needed NOW? (5) What happens if we don't do it?",
    "scope_boundary": "What's IN scope vs OUT of scope for this issue",
    "classification_assessment": "For bugs: structured argument with evidence FOR and AGAINST. For CR/Task: empty string",
    "classification_confidence": 0.0-1.0 or -1,
    "affected_components": ["ComponentName1 (layer)", "ComponentName2 (layer)"],
    "context_boundaries": [
      {{
        "category": "integration_boundary|technology_constraint|dependency_risk|pattern_constraint|data_boundary|security_boundary|testing_constraint|workflow_constraint|infrastructure_constraint",
        "boundary": "What does this fact MEAN for this issue? What constraint or risk arises?",
        "severity": "info|caution|blocking",
        "source_facts": ["tech_versions.json: LibX 6.4.3", "relations.json: ServiceA -> ServiceB"]
      }}
    ],
    "architecture_notes": "WALKTHROUGH: Where does this piece fit in the architecture? Which container(s), which layer(s)? What are the neighboring components? How do they connect? A developer reading this should know EXACTLY where their work fits — like a map with 'YOU ARE HERE'.",
    "anticipated_questions": [
      {{
        "question": "An obvious question a developer would ask before starting",
        "answer": "The answer based on what you know from the codebase analysis"
      }}
    ],
    "linked_tasks": ["Related task IDs or descriptions if identifiable from context"]
  }}
}}

RULES:
- context_boundaries: 2-6 boundaries, each must explain what a fact MEANS (not data copy), include source_facts citing extract file names, and use correct severity (info/caution/blocking)
- If analysis inputs are pre-loaded, use them — do not repeat calls for data already provided
- Triage is for UNDERSTANDING only — do not propose solutions or action steps
"""

        logger.info("[TriageLLM] Calling LLMGenerator")

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]
        raw = self._generator.generate(messages)
        logger.info("[TriageLLM] Received %d chars", len(raw))

        result = self._extract_json(raw)

        # ── Quality gate + automatic retry (mirrors PlanGeneratorStage) ──────
        if result is not None:
            quality = self._score_triage_quality(result)
            threshold = int(os.environ.get("TRIAGE_QUALITY_THRESHOLD", "50"))
            if quality["score"] < threshold and quality["warnings"]:
                logger.info(
                    "[TriageLLM] Quality %d < threshold %d — retrying with feedback: %s",
                    quality["score"], threshold, quality["warnings"],
                )
                raw2 = self._generator.retry_with_feedback(
                    original_messages=messages,
                    previous_output=raw,
                    issues=quality["warnings"],
                )
                result2 = self._extract_json(raw2)
                if result2 is not None:
                    quality2 = self._score_triage_quality(result2)
                    logger.info(
                        "[TriageLLM] Retry quality: %d (was %d)",
                        quality2["score"], quality["score"],
                    )
                    if quality2["score"] >= quality["score"]:
                        result = result2  # accept retry only if not worse

        return result

    @staticmethod
    def _build_deterministic_fallback(
        classification: dict,
        entry_points: list[dict],
        blast_radius: dict,
        risk: dict,
    ) -> dict[str, Any]:
        """Build minimal triage_context from deterministic results.

        Called when LLM synthesis fails so that the downstream Plan phase
        still receives actionable context instead of empty fields.
        """
        affected_components = []
        for ep in entry_points:
            name = ep.get("component", "") if isinstance(ep, dict) else ""
            if name and name not in affected_components:
                affected_components.append(name)
        for item in blast_radius.get("affected", []):
            name = item.get("component", "") if isinstance(item, dict) else ""
            if name and name not in affected_components:
                affected_components.append(name)

        risk_level = risk.get("risk_level", "unknown")
        risk_flags = risk.get("flags", [])

        # Build a synthetic scope_boundary from blast radius
        containers = blast_radius.get("containers_affected", [])
        scope_parts = []
        if containers:
            scope_parts.append(f"Affected containers: {', '.join(containers)}.")
        scope_parts.append(
            f"Blast radius: {blast_radius.get('component_count', 0)} components, "
            f"depth {blast_radius.get('depth', 0)}."
        )

        # Build synthetic context_boundaries from risk flags
        context_boundaries = []
        if risk.get("security_sensitive"):
            context_boundaries.append({
                "category": "security_boundary",
                "boundary": "Security-sensitive components affected — review required.",
                "severity": "caution",
                "source_facts": ["deterministic_risk_assessment"],
            })
        if risk_flags:
            context_boundaries.append({
                "category": "technology_constraint",
                "boundary": f"Risk flags: {', '.join(risk_flags)}.",
                "severity": "caution" if risk_level in ("medium", "high") else "info",
                "source_facts": ["deterministic_risk_assessment"],
            })

        return {
            "big_picture": (
                f"[Deterministic fallback — LLM unavailable] "
                f"{classification.get('type', 'unknown').title()} issue affecting "
                f"{len(affected_components)} component(s). "
                f"Risk level: {risk_level}."
            ),
            "scope_boundary": " ".join(scope_parts),
            "classification_assessment": "",
            "affected_components": affected_components,
            "context_boundaries": context_boundaries,
            "architecture_notes": "",
            "anticipated_questions": [],
        }

    @staticmethod
    def _score_triage_quality(result: dict) -> dict:
        """Score the LLM triage output for quality. Returns {score, warnings}."""
        score = 100
        warnings: list[str] = []
        dev = result.get("developer_context", {})

        # big_picture length check
        bp = dev.get("big_picture", "")
        if len(bp) < 50:
            score -= 20
            warnings.append("big_picture too short (<50 chars)")

        # scope_boundary must mention IN or OUT
        sb = dev.get("scope_boundary", "")
        sb_lower = sb.lower()
        if "in scope" not in sb_lower and "out of scope" not in sb_lower and "in " not in sb_lower:
            score -= 15
            warnings.append("scope_boundary lacks explicit IN/OUT")

        # context_boundaries count
        boundaries = dev.get("context_boundaries", [])
        if len(boundaries) < 2:
            score -= 15
            warnings.append(f"context_boundaries count={len(boundaries)} (<2)")

        # Parrot detection: boundary that just lists versions without analysis.
        # A line is "parroting" only if it's JUST "Name Version" with no analytical
        # content (e.g., "Spring Boot 3.2" alone). Lines that mention a version
        # within a sentence (e.g., "requires Spring Boot 3.2 due to...") are fine.
        bare_version_pattern = re.compile(
            r"^[-•*]?\s*[\w.-]+\s+v?\d+\.\d+[\w.-]*\s*$"
        )
        for b in boundaries:
            text = b.get("boundary", "") if isinstance(b, dict) else ""
            lines = [ln for ln in text.split("\n") if ln.strip()]
            if len(lines) < 3:
                # Too few lines to judge — skip parrot check
                continue
            bare_version_lines = sum(
                1 for ln in lines if bare_version_pattern.match(ln.strip())
            )
            if bare_version_lines > len(lines) / 2:
                score -= 10
                warnings.append(f"parrot detected in boundary: {b.get('category', '?')}")

            # Missing source_facts
            if isinstance(b, dict) and not b.get("source_facts"):
                score -= 5
                warnings.append(f"no source_facts in boundary: {b.get('category', '?')}")

        # Action steps leaked — only flag imperative instructions (sentence-initial
        # action verbs), not descriptive mentions like "this will add a layer..."
        # Only check fields that should be purely analytical:
        #   scope_boundary, context_boundaries, architecture_notes
        action_pattern = re.compile(
            r"(?:^|[.!?;]\s+|[-•*]\s+)"  # sentence/list start
            r"(implement|modify|change the|update the|add a|create a|fix the|remove the)\b",
            re.IGNORECASE,
        )
        check_fields = {
            "scope_boundary": dev.get("scope_boundary", ""),
            "context_boundaries": json.dumps(boundaries, ensure_ascii=False),
            "architecture_notes": dev.get("architecture_notes", ""),
        }
        for field_name, field_text in check_fields.items():
            matches = action_pattern.findall(field_text)
            for match in matches:
                score -= 5
                warnings.append(f"action step leaked in {field_name}: '{match}'")

        # Anticipated questions check (Point 4: Stupid Questions)
        questions = dev.get("anticipated_questions", [])
        if len(questions) < 2:
            score -= 10
            warnings.append(f"anticipated_questions count={len(questions)} (<2)")

        # big_picture must explain WHY (Point 1+3: North Star + Warum)
        bp_lower = bp.lower()
        if not any(w in bp_lower for w in ["warum", "weil", "because", "why", "needed", "security", "risk"]):
            score -= 5
            warnings.append("big_picture lacks WHY motivation")

        # architecture_notes should show placement (Point 2: Walkthrough)
        arch = dev.get("architecture_notes", "")
        if len(arch) < 30:
            score -= 10
            warnings.append("architecture_notes too short for walkthrough (<30 chars)")

        # File paths in developer context
        dev_text = json.dumps(dev, ensure_ascii=False).lower()
        if re.search(r"[/\\]\w+\.\w{2,4}", dev_text):
            score -= 10
            warnings.append("file paths found in developer_context")

        return {"score": max(0, score), "warnings": warnings}

    def _extract_json(self, text: str) -> dict | None:
        """Extract JSON object from LLM output text."""
        # Try direct JSON parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON block in markdown code fences
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find first { ... } block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning("[TriagePipeline] Could not parse JSON from LLM output")
        return None

    # ── Markdown formatting ─────────────────────────────────────────────

    @staticmethod
    def _format_customer_md(customer: dict, issue_id: str) -> str:
        """Format customer summary as Markdown."""
        lines = [
            f"# Issue Summary: {issue_id}",
            "",
            f"**Impact Level:** {customer.get('impact_level', 'unknown').upper()}",
            f"**Type:** {'Bug' if customer.get('is_bug') else 'Enhancement/Task'}",
            f"**Estimated Timeline:** {customer.get('eta_category', 'unknown')}",
            "",
            "## Summary",
            "",
            customer.get("summary", "No summary available."),
            "",
        ]
        workaround = customer.get("workaround", "")
        if workaround:
            lines.extend(["## Workaround", "", workaround, ""])
        return "\n".join(lines)

    @staticmethod
    def _format_developer_md(developer: dict, issue_id: str) -> str:
        """Format developer context as Markdown."""
        lines = [
            f"# Developer Context: {issue_id}",
            "",
            "## Big Picture",
            "",
            developer.get("big_picture", "Needs investigation."),
            "",
            "## Scope Boundary",
            "",
            developer.get("scope_boundary", "Needs investigation."),
            "",
        ]
        assessment = developer.get("classification_assessment", "")
        confidence = developer.get("classification_confidence", -1)
        if assessment:
            confidence_str = ""
            if isinstance(confidence, (int, float)) and confidence >= 0:
                pct = round(confidence * 100)
                if confidence >= 0.7:
                    label = "Confirmed bug"
                elif confidence >= 0.4:
                    label = "Uncertain"
                else:
                    label = "Likely NOT a bug"
                confidence_str = f" ({label} — {pct}%)"
            lines.extend(["## Classification Assessment", "", f"{assessment}{confidence_str}", ""])
        lines.extend(["## Affected Components", ""])
        for c in developer.get("affected_components", []):
            lines.append(f"- {c}")
        boundaries = developer.get("context_boundaries", [])
        if boundaries:
            lines.extend(["", "## Context Boundaries", ""])
            for b in boundaries:
                severity = b.get("severity", "info").upper()
                category = b.get("category", "").replace("_", " ").title()
                boundary_text = b.get("boundary", "")
                sources = [str(s) for s in b.get("source_facts", [])]
                lines.append(f"**[{severity}] {category}**")
                lines.append(boundary_text)
                if sources:
                    lines.append(f"_Sources: {', '.join(sources)}_")
                lines.append("")
        arch = developer.get("architecture_notes", "")
        if arch:
            lines.extend(["", "## Architecture Walkthrough", "", arch])
        questions = developer.get("anticipated_questions", [])
        if questions:
            lines.extend(["", "## Anticipated Questions", ""])
            for q in questions:
                if isinstance(q, dict):
                    lines.append(f"**Q: {q.get('question', '')}**")
                    lines.append(f"A: {q.get('answer', '')}")
                    lines.append("")
        linked = developer.get("linked_tasks", [])
        if linked:
            lines.extend(["", "## Linked Tasks", ""])
            for t in linked:
                lines.append(f"- {t}")
        return "\n".join(lines)

    # ── File I/O ────────────────────────────────────────────────────────

    def _write_json(self, data: dict, filename: str) -> None:
        """Write a versioned JSON report to the triage output directory."""
        path = self.output_dir / filename
        try:
            path.write_text(
                json.dumps(add_schema_version(data, "triage"), indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error("[TriagePipeline] Failed writing %s: %s", filename, e)

    def _write_markdown(self, content: str, filename: str) -> None:
        """Write a Markdown file to the triage output directory."""
        path = self.output_dir / filename
        try:
            path.write_text(content, encoding="utf-8")
        except Exception as e:
            logger.error("[TriagePipeline] Failed writing %s: %s", filename, e)
