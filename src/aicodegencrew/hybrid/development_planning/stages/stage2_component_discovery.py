"""
Stage 2: Component Discovery

Uses ChromaDB semantic search + multi-signal scoring to find affected components.

Signals:
1. Semantic similarity (ChromaDB vector distance)
2. Name matching (fuzzy string match)
3. Package/label matching
4. Stereotype matching (controller, service, etc.)

Duration: 2-5 seconds (RAG + scoring)
NO LLM REQUIRED
"""

import multiprocessing
import os
import queue
import time
from pathlib import Path
from typing import Any

from ....shared.paths import CHROMA_DIR, DISCOVER_SYMBOLS
from ....shared.utils.logger import setup_logger
from ..schemas import ComponentMatch, DependencyRelation, InterfaceMatch, TaskInput

logger = setup_logger(__name__)


# ---------------------------------------------------------------------------
# Subprocess worker for semantic search (crash-isolated)
# ---------------------------------------------------------------------------
# Module-level function so it's picklable by multiprocessing.Process on Windows.
# A segfault in ChromaDB/SQLite/Ollama kills only the child, not the pipeline.


def _semantic_search_subprocess(
    chroma_dir: str,
    query: str,
    n: int,
    components: list[dict],
    result_queue: multiprocessing.Queue,
) -> None:
    """Run ChromaDB semantic search in an isolated subprocess."""
    try:
        import chromadb  # noqa: local import — child process
        from chromadb.config import Settings

        chroma_path = Path(chroma_dir)
        if not chroma_path.exists():
            result_queue.put({})
            return

        client = chromadb.PersistentClient(
            path=str(chroma_path),
            settings=Settings(anonymized_telemetry=False),
        )
        collection = client.get_collection(name="repo_docs")

        # Embed query via Ollama (short timeout — fail fast)
        from aicodegencrew.shared.utils.ollama_client import OllamaClient

        embedding = OllamaClient(timeout=10, max_retries=1).embed_text(query)
        if not embedding:
            result_queue.put({})
            return

        results = collection.query(
            query_embeddings=[embedding],
            n_results=n,
            include=["metadatas", "distances"],
        )

        scores: dict[str, float] = {}
        if results and results.get("metadatas"):
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]
            for i, meta in enumerate(metadatas):
                file_path = meta.get("file_path", "")
                for comp in components:
                    comp_file = comp.get("file_path", "")
                    if comp_file and comp_file in file_path:
                        similarity = 1 - min(distances[i], 1.0)
                        scores[comp["id"]] = similarity
                        break

        result_queue.put(scores)
    except Exception:
        result_queue.put({})


