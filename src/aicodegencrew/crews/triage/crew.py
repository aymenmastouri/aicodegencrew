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
from .agents import create_triage_agent
from .blast_radius import calculate_blast_radius
from .classifier import classify_issue
from .context_builder import KnowledgeLoader
from .duplicate_detector import find_duplicates
from .entry_point_finder import find_entry_points
from .risk_assessor import assess_risk
from .schemas import TriageRequest
from .tasks import create_triage_task
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

        entry_points = find_entry_points(title, description, knowledge)

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

        # ── Pre-load relevant dimensions ─────────────────────────────────
        dimension_context = self._load_relevant_dimensions(entry_points, blast_radius)

        # ── Phase 2: LLM synthesis ──────────────────────────────────────
        llm_result = None
        llm_ok = False
        try:
            llm_result = self._run_llm_synthesis(
                title, description, task_info, findings, supplementary,
                is_bug=is_bug,
                dimension_context=dimension_context,
            )
            llm_ok = llm_result is not None
        except Exception as e:
            logger.error("[TriageCrew] LLM synthesis failed: %s", e)

        # ── Write outputs ───────────────────────────────────────────────
        customer = {}
        developer = {}
        if llm_result:
            customer = llm_result.get("customer_summary", {})
            developer = llm_result.get("developer_context", {})

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
        summary = {
            "status": "success" if llm_ok else "partial",
            "phase": "triage",
            "issue_id": issue_id,
            "classification": classification.get("type", "unknown"),
            "risk_level": risk.get("risk_level", "unknown"),
            "entry_points_found": len(entry_points),
            "blast_radius_count": blast_radius.get("component_count", 0),
            "llm_synthesis": llm_ok,
            "duration_seconds": duration,
        }
        self._write_json(summary, "summary.json")

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
        entry_points = find_entry_points(title, description, knowledge)
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
        """Load supplementary files (requirements, logs) as text snippets."""
        context: dict[str, str] = {}
        max_chars = 3000
        for category, paths in files.items():
            parts: list[str] = []
            for fp in paths:
                p = Path(fp)
                if not p.exists():
                    continue
                try:
                    text = p.read_text(encoding="utf-8", errors="replace")[:max_chars]
                    parts.append(f"--- {p.name} ---\n{text}")
                except Exception:
                    pass
            if parts:
                context[category] = "\n\n".join(parts)[:max_chars]
        return context

    # ── Dimension pre-loading ────────────────────────────────────────────

    def _load_relevant_dimensions(
        self, entry_points: list[dict], blast_radius: dict,
    ) -> str:
        """Pre-load relevant dimension data based on affected components.

        Reads dimension files from knowledge/extract/ and filters to entries
        relevant to the entry points and blast radius. Returns a formatted
        text block ready for prompt injection.
        """
        extract_dir = self.knowledge_dir / "extract"
        if not extract_dir.exists():
            return ""

        # Collect affected component/container names for filtering
        affected_names: set[str] = set()
        for ep in entry_points:
            if isinstance(ep, dict):
                affected_names.add(ep.get("component", "").lower())
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
        max_total = 4000  # budget for dimension context

        # 1. Technologies
        self._add_dimension_section(
            sections, extract_dir / "tech_versions.json",
            "Technologies", max_items=15,
            formatter=lambda items: "\n".join(
                f"  - {t['technology']} {t.get('version', '?')} ({t.get('category', '')})"
                for t in items
            ),
        )

        # 2. Components (filtered to affected)
        self._add_dimension_section(
            sections, extract_dir / "components.json",
            "Components", key="components",
            filter_fn=lambda c: (
                c.get("name", "").lower() in affected_names
                or c.get("container", "").lower() in affected_containers
            ),
            max_items=20,
            formatter=lambda items: "\n".join(
                f"  - {c['name']} [{c.get('stereotype', '')}] "
                f"layer={c.get('layer', '?')}, container={c.get('container', '?')}"
                for c in items
            ),
        )

        # 3. Containers (filtered to affected)
        self._add_dimension_section(
            sections, extract_dir / "containers.json",
            "Containers", key="containers",
            filter_fn=lambda c: (
                c.get("name", "").lower() in affected_containers
                or not affected_containers  # include all if none specifically affected
            ),
            max_items=10,
            formatter=lambda items: "\n".join(
                f"  - {c.get('name', '?')} ({c.get('technology', '?')}): "
                f"{c.get('description', '')[:120]}"
                for c in items
            ),
        )

        # 4. Interfaces (filtered to affected components)
        self._add_dimension_section(
            sections, extract_dir / "interfaces.json",
            "Interfaces", key="interfaces",
            filter_fn=lambda i: (
                i.get("component", "").lower() in affected_names
                or i.get("source", "").lower() in affected_names
            ),
            max_items=10,
            formatter=lambda items: "\n".join(
                f"  - {i.get('name', '?')} ({i.get('type', '?')}): "
                f"{i.get('description', '')[:100]}"
                for i in items
            ),
        )

        # 5. Error handling
        self._add_dimension_section(
            sections, extract_dir / "error_handling.json",
            "Error Handling", key="strategies",
            max_items=5,
            formatter=lambda items: "\n".join(
                f"  - {e.get('pattern', e.get('name', '?'))}: "
                f"{e.get('description', '')[:100]}"
                for e in items
            ),
        )

        result = "\n\n".join(sections)
        if len(result) > max_total:
            result = result[:max_total] + "\n  ... (truncated)"
        return result

    @staticmethod
    def _add_dimension_section(
        sections: list[str],
        file_path: Path,
        title: str,
        key: str | None = None,
        filter_fn=None,
        max_items: int = 10,
        formatter=None,
    ) -> None:
        """Load a dimension file and append a formatted section."""
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
        sections.append(f"[{title}]\n{body}")

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
        dimension_context: str = "",
    ) -> dict | None:
        """Run single-agent CrewAI crew for triage synthesis."""
        task_context = f"Title: {title}\nDescription: {description}"
        if task_info.get("priority"):
            task_context += f"\nPriority: {task_info['priority']}"
        if task_info.get("labels"):
            task_context += f"\nLabels: {task_info['labels']}"
        if task_info.get("acceptance_criteria"):
            task_context += f"\nAcceptance Criteria:\n{task_info['acceptance_criteria']}"

        findings_json = json.dumps(findings, indent=2, ensure_ascii=False, default=str)
        supplementary_text = "\n\n".join(f"[{k}]\n{v}" for k, v in supplementary.items())

        agent = create_triage_agent(
            facts_dir=self.facts_dir,
            chroma_dir=self.chroma_dir,
        )
        task = create_triage_task(
            agent, task_context, findings_json, supplementary_text,
            is_bug=is_bug, dimension_context=dimension_context,
        )

        log_dir = self.output_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
            step_callback=step_callback,
            task_callback=task_callback,
            output_log_file=str(log_dir / "synthesis.json"),
            embedder=get_crew_embedder(),
        )

        result = crew.kickoff()
        raw = result.raw if hasattr(result, "raw") else str(result)

        # Try to parse JSON from the LLM output
        return self._extract_json(raw)

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
        dimensions = developer.get("relevant_dimensions", [])
        if dimensions:
            lines.extend(["", "## Relevant Dimensions", ""])
            for dim in dimensions:
                name = dim.get("dimension", "")
                insight = dim.get("insight", "")
                if name and insight:
                    lines.append(f"**{name}:** {insight}")
                    lines.append("")
        arch = developer.get("architecture_notes", "")
        if arch:
            lines.extend(["", "## Architecture Notes", "", arch])
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
