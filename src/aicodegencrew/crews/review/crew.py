"""Phase 7: Review and Consistency Guard Crew.

Validates consistency between architecture facts (Phase 2 / extract) and
generated documentation (Phase 3 / document — C4 + arc42).

Architecture: deterministic scan → LLM synthesis

  1. Deterministic phase (no LLM):
       - Check container / component coverage in C4 diagrams
       - Verify required arc42 chapters are present
       - Detect placeholder text (TODO, FIXME, TBD, …)
       - Compute quality score 0-100

  2. LLM synthesis phase:
       - Single agent with FactsQueryTool + RAGQueryTool
       - Synthesises findings into a Markdown report

Input:  knowledge/extract/   (dimension files — containers.json, …)
        knowledge/document/c4/    (C4 diagrams)
        knowledge/document/arc42/ (arc42 chapters)

Output: knowledge/deliver/consistency.json
        knowledge/deliver/quality.json
        knowledge/deliver/summary.json
        knowledge/deliver/synthesis-report.md
"""

import json
import re
import time
from pathlib import Path
from typing import Any

from crewai import Crew, Process

from ...shared.paths import CHROMA_DIR
from ...shared.schema_version import add_schema_version
from ...shared.utils.logger import setup_logger
from .agents import create_quality_reviewer
from .tasks import create_synthesis_task

logger = setup_logger(__name__)

# Required arc42 chapters — stem prefix (lowercase)
_ARC42_REQUIRED: list[str] = [
    "01-introduction",
    "03-system-scope",
    "05-building-block-view",
    "06-runtime-view",
]

# Placeholder markers to detect in documentation files
_PLACEHOLDER_RE = re.compile(
    r"\b(TODO|FIXME|PLACEHOLDER|TBD|XXX)\b", re.IGNORECASE
)