class ComponentDiscoveryStage:
    """
    Discover affected components using RAG + multi-signal scoring.
    """

    def __init__(
        self,
        facts: dict,
        chroma_dir: str = None,
    ):
        """
        Initialize component discovery.

        Args:
            facts: architecture_facts.json (from Phase 1)
            chroma_dir: ChromaDB directory path
        """
        self.facts = facts
        self.chroma_dir = chroma_dir or CHROMA_DIR

        self.components = facts.get("components", [])
        self.interfaces = facts.get("interfaces", [])
        self.relations = facts.get("relations", [])

        self.collection = None  # Lazy init
        self._symbol_index: list[dict] | None = None  # Lazy init

    def run(self, task: TaskInput, top_k: int = 10) -> dict[str, Any]:
        """
        Discover affected components.

        Args:
            task: Parsed task input
            top_k: Number of components to return

        Returns:
            Dict with:
            - affected_components: List[ComponentMatch]
            - interfaces: List[InterfaceMatch]
            - dependencies: List[DependencyRelation]
        """
        logger.info(f"[Stage2] Discovering components for task: {task.task_id}")

        # Upgrade tasks: return ALL components in affected container
        if task.task_type == "upgrade":
            return self._upgrade_discovery(task)

        # Build query from task
        query = f"{task.summary} {task.description}"
        labels = task.labels

        # Multi-signal scoring
        semantic_scores: dict[str, float] = {}
        semantic_timeout_s = int(os.getenv("STAGE2_SEMANTIC_TIMEOUT_S", "12"))

        # Launch semantic search in an ISOLATED SUBPROCESS.
        # ChromaDB/SQLite native code can segfault under memory pressure;
        # a subprocess crash kills only the child, not the pipeline.
        proc: multiprocessing.Process | None = None
        result_queue: multiprocessing.Queue | None = None

        if semantic_timeout_s > 0:
            semantic_start = time.monotonic()
            try:
                result_queue = multiprocessing.Queue(maxsize=1)
                proc = multiprocessing.Process(
                    target=_semantic_search_subprocess,
                    args=(self.chroma_dir, query, 20, self.components, result_queue),
                    daemon=True,
                )
                proc.start()
                logger.debug(f"[Stage2] Semantic search subprocess started (pid={proc.pid})")
            except Exception as exc:
                logger.warning(f"[Stage2] Could not spawn semantic subprocess: {exc}")
                proc = None

        # Run deterministic signals in the main process (parallel to subprocess)
        name_scores = self._name_matching(query)
        package_scores = self._package_matching(labels) if labels else {}
        stereotype_scores = self._stereotype_matching(query)
        symbol_scores = self._symbol_matching(query)

        # Collect subprocess result (or timeout)
        if proc is not None:
            elapsed = time.monotonic() - semantic_start
            remaining = max(0.1, semantic_timeout_s - elapsed)
            proc.join(timeout=remaining)

            if proc.is_alive():
                logger.warning(f"[Stage2] Semantic search subprocess timed out after {semantic_timeout_s}s, terminating")
                proc.terminate()
                proc.join(timeout=3)
                if proc.is_alive():
                    proc.kill()
            elif proc.exitcode != 0:
                logger.warning(f"[Stage2] Semantic search subprocess crashed (exit={proc.exitcode})")
            else:
                # Subprocess finished normally — read scores
                try:
                    semantic_scores = result_queue.get_nowait()
                except queue.Empty:
                    pass

        # Combine scores (weighted average)
        combined_scores = self._combine_scores(
            semantic_scores,
            name_scores,
            package_scores,
            stereotype_scores,
            symbol_scores,
        )

        # Get top K components
        top_component_ids = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # Enrich with component details
        affected_components = []
        for comp_id, score in top_component_ids:
            comp = self._get_component_by_id(comp_id)
            if comp:
                affected_components.append(
                    ComponentMatch(
                        id=comp_id,
                        name=comp.get("name", ""),
                        stereotype=comp.get("stereotype", "unknown"),
                        layer=comp.get("layer", "unknown"),
                        package=comp.get("package", ""),
                        file_path=comp.get("file_path", ""),
                        relevance_score=round(score, 3),
                        change_type=self._infer_change_type(task.description),
                        source=self._determine_source(comp_id, semantic_scores, name_scores, package_scores),
                    )
                )

        # Find related interfaces
        related_interfaces = self._find_interfaces([c.id for c in affected_components])

        # Find dependencies
        dependencies = self._find_dependencies([c.id for c in affected_components])

        logger.info(
            f"[Stage2] Discovered {len(affected_components)} components, "
            f"{len(related_interfaces)} interfaces, {len(dependencies)} dependencies"
        )

        return {
            "affected_components": [c.model_dump() for c in affected_components],
            "interfaces": [i.model_dump() for i in related_interfaces],
            "dependencies": [d.model_dump() for d in dependencies],
        }

    def _upgrade_discovery(self, task: TaskInput) -> dict[str, Any]:
        """Discover ALL components for upgrade tasks (not top-K scoring)."""
        # Detect which container is being upgraded
        text = f"{task.summary} {task.description}".lower()
        target_container = None

        if "angular" in text or "frontend" in text:
            target_container = "container.frontend"
        elif "spring" in text or "backend" in text:
            target_container = "container.backend"

        affected = []
        for comp in self.components:
            container = comp.get("container", "")
            if target_container and target_container not in container:
                continue
            file_paths = comp.get("file_paths", [])
            affected.append(
                ComponentMatch(
                    id=comp.get("id", ""),
                    name=comp.get("name", ""),
                    stereotype=comp.get("stereotype", "unknown"),
                    layer=comp.get("layer", "unknown"),
                    package=comp.get("module", ""),
                    file_path=file_paths[0] if file_paths else "",
                    relevance_score=1.0,
                    change_type="modify",
                    source="upgrade_scan",
                )
            )

        logger.info(f"[Stage2] Upgrade discovery: {len(affected)} components in {target_container or 'all containers'}")

        return {
            "affected_components": [c.model_dump() for c in affected],
            "interfaces": [],
            "dependencies": [],
        }

    def _semantic_search(self, query: str, n: int) -> dict[str, float]:
        """Semantic search using ChromaDB."""
        scores = {}

        try:
            collection = self._get_collection()
            if not collection:
                logger.warning("[Stage2] ChromaDB not available, skipping semantic search")
                return scores

            # Embed query using same Ollama client as indexing pipeline
            query_embedding = self._embed_query(query)
            if not query_embedding:
                logger.warning("[Stage2] Query embedding failed, skipping semantic search")
                return scores
            logger.debug("[Stage2] Query embedding ready (dims=%s)", len(query_embedding))

            logger.debug("[Stage2] Running ChromaDB query (n_results=%s)", n)
            results = collection.query(
                query_embeddings=[query_embedding], n_results=n, include=["metadatas", "distances"]
            )
            logger.debug("[Stage2] ChromaDB query returned")

            if results and results.get("metadatas"):
                metadatas = results["metadatas"][0]
                distances = results["distances"][0]

                for i, metadata in enumerate(metadatas):
                    file_path = metadata.get("file_path", "")
                    comp_id = self._find_component_by_path(file_path)

                    if comp_id:
                        # Convert distance to similarity (0-1)
                        similarity = 1 - min(distances[i], 1.0)
                        scores[comp_id] = similarity

        except Exception as e:
            logger.error(f"[Stage2] ChromaDB error: {e}")

        return scores

    def _name_matching(self, query: str) -> dict[str, float]:
        """Fuzzy name matching using difflib (stdlib)."""
        from difflib import SequenceMatcher

        scores = {}
        query_lower = query.lower()
        query_words = set(query_lower.split())

        for comp in self.components:
            comp_id = comp["id"]
            comp_name = comp["name"].lower()

            # Sequence similarity
            ratio = SequenceMatcher(None, query_lower, comp_name).ratio()

            # Boost if any query word appears as substring in component name
            word_bonus = 0.2 if any(w in comp_name for w in query_words if len(w) > 3) else 0.0

            score = min(ratio + word_bonus, 1.0)

            if score > 0.3:  # Threshold
                scores[comp_id] = score

        return scores

    def _package_matching(self, labels: list[str]) -> dict[str, float]:
        """Match components by package/module labels."""
        scores = {}

        for label in labels:
            label_lower = label.lower()

            for comp in self.components:
                comp_id = comp["id"]
                package = comp.get("package", "").lower()

                if label_lower in package:
                    scores[comp_id] = scores.get(comp_id, 0) + 0.5

        # Normalize to 0-1
        if scores:
            max_score = max(scores.values())
            scores = {k: v / max_score for k, v in scores.items()}

        return scores

    def _stereotype_matching(self, query: str) -> dict[str, float]:
        """Match by stereotype keywords."""
        stereotype_keywords = {
            "controller": ["endpoint", "rest", "api", "http", "controller"],
            "service": ["business", "logic", "process", "workflow", "service"],
            "repository": ["database", "persistence", "dao", "crud", "repository"],
            "entity": ["model", "domain", "data", "entity"],
        }

        query_lower = query.lower()

        # Detect stereotypes in query
        detected_stereotypes = []
        for stereotype, keywords in stereotype_keywords.items():
            if any(kw in query_lower for kw in keywords):
                detected_stereotypes.append(stereotype)

        if not detected_stereotypes:
            return {}

        # Score components matching these stereotypes
        scores = {}
        for comp in self.components:
            comp_id = comp["id"]
            comp_stereotype = comp.get("stereotype", "")

            if comp_stereotype in detected_stereotypes:
                scores[comp_id] = 1.0

        return scores

    def _combine_scores(
        self,
        semantic: dict[str, float],
        name: dict[str, float],
        package: dict[str, float],
        stereotype: dict[str, float],
        symbol: dict[str, float] | None = None,
    ) -> dict[str, float]:
        """Combine scores with weights.

        When symbol index is available, weights are re-balanced:
        semantic=0.30, name=0.25, symbol=0.20, package=0.15, stereotype=0.10
        """
        symbol = symbol or {}

        if symbol:
            weights = {
                "semantic": 0.30,
                "name": 0.25,
                "symbol": 0.20,
                "package": 0.15,
                "stereotype": 0.10,
            }
        else:
            weights = {
                "semantic": 0.4,
                "name": 0.3,
                "symbol": 0.0,
                "package": 0.2,
                "stereotype": 0.1,
            }

        all_ids = (
            set(semantic.keys()) | set(name.keys()) | set(package.keys()) | set(stereotype.keys()) | set(symbol.keys())
        )

        combined = {}
        for comp_id in all_ids:
            score = (
                semantic.get(comp_id, 0) * weights["semantic"]
                + name.get(comp_id, 0) * weights["name"]
                + symbol.get(comp_id, 0) * weights["symbol"]
                + package.get(comp_id, 0) * weights["package"]
                + stereotype.get(comp_id, 0) * weights["stereotype"]
            )
            combined[comp_id] = score

        return combined

    def _find_interfaces(self, component_ids: list[str]) -> list[InterfaceMatch]:
        """Find interfaces implemented by these components."""
        interfaces = []

        for interface in self.interfaces:
            implemented_by = interface.get("implemented_by") or ""

            # Check if any component ID matches
            if any(comp_id in implemented_by for comp_id in component_ids):
                interfaces.append(
                    InterfaceMatch(
                        id=interface["id"],
                        type=interface.get("type", "REST"),
                        path=interface.get("path", ""),
                        method=interface.get("method"),
                        implemented_by=implemented_by,
                    )
                )

        return interfaces

    def _find_dependencies(self, component_ids: list[str]) -> list[DependencyRelation]:
        """Find dependencies between components."""
        dependencies = []

        for relation in self.relations:
            from_id = relation.get("from") or ""
            to_id = relation.get("to") or ""

            # Check if either end is in our component list
            if from_id in component_ids or to_id in component_ids:
                dependencies.append(
                    DependencyRelation(
                        from_component=from_id,
                        to_component=to_id,
                        relation_type=relation.get("type", "uses"),
                    )
                )

        return dependencies

    def _get_component_by_id(self, comp_id: str) -> dict | None:
        """Get component by ID."""
        for comp in self.components:
            if comp["id"] == comp_id:
                return comp
        return None

    def _find_component_by_path(self, file_path: str) -> str | None:
        """Find component ID by file path."""
        for comp in self.components:
            comp_file = comp.get("file_path", "")
            if comp_file and comp_file in file_path:
                return comp["id"]
        return None

    def _infer_change_type(self, description: str) -> str:
        """Infer change type from description."""
        desc_lower = description.lower()

        if any(kw in desc_lower for kw in ["add", "new", "create"]):
            return "create"
        elif any(kw in desc_lower for kw in ["delete", "remove"]):
            return "delete"
        else:
            return "modify"

    def _determine_source(
        self,
        comp_id: str,
        semantic: dict[str, float],
        name: dict[str, float],
        package: dict[str, float],
    ) -> str:
        """Determine which signal contributed most to this match."""
        scores = {
            "chromadb": semantic.get(comp_id, 0),
            "name_match": name.get(comp_id, 0),
            "package_match": package.get(comp_id, 0),
        }

        max_source = max(scores.items(), key=lambda x: x[1])
        return max_source[0] if max_source[1] > 0 else "unknown"

    def _load_symbol_index(self) -> list[dict]:
        """Lazy-load symbols.jsonl for deterministic matching."""
        if self._symbol_index is not None:
            return self._symbol_index

        import json

        symbols_path = Path(DISCOVER_SYMBOLS)
        if not symbols_path.exists():
            self._symbol_index = []
            return self._symbol_index

        records = []
        try:
            with open(symbols_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
            logger.info(f"[Stage2] Loaded {len(records)} symbols for matching")
        except Exception as e:
            logger.debug(f"[Stage2] Could not load symbol index: {e}")

        self._symbol_index = records
        return self._symbol_index

    def _symbol_matching(self, query: str) -> dict[str, float]:
        """Match components by deterministic symbol index lookup."""
        symbols = self._load_symbol_index()
        if not symbols:
            return {}

        query_lower = query.lower()
        query_words = [w for w in query_lower.split() if len(w) > 3]

        # Find symbols matching query words
        matched_paths: dict[str, float] = {}
        for sym in symbols:
            sym_name = sym.get("symbol", "").lower()
            for word in query_words:
                if word in sym_name:
                    path = sym.get("path", "")
                    matched_paths[path] = max(matched_paths.get(path, 0), 0.8)
                    break

        # Map paths back to component IDs
        scores: dict[str, float] = {}
        for path, path_score in matched_paths.items():
            comp_id = self._find_component_by_path(path)
            if comp_id:
                scores[comp_id] = max(scores.get(comp_id, 0), path_score)

        return scores

    def _get_collection(self):
        """Get ChromaDB collection (lazy init)."""
        if self.collection is not None:
            return self.collection

        try:
            import chromadb
            from chromadb.config import Settings

            chroma_path = Path(self.chroma_dir)

            if not chroma_path.exists():
                logger.warning(f"[Stage2] ChromaDB not found at {chroma_path}")
                return None

            client = chromadb.PersistentClient(
                path=str(chroma_path),
                # Semantic search is a best-effort signal; keep Chroma calls bounded.
                settings=Settings(
                    anonymized_telemetry=False,
                    chroma_query_request_timeout_seconds=10,
                    chroma_sysdb_request_timeout_seconds=5,
                ),
            )

            # No embedding function - embeddings were stored externally by indexing pipeline.
            # We embed queries manually via _embed_query() and use query_embeddings.
            self.collection = client.get_collection(name="repo_docs")

            logger.info(f"[Stage2] Connected to ChromaDB at {chroma_path}")
            return self.collection

        except Exception as e:
            logger.error(f"[Stage2] ChromaDB initialization error: {e}")
            return None

    def _embed_query(self, text: str) -> list[float] | None:
        """Embed query text using the same Ollama client as the indexing pipeline."""
        try:
            from ....shared.utils.ollama_client import OllamaClient

            # Stage 2 is expected to finish in a few seconds; use a short, single-attempt
            # embed call so we fail fast instead of hanging the entire pipeline when
            # Ollama is slow or unreachable. Semantic search will be skipped if this
            # returns None, and deterministic signals will still run.
            client = OllamaClient(timeout=10, max_retries=1)
            logger.debug("[Stage2] Embedding query via Ollama (timeout=10s, retries=1)")
            return client.embed_text(text)
        except Exception as e:
            logger.warning(f"[Stage2] Failed to embed query: {e}")
            return None
