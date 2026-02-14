"""Indexing pipeline (Phase 0) - Repository indexing to ChromaDB.

Single merged class handling all index modes (off/auto/smart/force),
persistent state, stale lock recovery, and embedding failure monitoring.
"""

import ctypes
import hashlib
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from ...shared.paths import CHROMA_DIR
from ...shared.utils.file_filters import collect_files
from ...shared.utils.logger import log_metric, setup_logger
from .chroma_index_tool import ChromaIndexTool
from .chunker_tool import ChunkerTool
from .embeddings_tool import OllamaEmbeddingsTool
from .repo_discovery_tool import RepoDiscoveryTool
from .repo_reader_tool import RepoReaderTool

logger = setup_logger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class IndexingConfig:
    """Configuration for indexing pipeline."""

    repo_path: Path
    index_mode: str = "auto"
    chroma_dir: str | None = None
    collection_name: str = "repo_docs"
    include_submodules: bool = True
    batch_size: int = 50
    max_total_files: int = 8000
    max_total_chunks: int = 50000
    chunk_chars: int = 1800
    chunk_overlap: int = 200
    max_file_bytes: int = 2000000
    lock_timeout_s: int = 300
    fingerprint_max_files: int = 2000

    @classmethod
    def from_env(cls, repo_path: str = None, index_mode: str = None, chroma_dir: str = None) -> "IndexingConfig":
        """Create config from environment variables with optional overrides."""
        if repo_path is None:
            repo_path = os.getenv("PROJECT_PATH") or os.getenv("REPO_PATH")
        if not repo_path:
            raise ValueError("No repository path specified.")

        resolved_path = Path(repo_path).resolve()
        if not resolved_path.exists():
            raise ValueError(f"Repo path not found: {resolved_path}")

        return cls(
            repo_path=resolved_path,
            index_mode=index_mode or os.getenv("INDEX_MODE", "auto"),
            chroma_dir=chroma_dir or CHROMA_DIR,
            collection_name=os.getenv("COLLECTION_NAME", "repo_docs"),
            include_submodules=True,
            batch_size=int(os.getenv("INDEX_BATCH_SIZE", "50")),
            max_total_files=int(os.getenv("INDEX_MAX_TOTAL_FILES", "8000")),
            max_total_chunks=int(os.getenv("INDEX_MAX_TOTAL_CHUNKS", "50000")),
            chunk_chars=int(os.getenv("CHUNK_CHARS", "1800")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
            max_file_bytes=int(os.getenv("MAX_FILE_BYTES", "2000000")),
            lock_timeout_s=int(os.getenv("INDEX_LOCK_TIMEOUT_S", "300")),
            fingerprint_max_files=int(os.getenv("FINGERPRINT_MAX_FILES", "2000")),
        )


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


@dataclass
class IndexingMetrics:
    """Metrics for indexing operation."""

    total_files_discovered: int = 0
    total_files_processed: int = 0
    total_chunks_created: int = 0
    total_chunks_indexed: int = 0
    total_embeddings_none: int = 0
    batches_processed: int = 0
    batches_failed: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None

    @property
    def duration_seconds(self) -> float:
        end = self.end_time or time.time()
        return end - self.start_time

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_files_discovered": self.total_files_discovered,
            "total_files_processed": self.total_files_processed,
            "total_chunks_created": self.total_chunks_created,
            "total_chunks_indexed": self.total_chunks_indexed,
            "total_embeddings_none": self.total_embeddings_none,
            "batches_processed": self.batches_processed,
            "batches_failed": self.batches_failed,
            "duration_seconds": self.duration_seconds,
            "chunks_per_second": (
                self.total_chunks_indexed / self.duration_seconds if self.duration_seconds > 0 else 0
            ),
        }


# ---------------------------------------------------------------------------
# Persistent state
# ---------------------------------------------------------------------------