class ReviewCrew:
    """Review and Consistency Guard Crew — Phase 7.

    Reads Phase 2 extract dimension files and Phase 3 document outputs,
    performs deterministic consistency checks, then synthesises findings
    using a single LLM agent into a Markdown quality report.

    Usage (via orchestrator)::

        crew = ReviewCrew()
        orchestrator.register("deliver", crew)

    Direct usage::

        crew = ReviewCrew(knowledge_dir="knowledge")
        result = crew.run()
    """

    def __init__(
        self,
        knowledge_dir: str = "knowledge",
        chroma_dir: str | None = None,
    ):
        self.knowledge_dir = Path(knowledge_dir)
        self.facts_dir = str(self.knowledge_dir / "extract")
        self.document_dir = self.knowledge_dir / "document"
        self.c4_dir = self.knowledge_dir / "document" / "c4"
        self.arc42_dir = self.knowledge_dir / "document" / "arc42"
        self.output_dir = self.knowledge_dir / "deliver"
        self.chroma_dir = chroma_dir or CHROMA_DIR

    # ── Orchestrator interface ────────────────────────────────────────────

    def kickoff(self, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        """Orchestrator-compatible kickoff — called by SDLCOrchestrator."""
        return self.run()

    # ── Main entry point ─────────────────────────────────────────────────

    def run(self) -> dict[str, Any]:
        """Run consistency checks then LLM synthesis."""
        t0 = time.monotonic()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # ── Phase 1: deterministic checks ────────────────────────────────
        consistency = self._check_consistency()
        quality = self._check_quality(consistency)

        # ── Write deterministic reports ───────────────────────────────────
        self._write_json(consistency, "consistency.json")
        self._write_json(quality, "quality.json")

        # ── Phase 2: LLM synthesis ────────────────────────────────────────
        synthesis_path = str(self.output_dir / "synthesis-report.md")
        llm_ok = False
        try:
            llm_ok = self._run_llm_synthesis(consistency, quality, synthesis_path)
        except Exception as e:
            logger.error("[ReviewCrew] LLM synthesis failed: %s", e)

        duration = round(time.monotonic() - t0, 2)
        issue_count = (
            len(consistency.get("missing_containers", []))
            + len(consistency.get("missing_arc42_chapters", []))
        )
        summary = {
            "status": "success",
            "phase": "deliver",
            "quality_score": quality.get("score", 0),
            "consistency_issues": issue_count,
            "placeholder_count": quality.get("placeholder_count", 0),
            "synthesis_report": synthesis_path if llm_ok else None,
            "duration_seconds": duration,
        }
        self._write_json(summary, "summary.json")

        logger.info(
            "[ReviewCrew] Done — score=%d, issues=%d, duration=%.1fs",
            summary["quality_score"],
            issue_count,
            duration,
        )
        return summary

    # ── Deterministic consistency checks ─────────────────────────────────

    def _check_consistency(self) -> dict[str, Any]:
        """Scan facts and document outputs; return a consistency report dict."""
        containers_in_facts = self._load_fact_containers()
        containers_in_c4 = self._scan_c4_for_containers(containers_in_facts)
        missing_containers = [c for c in containers_in_facts if c not in containers_in_c4]
        extra_containers = [c for c in containers_in_c4 if c not in containers_in_facts]

        chapters_present = self._check_arc42_chapters()
        missing_chapters = [ch for ch in _ARC42_REQUIRED if ch not in chapters_present]

        c4_files = {
            "container_diagram": (self.c4_dir / "c4-container.md").exists(),
            "context_diagram": (self.c4_dir / "c4-context.md").exists(),
        }

        return {
            "containers_in_facts": containers_in_facts,
            "containers_found_in_c4": containers_in_c4,
            "missing_containers": missing_containers,
            "extra_containers": extra_containers,
            "arc42_chapters_present": chapters_present,
            "missing_arc42_chapters": missing_chapters,
            "c4_files": c4_files,
        }

    def _check_quality(self, consistency: dict) -> dict[str, Any]:
        """Compute a 0-100 quality score and collect placeholder findings."""
        placeholders = self._scan_placeholders()
        score = 100

        # Deduct for missing arc42 chapters (up to -30)
        missing_chapters = consistency.get("missing_arc42_chapters", [])
        score -= min(len(missing_chapters) * 10, 30)

        # Deduct for missing containers (up to -20)
        missing_containers = consistency.get("missing_containers", [])
        score -= min(len(missing_containers) * 5, 20)

        # Deduct for hallucinated / extra containers (up to -15)
        extra_containers = consistency.get("extra_containers", [])
        score -= min(len(extra_containers) * 5, 15)

        # Deduct for excessive placeholder text
        placeholder_count = sum(len(v) for v in placeholders.values())
        if placeholder_count > 10:
            score -= 10
        elif placeholder_count > 5:
            score -= 5

        # Deduct for missing C4 key diagrams
        c4_files = consistency.get("c4_files", {})
        if not c4_files.get("container_diagram"):
            score -= 10
        if not c4_files.get("context_diagram"):
            score -= 5

        score = max(0, score)
        return {
            "score": score,
            "placeholder_count": placeholder_count,
            "placeholder_locations": placeholders,
            "severity": "high" if score < 60 else ("medium" if score < 80 else "low"),
        }

    # ── Fact / document helpers ───────────────────────────────────────────

    def _load_fact_containers(self) -> list[str]:
        """Load container names from knowledge/extract/containers.json."""
        path = Path(self.facts_dir) / "containers.json"
        if not path.exists():
            logger.warning("[ReviewCrew] containers.json not found: %s", path)
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            items = data if isinstance(data, list) else data.get("containers", [])
            return [item.get("name", "") for item in items if item.get("name")]
        except Exception as e:
            logger.error("[ReviewCrew] Failed loading containers.json: %s", e)
            return []

    def _scan_c4_for_containers(self, container_names: list[str]) -> list[str]:
        """Return which container names from the facts list appear in C4 diagrams."""
        if not self.c4_dir.exists() or not container_names:
            return []
        try:
            all_text = ""
            for md_file in self.c4_dir.glob("*.md"):
                all_text += md_file.read_text(encoding="utf-8", errors="replace")
            return [name for name in container_names if name.lower() in all_text.lower()]
        except Exception as e:
            logger.error("[ReviewCrew] Error scanning C4 diagrams: %s", e)
            return []

    def _check_arc42_chapters(self) -> list[str]:
        """Return the list of _ARC42_REQUIRED chapter prefixes found on disk."""
        if not self.arc42_dir.exists():
            return []
        present: list[str] = []
        for md_file in self.arc42_dir.glob("*.md"):
            stem = md_file.stem.lower()
            for chapter in _ARC42_REQUIRED:
                if chapter not in present and stem.startswith(chapter):
                    present.append(chapter)
        return present

    def _scan_placeholders(self) -> dict[str, list[str]]:
        """Scan all .md files in document_dir for placeholder markers.

        Returns:
            Dict mapping ``str(file_path)`` → list of matching line snippets.
        """
        findings: dict[str, list[str]] = {}
        if not self.document_dir.exists():
            return findings
        for md_file in self.document_dir.rglob("*.md"):
            matches: list[str] = []
            try:
                lines = md_file.read_text(encoding="utf-8", errors="replace").splitlines()
                for i, line in enumerate(lines, 1):
                    if _PLACEHOLDER_RE.search(line):
                        matches.append(f"L{i}: {line.strip()[:120]}")
            except Exception:
                pass
            if matches:
                findings[str(md_file)] = matches
        return findings

    # ── LLM synthesis ─────────────────────────────────────────────────────

    def _run_llm_synthesis(
        self,
        consistency: dict,
        quality: dict,
        output_path: str,
    ) -> bool:
        """Run a single-agent CrewAI crew to synthesise a Markdown quality report.

        Returns:
            True if the report was written successfully, False otherwise.
        """
        findings_summary = json.dumps(
            {"consistency": consistency, "quality": quality},
            indent=2,
            ensure_ascii=False,
        )
        agent = create_quality_reviewer(
            facts_dir=self.facts_dir,
            chroma_dir=self.chroma_dir,
        )
        task = create_synthesis_task(agent, findings_summary, output_path)

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )
        try:
            result = crew.kickoff()
            raw = result.raw if hasattr(result, "raw") else str(result)
            Path(output_path).write_text(raw, encoding="utf-8")
            logger.info("[ReviewCrew] Synthesis report written: %s", output_path)
            return True
        except Exception as e:
            logger.error("[ReviewCrew] Synthesis crew failed: %s", e)
            return False

    # ── File I/O ──────────────────────────────────────────────────────────

    def _write_json(self, data: dict, filename: str) -> None:
        """Write a versioned JSON report to the deliver output directory."""
        path = self.output_dir / filename
        try:
            path.write_text(
                json.dumps(add_schema_version(data, "deliver"), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error("[ReviewCrew] Failed writing %s: %s", filename, e)
