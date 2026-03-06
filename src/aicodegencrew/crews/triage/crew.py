"""Issue Triage Crew — deterministic analysis + LLM synthesis.

Architecture: deterministic scan → LLM synthesis (follows ReviewCrew pattern).

  1. Deterministic phase (no LLM, <5s):
       - Classify issue (bug | feature | refactor | investigation)
       - Find entry-point components (multi-signal matching)
       - Calculate blast radius (BFS on relation graph)
       - Find similar code/issues (ChromaDB)
       - Check test coverage for affected components
       - Assess risk (security, error handling, quality)

  2. LLM synthesis phase:
       - Single agent with FactsQueryTool + RAGQueryTool + SymbolQueryTool
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
import time
from pathlib import Path
from typing import Any

from crewai import Crew, Process

from ...shared.paths import CHROMA_DIR, get_chroma_dir
from ...shared.schema_version import add_schema_version
from ...shared.utils.crew_callbacks import step_callback, task_callback
from ...shared.utils.embedder_config import get_crew_embedder
from ...shared.utils.logger import setup_logger
from .agents import create_triage_agent, create_triage_reviewer_agent
from .blast_radius import calculate_blast_radius
from .classifier import classify_issue
from .context_builder import KnowledgeLoader
from .duplicate_detector import find_duplicates
from .entry_point_finder import find_entry_points
from .risk_assessor import assess_risk
from .schemas import TriageRequest
from .tasks import create_review_task, create_triage_task
from .test_coverage import check_test_coverage

logger = setup_logger(__name__)


class TriageCrew:
    """Issue Triage Crew — deterministic analysis + LLM synthesis.

    Usage (via orchestrator)::

        crew = TriageCrew()
        orchestrator.register("triage", crew)

    Direct usage::

        crew = TriageCrew(knowledge_dir="knowledge")
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
        self.chroma_dir = chroma_dir or get_chroma_dir()
        self._loader = KnowledgeLoader(knowledge_dir)

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
            llm_error = f"LLM server unreachable (VPN off?): {health_msg}"
            logger.error("[TriageCrew] %s — skipping LLM synthesis entirely", llm_error)
        else:
            logger.info("[TriageCrew] LLM health check: %s", health_msg)
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
                    logger.error("[TriageCrew] LLM synthesis returned None — no JSON in output")
            except Exception as e:
                llm_error = str(e)
                logger.error(
                    "[TriageCrew] LLM synthesis FAILED (is VPN/LLM server reachable?): %s", e,
                )

        # ── Quality gate ────────────────────────────────────────────────
        if llm_result:
            quality = self._score_triage_quality(llm_result)
            if quality["score"] < 50:
                logger.warning("[TriageCrew] Quality score %d — partial: %s", quality["score"], quality["warnings"])
                llm_status = "partial"  # downgrade: LLM ran but output is poor
            elif quality["warnings"]:
                logger.info("[TriageCrew] Quality score %d — warnings: %s", quality["score"], quality["warnings"])

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
                    "[TriageCrew] LLM overrides classification: %s → %s "
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
            # LLM failed — downstream phases should know context is incomplete
            triage_context["llm_error"] = llm_error or "LLM synthesis failed"

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
                "[TriageCrew] INCOMPLETE — LLM synthesis FAILED for %s. "
                "Deterministic analysis saved but developer_context is EMPTY. "
                "Check VPN/LLM server connectivity. Error: %s",
                issue_id, llm_error,
            )
        elif llm_status == "partial":
            logger.warning(
                "[TriageCrew] Done (partial) — LLM output below quality threshold for %s",
                issue_id,
            )
        else:
            logger.info(
                "[TriageCrew] Done — type=%s, risk=%s, entry_points=%d, duration=%.1fs",
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
            from ...hybrid.development_planning.stages.stage1_input_parser import InputParserStage

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
            logger.warning("[TriageCrew] Task file parse failed: %s", e)
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
                    logger.warning("[TriageCrew] Failed to load supplementary %s: %s", p.name, e)
            if parts:
                context[category] = "\n\n".join(parts)[:max_chars]
        return context

    @staticmethod
    def _extract_pdf_text(path: Path, max_chars: int = 3000) -> str:
        """Extract text from a PDF file using pymupdf."""
        try:
            import pymupdf
        except ImportError:
            logger.warning("[TriageCrew] pymupdf not installed — cannot extract PDF text")
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
            logger.warning("[TriageCrew] PDF extraction failed for %s: %s", path.name, e)
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
        """Run 2-agent mini-crew for triage synthesis.

        Agent 1 (Issue Context Analyst): produces initial synthesis.
        Agent 2 (Triage Quality Reviewer): validates and fixes quality issues.
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

        # Agent 1: Issue Context Analyst (has tools for querying knowledge)
        analyst = create_triage_agent(
            facts_dir=self.facts_dir,
            chroma_dir=self.chroma_dir,
        )
        analyst_task = create_triage_task(
            analyst, task_context, findings_json, supplementary_text,
            is_bug=is_bug, analysis_inputs=analysis_inputs,
        )

        # Agent 2: Quality Reviewer (no tools — pure review)
        reviewer = create_triage_reviewer_agent()
        review_task = create_review_task(reviewer)

        log_dir = self.output_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        crew = Crew(
            agents=[analyst, reviewer],
            tasks=[analyst_task, review_task],
            process=Process.sequential,
            verbose=True,
            step_callback=step_callback,
            task_callback=task_callback,
            output_log_file=str(log_dir / "synthesis.json"),
            embedder=get_crew_embedder(),
        )

        logger.info("[TriageCrew] Starting 2-agent mini-crew: analyst + reviewer")
        result = crew.kickoff()
        raw = result.raw if hasattr(result, "raw") else str(result)

        # Try to parse JSON from the LLM output (reviewer's corrected version)
        return self._extract_json(raw)

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

        # Parrot detection: boundary that just lists versions without analysis
        import re
        version_pattern = re.compile(r"^\s*[\w.-]+\s+\d+\.\d+")
        for b in boundaries:
            text = b.get("boundary", "") if isinstance(b, dict) else ""
            # If more than half the lines are just "name version" patterns
            lines = [ln for ln in text.split("\n") if ln.strip()]
            version_lines = sum(1 for ln in lines if version_pattern.match(ln.strip()))
            if lines and version_lines > len(lines) / 2:
                score -= 10
                warnings.append(f"parrot detected in boundary: {b.get('category', '?')}")

            # Missing source_facts
            if isinstance(b, dict) and not b.get("source_facts"):
                score -= 5
                warnings.append(f"no source_facts in boundary: {b.get('category', '?')}")

        # Action steps leaked — check context_boundaries and architecture_notes only
        # (scope_boundary legitimately contains words like "change", "update")
        action_words = ["implement", "modify", "change the", "update the", "add a", "create a", "fix the"]
        check_fields = {
            "context_boundaries": json.dumps(boundaries, ensure_ascii=False).lower(),
            "architecture_notes": dev.get("architecture_notes", "").lower(),
        }
        for field_name, field_text in check_fields.items():
            for word in action_words:
                if word in field_text:
                    score -= 5
                    warnings.append(f"action step leaked in {field_name}: '{word}'")

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
        import re

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

        logger.warning("[TriageCrew] Could not parse JSON from LLM output")
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
            logger.error("[TriageCrew] Failed writing %s: %s", filename, e)

    def _write_markdown(self, content: str, filename: str) -> None:
        """Write a Markdown file to the triage output directory."""
        path = self.output_dir / filename
        try:
            path.write_text(content, encoding="utf-8")
        except Exception as e:
            logger.error("[TriageCrew] Failed writing %s: %s", filename, e)