@dataclass
class IndexingState:
    """Persistent indexing state saved to `.cache/.indexing_state.json`.

    Survives ChromaDB deletion so that ``auto`` mode can detect
    "fingerprint unchanged but ChromaDB missing" and warn instead of
    silently re-indexing for 3 hours.
    """

    fingerprint: str = ""
    fingerprint_type: str = ""
    chunk_count: int = 0
    timestamp: float = 0.0
    repo_path: str = ""

    _STATE_FILENAME = ".indexing_state.json"

    @classmethod
    def _state_path(cls, cache_dir: Path) -> Path:
        return cache_dir / cls._STATE_FILENAME

    @classmethod
    def load(cls, cache_dir: Path) -> Optional["IndexingState"]:
        path = cls._state_path(cache_dir)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(
                fingerprint=data.get("fingerprint", ""),
                fingerprint_type=data.get("fingerprint_type", ""),
                chunk_count=data.get("chunk_count", 0),
                timestamp=data.get("timestamp", 0.0),
                repo_path=data.get("repo_path", ""),
            )
        except Exception as e:
            logger.warning(f"Could not load indexing state: {e}")
            return None

    def save(self, cache_dir: Path) -> None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        path = self._state_path(cache_dir)
        data = {
            "fingerprint": self.fingerprint,
            "fingerprint_type": self.fingerprint_type,
            "chunk_count": self.chunk_count,
            "timestamp": self.timestamp,
            "repo_path": self.repo_path,
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.debug(f"Saved indexing state to {path}")


# ---------------------------------------------------------------------------
# Lock helpers
# ---------------------------------------------------------------------------


def _get_index_lock_path(chroma_dir: str | None = None) -> Path:
    d = chroma_dir or CHROMA_DIR
    return Path(d).resolve() / ".index.lock"


def _is_pid_alive(pid: int) -> bool:
    """Check if a process is alive (Windows-specific via kernel32)."""
    try:
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    except Exception:
        # Fallback: assume alive to be safe
        return True


def _acquire_index_lock(lock_path: Path, timeout_s: int) -> bool:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.time()

    # On first attempt, check for stale lock
    if lock_path.exists():
        try:
            content = lock_path.read_text(encoding="utf-8")
            for line in content.splitlines():
                if line.startswith("pid="):
                    old_pid = int(line.split("=", 1)[1])
                    if not _is_pid_alive(old_pid):
                        logger.warning(f"Stale lock detected (pid={old_pid} not alive). Removing.")
                        lock_path.unlink(missing_ok=True)
                    break
        except Exception as e:
            logger.debug(f"Could not check stale lock: {e}")

    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(f"pid={os.getpid()}\nstarted={int(time.time())}\n")
            return True
        except FileExistsError:
            if time.time() - start > timeout_s:
                return False
            time.sleep(1)


def _release_index_lock(lock_path: Path) -> None:
    try:
        if lock_path.exists():
            lock_path.unlink()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Fingerprint
# ---------------------------------------------------------------------------


def _calculate_repo_fingerprint(
    repo_path: Path,
    include_submodules: bool,
    max_files: int = 2000,
) -> tuple[str, str]:
    """Calculate a stable fingerprint for "did repo change?".

    Prefers Git state (fast + accurate). Falls back to filesystem stat sampling.

    Returns:
        (fingerprint_hex, fingerprint_type)  where type is ``"git"`` or ``"fs"``.
    """

    def _sha16(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    def _git(args: list[str]) -> str:
        result = subprocess.run(
            ["git", "-C", str(repo_path), *args],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "git command failed")
        return result.stdout.strip()

    # -- Git fingerprint ---------------------------------------------------
    if (repo_path / ".git").exists():
        try:
            head = _git(["rev-parse", "HEAD"])
            status = _git(["status", "--porcelain"])

            parts = [f"head={head}", f"dirty={len(status.splitlines())}"]
            if status:
                parts.append("changed=" + "\n".join(status.splitlines()[:500]))

            if include_submodules:
                try:
                    sub = _git(["submodule", "status", "--recursive"])
                    if sub:
                        parts.append("submodules=" + sub)
                except Exception:
                    pass

            return _sha16("\n".join(parts)), "git"
        except Exception:
            pass

    # -- Filesystem fallback -----------------------------------------------
    max_files = int(os.getenv("FINGERPRINT_MAX_FILES", str(max_files)))
    sample_per_side = max(100, max_files // 2)

    try:
        all_files = collect_files(repo_path)
    except Exception:
        all_files = []

    file_count = len(all_files)
    if file_count <= max_files:
        sampled = all_files
    elif all_files:
        sampled = list(all_files[:sample_per_side]) + list(all_files[-sample_per_side:])
    else:
        sampled = []

    info = [f"count={file_count}"]
    for p in sampled:
        try:
            rel = p.relative_to(repo_path).as_posix()
            st = p.stat()
            info.append(f"{rel}|{st.st_size}|{int(st.st_mtime)}")
        except Exception:
            continue

    return _sha16("\n".join(info)), "fs"


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class IndexingPipeline:
    """Repository indexing pipeline (Phase 0).

    Constructor signature matches the CLI call::

        IndexingPipeline(repo_path=str(...), index_mode="auto")

    The ``kickoff(inputs=None)`` method satisfies the orchestrator Protocol.
    """

    def __init__(
        self,
        repo_path: str,
        index_mode: str = "auto",
        chroma_dir: str | None = None,
    ):
        self.config = IndexingConfig.from_env(
            repo_path=repo_path,
            index_mode=index_mode,
            chroma_dir=chroma_dir,
        )
        # Normalise mode
        if self.config.index_mode not in ("off", "auto", "smart", "force"):
            logger.warning(f"Unknown INDEX_MODE '{self.config.index_mode}', defaulting to 'auto'")
            self.config.index_mode = "auto"

        self.index_mode = self.config.index_mode
        self.repo_path = self.config.repo_path
        self.metrics = IndexingMetrics()

        # Resolve chroma dir relative to repo_path (not CWD) so the index
        # is always found regardless of where the tool is started from.
        chroma_base = self.config.chroma_dir or CHROMA_DIR
        chroma_resolved = (self.config.repo_path / chroma_base).resolve()
        self._cache_dir = chroma_resolved
        self._chroma_dir_resolved = str(chroma_resolved)

        # Lazy tool singletons
        self._discovery_tool = None
        self._reader_tool = None
        self._chunker_tool = None
        self._embeddings_tool = None
        self._chroma_tool = None

        logger.info(f"[CONFIG] IndexingPipeline INDEX_MODE={self.index_mode}")

    # -- Lazy tool accessors ------------------------------------------------

    @property
    def discovery_tool(self) -> RepoDiscoveryTool:
        if self._discovery_tool is None:
            self._discovery_tool = RepoDiscoveryTool()
        return self._discovery_tool

    @property
    def reader_tool(self) -> RepoReaderTool:
        if self._reader_tool is None:
            self._reader_tool = RepoReaderTool()
        return self._reader_tool

    @property
    def chunker_tool(self) -> ChunkerTool:
        if self._chunker_tool is None:
            self._chunker_tool = ChunkerTool()
        return self._chunker_tool

    @property
    def embeddings_tool(self) -> OllamaEmbeddingsTool:
        if self._embeddings_tool is None:
            self._embeddings_tool = OllamaEmbeddingsTool()
        return self._embeddings_tool

    @property
    def chroma_tool(self) -> ChromaIndexTool:
        if self._chroma_tool is None:
            self._chroma_tool = ChromaIndexTool(chroma_dir=self._chroma_dir_resolved)
        return self._chroma_tool

    # -- Public API ---------------------------------------------------------

    def kickoff(self, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute the indexing pipeline (orchestrator Protocol)."""
        logger.info("[START] Repository Indexing Pipeline")
        logger.info(f"[CONFIG] INDEX_MODE={self.index_mode}  repo={self.repo_path}")

        log_metric("phase_start", phase="discover", index_mode=self.index_mode)

        if self.index_mode == "off":
            logger.info("[SKIP] INDEX_MODE=off")
            log_metric("phase_complete", phase="discover", status="skipped")
            return {
                "phase": "discover",
                "status": "success",
                "message": "Skipped (INDEX_MODE=off)",
                "skipped": True,
                "index_mode": self.index_mode,
            }

        try:
            result_msg = self._run()
            skipped = result_msg.startswith("Skipped:")
            log_metric(
                "phase_complete",
                phase="discover",
                status="success",
                skipped=skipped,
                duration_seconds=round(self.metrics.duration_seconds, 2),
                chunks_indexed=self.metrics.total_chunks_indexed,
            )
            return {
                "phase": "discover",
                "status": "success",
                "repo_path": str(self.repo_path),
                "message": result_msg,
                "statistics": self.metrics.to_dict(),
                "skipped": skipped,
                "index_mode": self.index_mode,
            }
        except Exception as e:
            logger.error(f"[ERROR] Indexing failed: {e}", exc_info=True)
            log_metric("phase_failed", phase="discover", error=str(e)[:500])
            return {
                "phase": "discover",
                "status": "failed",
                "error": str(e),
                "index_mode": self.index_mode,
            }

    # -- Core pipeline logic ------------------------------------------------

    def _run(self) -> str:
        """Execute the indexing pipeline, returning a status message."""
        logger.info(f"Starting indexing pipeline for: {self.repo_path}")

        # Force mode: wipe ChromaDB first
        if self.index_mode == "force":
            self._clear_chroma()

        needs_idx, fp, fp_type, reason = self._check_needs_indexing()

        if not needs_idx:
            logger.info(f"Skipping indexing: {reason}")
            # Regenerate state file if missing (e.g. after manual deletion)
            if fp and not IndexingState.load(self._cache_dir):
                count_result = self.chroma_tool._run(
                    "count", collection_name=self.config.collection_name
                )
                chunk_count = count_result.get("count", 0)
                state = IndexingState(
                    fingerprint=fp,
                    fingerprint_type=fp_type,
                    chunk_count=chunk_count,
                    timestamp=time.time(),
                    repo_path=str(self.repo_path),
                )
                state.save(self._cache_dir)
                logger.info("[AUTO] Regenerated missing state file")
            return f"Skipped: {reason}"

        # Acquire lock (with stale-lock recovery)
        lock_path = _get_index_lock_path(self._chroma_dir_resolved)
        if not _acquire_index_lock(lock_path, self.config.lock_timeout_s):
            raise RuntimeError("Could not acquire index lock.")

        try:
            # Ensure fingerprint is available for metadata
            if not fp or not fp_type:
                fp, fp_type = _calculate_repo_fingerprint(
                    self.config.repo_path,
                    self.config.include_submodules,
                    self.config.fingerprint_max_files,
                )

            logger.info(f"STARTING INDEXING: {reason}")
            result = self._run_indexing_process(fp, fp_type)
            self.metrics.end_time = time.time()

            logger.info(f"Indexing Metrics: {self.metrics.to_dict()}")
            self._generate_indexed_files_report()

            # Persist state for future auto-mode skip
            state = IndexingState(
                fingerprint=fp,
                fingerprint_type=fp_type,
                chunk_count=self.metrics.total_chunks_indexed,
                timestamp=time.time(),
                repo_path=str(self.repo_path),
            )
            state.save(self._cache_dir)

            return result
        finally:
            _release_index_lock(lock_path)

    # -- Needs-indexing check (mode-aware) ----------------------------------

    def _check_needs_indexing(self) -> tuple[bool, str, str, str]:
        """Determine whether indexing should proceed.

        Returns:
            (needs_indexing, fingerprint, fingerprint_type, reason)
        """
        mode = self.index_mode

        # force / smart always proceed
        if mode == "force":
            return True, "", "", "Force re-index"
        if mode == "smart":
            return True, "", "", "Smart incremental update"

        # auto: check state + fingerprint + ChromaDB
        current_fp, fp_type = _calculate_repo_fingerprint(
            self.config.repo_path,
            self.config.include_submodules,
            self.config.fingerprint_max_files,
        )

        # Check persistent state first
        saved = IndexingState.load(self._cache_dir)

        # Check ChromaDB collection
        count_result = self.chroma_tool._run(
            operation="count",
            collection_name=self.config.collection_name,
        )
        doc_count = count_result.get("count", 0)
        chroma_has_data = count_result.get("success") and doc_count > 0

        if saved and saved.fingerprint == current_fp:
            if chroma_has_data:
                return False, current_fp, fp_type, f"Unchanged ({doc_count} chunks)"
            else:
                # ChromaDB was deleted but fingerprint unchanged
                logger.warning(
                    "ChromaDB missing/empty but fingerprint unchanged. "
                    "Repo has NOT changed since last successful index. "
                    "Use --index-mode force to re-index."
                )
                return (
                    False,
                    current_fp,
                    fp_type,
                    (f"Skipped: fingerprint unchanged (ChromaDB missing, last indexed {saved.chunk_count} chunks)"),
                )

        if not chroma_has_data:
            return True, current_fp, fp_type, "Collection empty or missing"

        # ChromaDB has data - check stored fingerprint in collection metadata
        meta = self.chroma_tool._get_collection_metadata(self.config.collection_name)
        stored_fp = meta.get("repo_fingerprint") or meta.get("repo_hash") or ""

        if stored_fp and current_fp != stored_fp:
            # Auto-upgrade to smart mode: only re-index changed files
            self.index_mode = "smart"
            logger.info(
                f"[AUTO->SMART] Repo changed ({stored_fp[:8]} -> {current_fp[:8]}), "
                f"switching to incremental update (only changed files)"
            )
            return True, current_fp, fp_type, f"Incremental update: {stored_fp[:8]} -> {current_fp[:8]}"

        if stored_fp and current_fp == stored_fp:
            # Metadata confirms repo unchanged — skip
            return False, current_fp, fp_type, f"Unchanged ({doc_count} chunks)"

        # No stored fingerprint in metadata (collection.modify() may have failed).
        # Check state file as fallback evidence.
        if saved and saved.fingerprint != current_fp:
            # State file says repo changed — do smart incremental update
            self.index_mode = "smart"
            logger.info(
                f"[AUTO->SMART] State file indicates change ({saved.fingerprint[:8]} -> {current_fp[:8]}), "
                f"switching to incremental update"
            )
            return True, current_fp, fp_type, f"Incremental update: {saved.fingerprint[:8]} -> {current_fp[:8]}"

        if not saved:
            # No state file, no metadata fingerprint, but ChromaDB has data.
            # Do smart incremental check to verify what's actually changed.
            self.index_mode = "smart"
            logger.info(
                "[AUTO->SMART] No state file and no metadata fingerprint, "
                "switching to incremental update to verify"
            )
            return True, current_fp, fp_type, "Incremental update (no prior state)"

        # State file fingerprint matches current, metadata has no fingerprint — skip
        return False, current_fp, fp_type, f"Unchanged ({doc_count} chunks)"

    # -- Force-mode helpers -------------------------------------------------

    def _clear_chroma(self) -> None:
        """Delete ChromaDB directory for force re-index."""
        chroma_path = Path(self._chroma_dir_resolved)
        if chroma_path.exists():
            logger.info(f"[FORCE] Clearing ChromaDB: {chroma_path}")
            try:
                shutil.rmtree(chroma_path)
                # Reset lazy tool so it re-creates the client
                self._chroma_tool = None
            except Exception as e:
                logger.error(f"[FORCE] Failed to clear ChromaDB: {e}")

    # -- Indexing process ---------------------------------------------------

    def _run_indexing_process(self, fingerprint: str, fp_type: str) -> str:
        """Run the core indexing process: Discover -> Read -> Chunk -> Embed -> Store."""
        logger.info("Step 1/5: Discovering files...")
        all_file_paths = self._discover_files()
        self.metrics.total_files_discovered = len(all_file_paths)

        estimated_s = self._estimate_duration(len(all_file_paths))
        hours, minutes = int(estimated_s // 3600), int((estimated_s % 3600) // 60)
        total_batches = (len(all_file_paths) + self.config.batch_size - 1) // self.config.batch_size
        logger.info(f"Found {len(all_file_paths)} files")
        logger.info(f"Estimated duration: {hours}h {minutes}m")
        logger.info(f"   - Batch size: {self.config.batch_size}  Total batches: {total_batches}")

        logger.info(f"Step 2-5: Processing {len(all_file_paths)} files in batches of {self.config.batch_size}...")
        self._process_batches(all_file_paths, fingerprint, fp_type)

        return f"Indexed {self.metrics.total_files_processed} files ({self.metrics.total_chunks_indexed} chunks)"

    def _discover_files(self) -> list[str]:
        discovery = self.discovery_tool._run(
            str(self.config.repo_path),
            self.config.include_submodules,
        )
        if not discovery.get("success"):
            raise RuntimeError(f"Discovery failed: {discovery.get('error')}")

        scan_paths = discovery.get("scan_paths", [])
        all_file_paths = []
        for sp in scan_paths:
            p = Path(sp).resolve()
            if p.exists():
                all_file_paths.extend([str(f) for f in collect_files(p)])

        if len(all_file_paths) > self.config.max_total_files:
            logger.warning(f"Limiting {len(all_file_paths)} files to {self.config.max_total_files}")
            all_file_paths = all_file_paths[: self.config.max_total_files]

        logger.info(f"Discovered {len(all_file_paths)} files to process")
        return all_file_paths

    def _process_batches(self, all_file_paths: list[str], fingerprint: str, fp_type: str) -> None:
        total_batches = (len(all_file_paths) + self.config.batch_size - 1) // self.config.batch_size

        for i in range(0, len(all_file_paths), self.config.batch_size):
            if self.metrics.total_chunks_indexed >= self.config.max_total_chunks:
                logger.warning(
                    f"Reached chunk limit ({self.metrics.total_chunks_indexed} >= "
                    f"{self.config.max_total_chunks}). Stopping."
                )
                break

            batch_num = (i // self.config.batch_size) + 1
            batch_paths = all_file_paths[i : i + self.config.batch_size]

            # ETA calculation
            elapsed_s = time.time() - self.metrics.start_time
            if batch_num > 1:
                avg = elapsed_s / (batch_num - 1)
                rem = (total_batches - batch_num) * avg
                eta_str = f" [ETA ~{int(rem // 3600)}h {int((rem % 3600) // 60)}m]"
            else:
                eta_str = ""

            logger.info(f"Batch {batch_num}/{total_batches}: {len(batch_paths)} files...{eta_str}")

            try:
                self._process_batch(batch_paths, fingerprint, fp_type)
                self.metrics.batches_processed += 1
            except Exception as e:
                logger.error(f"Batch {batch_num} failed: {e}")
                self.metrics.batches_failed += 1

    def _process_batch(self, batch_paths: list[str], fingerprint: str, fp_type: str) -> None:
        # Read
        read_res = self.reader_tool._run(
            str(self.config.repo_path),
            specific_files=batch_paths,
            max_file_bytes=self.config.max_file_bytes,
        )
        if read_res is None:
            raise RuntimeError("Read failed: reader tool returned None")
        if not read_res.get("success"):
            raise RuntimeError(f"Read failed: {read_res.get('error')}")

        files_batch = read_res.get("files", [])
        if not files_batch:
            return

        repo_path_str = str(self.config.repo_path)

        # Smart mode: per-file hash check (incremental)
        if self.index_mode == "smart":
            files_batch = self._filter_unchanged_files(files_batch, repo_path_str)
            if not files_batch:
                return

        self.metrics.total_files_processed += len(files_batch)

        # Chunk
        chunk_res = self.chunker_tool._run(
            files_batch,
            chunk_chars=self.config.chunk_chars,
            chunk_overlap=self.config.chunk_overlap,
        )
        if chunk_res is None:
            raise RuntimeError("Chunking failed: chunker tool returned None")
        if not chunk_res.get("success"):
            raise RuntimeError("Chunking failed")

        chunks_batch = chunk_res.get("chunks", [])
        if not chunks_batch:
            return

        self.metrics.total_chunks_created += len(chunks_batch)

        # Attach per-file metadata
        file_hash_by_path = {
            f.get("path", ""): (
                f.get("file_hash") or hashlib.sha256((f.get("content") or "").encode("utf-8")).hexdigest()
            )
            for f in files_batch
        }
        for chunk in chunks_batch:
            fp = chunk.get("file_path", "")
            chunk["file_hash"] = file_hash_by_path.get(fp, "")
            chunk["repo_path"] = repo_path_str

        # Embed
        logger.info(f"   Embedding {len(chunks_batch)} chunks...")
        texts_to_embed = [c["text"] for c in chunks_batch]
        embed_res = self.embeddings_tool._run(texts=texts_to_embed)

        if embed_res is None:
            raise RuntimeError("Embedding tool returned None")
        if not embed_res.get("success"):
            raise RuntimeError(f"Embedding failed: {embed_res.get('error')}")

        embeddings_batch = embed_res.get("embeddings", [])

        # Embedding failure monitoring
        none_count = sum(1 for e in embeddings_batch if e is None)
        if none_count > 0:
            self.metrics.total_embeddings_none += none_count
            pct = (none_count / len(embeddings_batch)) * 100
            if pct > 20:
                raise RuntimeError(
                    f"Embedding failure rate {pct:.1f}% exceeds 20% threshold "
                    f"({none_count}/{len(embeddings_batch)} None)"
                )
            if pct > 5:
                logger.warning(f"Embedding failure rate {pct:.1f}% ({none_count}/{len(embeddings_batch)} None)")

        # Store
        index_res = self.chroma_tool._run(
            "upsert",
            chunks=chunks_batch,
            embeddings=embeddings_batch,
            collection_name=self.config.collection_name,
            collection_metadata={
                "repo_fingerprint": fingerprint,
                "repo_fingerprint_type": fp_type,
                "repo_path": repo_path_str,
            },
        )
        if index_res is None:
            raise RuntimeError("Indexing failed: chroma tool returned None")
        if not index_res.get("success"):
            raise RuntimeError("Indexing failed")

        self.metrics.total_chunks_indexed += int(index_res.get("upserted_count", 0) or 0)

    # -- Smart-mode per-file filter -----------------------------------------

    def _filter_unchanged_files(self, files_batch: list[dict[str, Any]], repo_path_str: str) -> list[dict[str, Any]]:
        """Filter out files whose hash hasn't changed (smart/incremental mode)."""
        filtered: list[dict[str, Any]] = []
        for file_info in files_batch:
            file_path = file_info.get("path", "")
            content = file_info.get("content") or ""
            file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            file_info["file_hash"] = file_hash

            exists_res = self.chroma_tool._run(
                "get",
                collection_name=self.config.collection_name,
                where={
                    "repo_path": repo_path_str,
                    "file_path": file_path,
                    "file_hash": file_hash,
                },
                limit=1,
            )

            if exists_res and exists_res.get("success") and exists_res.get("count", 0) > 0:
                continue

            # Remove old chunks for this file
            self.chroma_tool._run(
                "delete",
                collection_name=self.config.collection_name,
                where={
                    "repo_path": repo_path_str,
                    "file_path": file_path,
                },
            )
            filtered.append(file_info)

        return filtered

    # -- Report generation --------------------------------------------------

    def _generate_indexed_files_report(self) -> None:
        try:
            import chromadb

            chroma_path = Path(self._chroma_dir_resolved)
            client = chromadb.PersistentClient(path=str(chroma_path))
            coll = client.get_collection(self.config.collection_name)

            results = coll.get(include=["metadatas"])
            files = set()
            repo_path = None
            for meta in results["metadatas"]:
                if meta and "file_path" in meta:
                    files.add(meta["file_path"])
                    if not repo_path and "repo_path" in meta:
                        repo_path = meta["repo_path"]

            submodules: dict[str, int] = {}
            for fp in files:
                parts = fp.replace("\\", "/").split("/")
                if parts:
                    first = parts[0]
                    submod = (
                        first
                        if first not in [".gitignore", ".env", "README.md"] and not first.startswith(".")
                        else "root"
                    )
                    submodules[submod] = submodules.get(submod, 0) + 1

            report_path = Path("indexed_files.txt")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("ChromaDB Index Report\n")
                f.write(f"Repository: {repo_path}\n")
                f.write(f"Total indexed documents (chunks): {coll.count()}\n")
                f.write(f"Total unique files: {len(files)}\n")
                f.write("=" * 60 + "\n\n")
                f.write("ALL INDEXED FILES:\n")
                f.write("-" * 60 + "\n")
                for fp in sorted(files):
                    f.write(fp + "\n")
                f.write("\n" + "=" * 60 + "\n")
                f.write("Files by Submodule:\n")
                f.write("=" * 40 + "\n")
                for name, count in sorted(submodules.items(), key=lambda x: -x[1]):
                    f.write(f"{name:30} {count:5} files\n")

            logger.info(f"Generated indexed_files.txt with {len(files)} files")
        except Exception as e:
            logger.warning(f"Could not generate indexed_files.txt: {e}")

    # -- Duration estimation ------------------------------------------------

    def _estimate_duration(self, total_files: int) -> float:
        batch_size = self.config.batch_size
        embed_delay = float(os.getenv("EMBED_DELAY_S", "0.05"))
        pause_every = int(os.getenv("EMBED_PAUSE_EVERY", "200"))
        pause_s = float(os.getenv("EMBED_PAUSE_S", "2"))

        chunks_per_file = 35
        file_io_per_batch_s = 90

        num_batches = (total_files + batch_size - 1) // batch_size
        chunks_per_batch = batch_size * chunks_per_file
        embed_time = chunks_per_batch * embed_delay
        num_pauses = max(1, chunks_per_batch // pause_every)
        time_per_batch = file_io_per_batch_s + embed_time + (num_pauses * pause_s)

        return (num_batches * time_per_batch) + 120


# ---------------------------------------------------------------------------
# Backward-compat wrapper
# ---------------------------------------------------------------------------


def ensure_repo_indexed(
    repo_path: str = None,
    force_reindex: bool = False,
) -> str:
    """Backward-compatible entry point for ``cmd_index``."""
    mode = "force" if force_reindex else "auto"
    pipeline = IndexingPipeline(repo_path=repo_path, index_mode=mode)
    result = pipeline.kickoff()
    return result.get("message", str(result))
