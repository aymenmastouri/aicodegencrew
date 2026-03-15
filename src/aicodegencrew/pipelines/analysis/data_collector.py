"""DataCollector — deterministic fact loading for analysis sections.

Reads architecture facts files directly from disk (no CrewAI agents, no tool loops).
Optionally queries ChromaDB for RAG-based code evidence.

No LLM calls, no agents — pure Python data collection.
"""

import json
import logging
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Ensure .env is loaded even when called outside CLI subprocess
load_dotenv(override=True)

logger = logging.getLogger(__name__)


class DataCollector:
    """Loads architecture facts and provides section-scoped data slices.

    Facts are loaded once via ``load()`` and then served to ``collect_section_data()``
    without any further disk I/O.  ChromaDB RAG queries are attempted lazily and
    fail gracefully (return []) when ChromaDB is unavailable.
    """

    def __init__(self, facts_dir: str | Path, chroma_dir: str | None = None):
        """Initialise the collector.

        Args:
            facts_dir:  Directory containing architecture_facts.json and the
                        ``dimensions/`` sub-folder (e.g. ``knowledge/extract``).
            chroma_dir: Optional path to a ChromaDB persistent directory.
                        When None the RAG tool uses its own auto-discovery logic.
        """
        self._facts_dir = Path(facts_dir)
        self._chroma_dir = chroma_dir

        # Populated by load()
        self._facts: dict[str, Any] = {}
        self._components: list[dict] = []
        self._relations: list[dict] = []
        self._interfaces: list[dict] = []
        self._containers: list[dict] = []

    # ── Loading ──────────────────────────────────────────────────────────────

    def load(self) -> None:
        """Load all fact files into memory once.

        Reads:
        - ``{facts_dir}/architecture_facts.json``
        - ``{facts_dir}/dimensions/components.json``
        - ``{facts_dir}/dimensions/relations.json``
        - ``{facts_dir}/dimensions/interfaces.json``
        - ``{facts_dir}/dimensions/containers.json``

        Falls back gracefully when individual files are absent.
        """
        facts_path = self._facts_dir / "architecture_facts.json"
        if facts_path.exists():
            self._facts = json.loads(facts_path.read_text(encoding="utf-8"))
            logger.info("[DataCollector] Loaded facts: %d top-level keys", len(self._facts))
        else:
            logger.warning("[DataCollector] architecture_facts.json not found at %s", facts_path)

        # Load dimension files — prefer dedicated files, fall back to facts keys
        self._components = self._load_dimension("components")
        self._relations = self._load_dimension("relations")
        self._interfaces = self._load_dimension("interfaces")
        self._containers = self._load_dimension("containers")

        logger.info(
            "[DataCollector] Loaded — components:%d relations:%d interfaces:%d containers:%d",
            len(self._components),
            len(self._relations),
            len(self._interfaces),
            len(self._containers),
        )

    def _load_dimension(self, name: str) -> list[dict]:
        """Load a dimension list from its dedicated file or from facts fallback."""
        # Try dimensions/ sub-folder first (canonical location)
        dim_path = self._facts_dir / "dimensions" / f"{name}.json"
        if dim_path.exists():
            try:
                raw = json.loads(dim_path.read_text(encoding="utf-8"))
                # The file may be a plain list or {"components": [...]}
                if isinstance(raw, list):
                    return raw
                if isinstance(raw, dict) and name in raw:
                    return raw[name]
                # Single-level dict — treat as list of one
                return [raw]
            except Exception as exc:
                logger.warning("[DataCollector] Could not load %s: %s", dim_path, exc)

        # Try direct file in facts_dir (legacy flat layout)
        flat_path = self._facts_dir / f"{name}.json"
        if flat_path.exists():
            try:
                raw = json.loads(flat_path.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    return raw
                if isinstance(raw, dict) and name in raw:
                    return raw[name]
            except Exception as exc:
                logger.warning("[DataCollector] Could not load %s: %s", flat_path, exc)

        # Fall back to the top-level facts key
        fallback = self._facts.get(name, [])
        if isinstance(fallback, list):
            return fallback
        return []

    # ── Statistics ───────────────────────────────────────────────────────────

    def get_statistics(self) -> dict:
        """Return aggregate counts and stereotype breakdown.

        Returns:
            dict with keys: total_components, total_relations, total_interfaces,
            total_containers, stereotypes (dict stereotype -> count).
        """
        stereotypes: dict[str, int] = {}
        for comp in self._components:
            if isinstance(comp, dict):
                st = comp.get("stereotype", "unknown")
                stereotypes[st] = stereotypes.get(st, 0) + 1

        return {
            "total_components": len(self._components),
            "total_relations": len(self._relations),
            "total_interfaces": len(self._interfaces),
            "total_containers": len(self._containers),
            "stereotypes": stereotypes,
        }

    # ── Slice helpers ─────────────────────────────────────────────────────────

    def get_components_by_stereotype(self, stereotype: str, limit: int = 50) -> list[dict]:
        """Return components matching *stereotype* (case-insensitive), capped at *limit*."""
        filtered = [
            c
            for c in self._components
            if isinstance(c, dict) and c.get("stereotype", "").lower() == stereotype.lower()
        ]
        return filtered[:limit]

    def get_containers(self) -> list[dict]:
        """Return all containers."""
        return list(self._containers)

    def get_relations(self, limit: int = 100) -> list[dict]:
        """Return relations capped at *limit*."""
        return self._relations[:limit]

    def get_interfaces(self, limit: int = 50) -> list[dict]:
        """Return interfaces/endpoints capped at *limit*."""
        return self._interfaces[:limit]

    # ── RAG ──────────────────────────────────────────────────────────────────

    def rag_query(self, query: str, limit: int = 8) -> list[dict]:
        """Query ChromaDB for semantic code evidence.

        Returns an empty list when ChromaDB is unavailable — callers must handle
        the absence of RAG results gracefully.

        Args:
            query: Natural language search query.
            limit: Maximum results to return.

        Returns:
            List of result dicts with keys: file_path, relevance_score, content.
        """
        try:
            from ...shared.tools.rag_query_tool import RAGQueryTool

            tool = RAGQueryTool(chroma_dir=self._chroma_dir)
            result_json = tool._run(query=query, limit=limit)
            result = json.loads(result_json)
            return result.get("results", [])
        except Exception as exc:
            logger.debug("[DataCollector] RAG query failed for '%s': %s", query, exc)
            return []

    # ── Section data map ─────────────────────────────────────────────────────

    def collect_section_data(self, section_id: str) -> dict:
        """Collect all data required for a specific analysis section.

        Section IDs "01" through "16" correspond to the 16 analysis tasks.
        The returned dict is passed directly to AnalysisPromptBuilder.build_section().

        Args:
            section_id: Two-digit string e.g. "01", "13".

        Returns:
            dict with relevant sub-sets of facts (statistics, components, relations,
            interfaces, containers) and optional rag_results list.
        """
        stats = self.get_statistics()

        section_map = {
            "01": self._section_01,
            "02": self._section_02,
            "03": self._section_03,
            "04": self._section_04,
            "05": self._section_05,
            "06": self._section_06,
            "07": self._section_07,
            "08": self._section_08,
            "09": self._section_09,
            "10": self._section_10,
            "11": self._section_11,
            "12": self._section_12,
            "13": self._section_13,
            "14": self._section_14,
            "15": self._section_15,
            "16": self._section_16,
        }

        fn = section_map.get(section_id)
        if fn is None:
            logger.warning("[DataCollector] Unknown section_id: %s", section_id)
            return {"statistics": stats}

        data = fn(stats)
        logger.debug(
            "[DataCollector] Section %s data keys: %s",
            section_id,
            list(data.keys()),
        )
        return data

    # ── Per-section data methods ─────────────────────────────────────────────

    def _section_01(self, stats: dict) -> dict:
        """01 — Macro Architecture: statistics + containers + relations[:50]."""
        return {
            "statistics": stats,
            "containers": self.get_containers(),
            "relations": self.get_relations(50),
        }

    def _section_02(self, stats: dict) -> dict:
        """02 — Backend Pattern: statistics + controllers/services/repos/entities."""
        return {
            "statistics": stats,
            "controllers": self.get_components_by_stereotype("controller", 50),
            "services": self.get_components_by_stereotype("service", 50),
            "repositories": self.get_components_by_stereotype("repository", 50),
            "entities": self.get_components_by_stereotype("entity", 30),
        }

    def _section_03(self, stats: dict) -> dict:
        """03 — Frontend Pattern: containers + components + modules."""
        return {
            "containers": self.get_containers(),
            "components": self.get_components_by_stereotype("component", 50),
            "modules": self.get_components_by_stereotype("module", 50),
        }

    def _section_04(self, stats: dict) -> dict:
        """04 — Architecture Quality: statistics + relations[:100]."""
        return {
            "statistics": stats,
            "relations": self.get_relations(100),
        }

    def _section_05(self, stats: dict) -> dict:
        """05 — Domain Model: statistics + entities[:100]."""
        return {
            "statistics": stats,
            "entities": self.get_components_by_stereotype("entity", 100),
        }

    def _section_06(self, stats: dict) -> dict:
        """06 — Business Capabilities: services[:100]."""
        return {
            "services": self.get_components_by_stereotype("service", 100),
        }

    def _section_07(self, stats: dict) -> dict:
        """07 — Bounded Contexts: statistics + entities + services + relations[:50]."""
        return {
            "statistics": stats,
            "entities": self.get_components_by_stereotype("entity", 50),
            "services": self.get_components_by_stereotype("service", 50),
            "relations": self.get_relations(50),
        }

    def _section_08(self, stats: dict) -> dict:
        """08 — State Machines: entities + RAG state/status queries."""
        return {
            "entities": self.get_components_by_stereotype("entity", 50),
            "rag_state_machine": self.rag_query("state machine StateMachine enum Status"),
            "rag_transitions": self.rag_query("status transition PENDING APPROVED REJECTED"),
        }

    def _section_09(self, stats: dict) -> dict:
        """09 — Workflow Engines: RAG workflow queries + design_pattern components."""
        return {
            "rag_workflow_engine": self.rag_query("workflow engine process BPMN"),
            "rag_workflow_libs": self.rag_query("Camunda Flowable Activiti Temporal Celery"),
            "design_patterns": self.get_components_by_stereotype("design_pattern", 20),
        }

    def _section_10(self, stats: dict) -> dict:
        """10 — Saga Patterns: RAG saga/outbox queries + design_pattern components."""
        return {
            "rag_saga": self.rag_query("saga pattern compensation rollback"),
            "rag_outbox": self.rag_query("outbox pattern event publishing"),
            "design_patterns": self.get_components_by_stereotype("design_pattern", 20),
        }

    def _section_11(self, stats: dict) -> dict:
        """11 — Runtime Scenarios: controllers + interfaces[:30]."""
        return {
            "controllers": self.get_components_by_stereotype("controller", 30),
            "interfaces": self.get_interfaces(30),
        }

    def _section_12(self, stats: dict) -> dict:
        """12 — API Design: statistics + interfaces[:50]."""
        return {
            "statistics": stats,
            "interfaces": self.get_interfaces(50),
        }

    def _section_13(self, stats: dict) -> dict:
        """13 — Complexity: statistics + relations[:100]."""
        return {
            "statistics": stats,
            "relations": self.get_relations(100),
        }

    def _section_14(self, stats: dict) -> dict:
        """14 — Technical Debt: statistics + RAG debt queries."""
        return {
            "statistics": stats,
            "rag_todo_fixme": self.rag_query("TODO FIXME HACK workaround"),
            "rag_deprecated": self.rag_query("deprecated @Deprecated SuppressWarnings"),
        }

    def _section_15(self, stats: dict) -> dict:
        """15 — Security: RAG security/auth queries."""
        return {
            "rag_security_config": self.rag_query("security config authentication"),
            "rag_jwt_oauth": self.rag_query("JWT OAuth2 token"),
            "rag_authorization": self.rag_query("authorization permission role"),
            "rag_csrf_xss": self.rag_query("CSRF XSS input validation"),
        }

    def _section_16(self, stats: dict) -> dict:
        """16 — Operational Readiness: RAG ops queries."""
        return {
            "rag_health": self.rag_query("health check liveness readiness"),
            "rag_logging": self.rag_query("logging structured log level"),
            "rag_metrics": self.rag_query("metrics prometheus monitoring"),
            "rag_config": self.rag_query("configuration environment profile"),
        }
