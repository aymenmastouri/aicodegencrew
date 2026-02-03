"""One-time indexing pipeline to be run before Crew starts.

Best Practices:
- Class-based architecture for better testability
- Metrics tracking for observability
- Batch processing for memory efficiency
- Lock mechanism for concurrent safety
- Fingerprinting for smart re-indexing
"""

import os
import hashlib
import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from ...shared.utils.logger import setup_logger
from .repo_discovery_tool import RepoDiscoveryTool
from .repo_reader_tool import RepoReaderTool
from .chunker_tool import ChunkerTool
from .embeddings_tool import OllamaEmbeddingsTool
from .chroma_index_tool import ChromaIndexTool
from ...shared.utils.file_filters import collect_files

logger = setup_logger(__name__)


@dataclass
class IndexingConfig:
    """Configuration for indexing pipeline."""
    repo_path: Path
    collection_name: str = "repo_docs"
    include_submodules: bool = True
    force_reindex: bool = False
    incremental: bool = True
    batch_size: int = 50  # Continue-style: larger batches work fine
    max_total_files: int = 8000  # Index full repos
    max_total_chunks: int = 50000
    chunk_chars: int = 1800
    chunk_overlap: int = 200
    max_file_bytes: int = 2000000
    lock_timeout_s: int = 300
    fingerprint_max_files: int = 2000

    @classmethod
    def from_env(cls, repo_path: str = None) -> 'IndexingConfig':
        """Create config from environment variables."""
        if repo_path is None:
            repo_path = os.getenv("PROJECT_PATH") or os.getenv("REPO_PATH")
        if not repo_path:
            raise ValueError("No repository path specified.")
        
        resolved_path = Path(repo_path).resolve()
        if not resolved_path.exists():
            raise ValueError(f"Repo path not found: {resolved_path}")
        
        return cls(
            repo_path=resolved_path,
            collection_name=os.getenv("COLLECTION_NAME", "repo_docs"),
            include_submodules=os.getenv("INCLUDE_SUBMODULES", "true").lower() == "true",
            force_reindex=os.getenv("FORCE_REINDEX", "0") == "1",
            incremental=os.getenv("INDEX_INCREMENTAL", "true").lower() in {"1", "true", "yes", "y", "on"},
            batch_size=int(os.getenv("INDEX_BATCH_SIZE", "50")),
            max_total_files=int(os.getenv("INDEX_MAX_TOTAL_FILES", "8000")),
            max_total_chunks=int(os.getenv("INDEX_MAX_TOTAL_CHUNKS", "50000")),
            chunk_chars=int(os.getenv("CHUNK_CHARS", "1800")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
            max_file_bytes=int(os.getenv("MAX_FILE_BYTES", "2000000")),
            lock_timeout_s=int(os.getenv("INDEX_LOCK_TIMEOUT_S", "300")),
            fingerprint_max_files=int(os.getenv("FINGERPRINT_MAX_FILES", "2000")),
        )


@dataclass
class IndexingMetrics:
    """Metrics for indexing operation."""
    total_files_discovered: int = 0
    total_files_processed: int = 0
    total_chunks_created: int = 0
    total_chunks_indexed: int = 0
    batches_processed: int = 0
    batches_failed: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        end = self.end_time or time.time()
        return end - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_files_discovered": self.total_files_discovered,
            "total_files_processed": self.total_files_processed,
            "total_chunks_created": self.total_chunks_created,
            "total_chunks_indexed": self.total_chunks_indexed,
            "batches_processed": self.batches_processed,
            "batches_failed": self.batches_failed,
            "duration_seconds": self.duration_seconds,
            "chunks_per_second": self.total_chunks_indexed / self.duration_seconds if self.duration_seconds > 0 else 0,
        }


def _get_index_lock_path() -> Path:
    chroma_dir = os.getenv("CHROMA_DIR", "./.chroma_db")
    return Path(chroma_dir).resolve() / ".index.lock"


def _acquire_index_lock(lock_path: Path, timeout_s: int) -> bool:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.time()
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


class IndexingPipeline:
    """Manages the complete indexing pipeline with metrics and monitoring."""
    
    def __init__(self, config: IndexingConfig):
        """Initialize pipeline with configuration.
        
        Args:
            config: Indexing configuration
        """
        self.config = config
        self.metrics = IndexingMetrics()
        
        # Initialize tools lazily
        self._discovery_tool = None
        self._reader_tool = None
        self._chunker_tool = None
        self._embeddings_tool = None
        self._chroma_tool = None
    
    @property
    def discovery_tool(self) -> RepoDiscoveryTool:
        """Lazy initialization of discovery tool."""
        if self._discovery_tool is None:
            self._discovery_tool = RepoDiscoveryTool()
        return self._discovery_tool
    
    @property
    def reader_tool(self) -> RepoReaderTool:
        """Lazy initialization of reader tool."""
        if self._reader_tool is None:
            self._reader_tool = RepoReaderTool()
        return self._reader_tool
    
    @property
    def chunker_tool(self) -> ChunkerTool:
        """Lazy initialization of chunker tool."""
        if self._chunker_tool is None:
            self._chunker_tool = ChunkerTool()
        return self._chunker_tool
    
    @property
    def embeddings_tool(self) -> OllamaEmbeddingsTool:
        """Lazy initialization of embeddings tool."""
        if self._embeddings_tool is None:
            self._embeddings_tool = OllamaEmbeddingsTool()
        return self._embeddings_tool
    
    @property
    def chroma_tool(self) -> ChromaIndexTool:
        """Lazy initialization of chroma tool."""
        if self._chroma_tool is None:
            self._chroma_tool = ChromaIndexTool()
        return self._chroma_tool
    
    def run(self) -> str:
        """Execute the complete indexing pipeline.
        
        Returns:
            Status message
        """
        logger.info(f"Starting indexing pipeline for: {self.config.repo_path}")
        
        # Check if indexing needed
        needs_idx, fp, fp_type, reason = self._check_needs_indexing()
        
        if not needs_idx:
            logger.info(f"Skipping indexing: {reason}")
            return f"Skipped: {reason}"
        
        # Acquire lock
        lock_path = _get_index_lock_path()
        if not _acquire_index_lock(lock_path, self.config.lock_timeout_s):
            raise RuntimeError("Could not acquire index lock.")
        
        try:
            # Always compute a fingerprint for metadata, even when forcing reindexing
            # or starting from an empty/missing collection.
            if not fp or not fp_type:
                fp, fp_type = _calculate_repo_fingerprint(
                    self.config.repo_path,
                    self.config.include_submodules,
                    self.config.fingerprint_max_files,
                )

            # Repo-scoped cache reset: on FORCE_REINDEX, delete only this repo's chunks.
            if self.config.force_reindex:
                self._wipe_repo_index()

            logger.info(f"STARTING INDEXING: {reason}")
            result = self._run_indexing_process(fp, fp_type)
            self.metrics.end_time = time.time()
            
            # Log metrics
            logger.info(f"Indexing Metrics: {self.metrics.to_dict()}")
            
            # Generate indexed files report
            self._generate_indexed_files_report()
            
            return result
        finally:
            _release_index_lock(lock_path)

    def _generate_indexed_files_report(self) -> None:
        """Generate indexed_files.txt report with all indexed files and submodule summary.
        
        This report is regenerated after each indexing run for documentation.
        """
        try:
            import chromadb
            chroma_path = Path(os.getenv("CHROMA_PERSIST_DIR", ".cache/.chroma"))
            client = chromadb.PersistentClient(path=str(chroma_path))
            coll = client.get_collection(self.config.collection_name)
            
            # Get all unique source files
            results = coll.get(include=['metadatas'])
            files = set()
            repo_path = None
            for meta in results['metadatas']:
                if meta and 'file_path' in meta:
                    files.add(meta['file_path'])
                    if not repo_path and 'repo_path' in meta:
                        repo_path = meta['repo_path']
            
            # Count by submodule
            submodules = {}
            for fp in files:
                parts = fp.replace('\\', '/').split('/')
                if len(parts) > 0:
                    first = parts[0]
                    submod = first if first not in ['.gitignore', '.env', 'README.md'] and not first.startswith('.') else 'root'
                    submodules[submod] = submodules.get(submod, 0) + 1
            
            # Write report
            report_path = Path("indexed_files.txt")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write('ChromaDB Index Report\n')
                f.write(f'Repository: {repo_path}\n')
                f.write(f'Total indexed documents (chunks): {coll.count()}\n')
                f.write(f'Total unique files: {len(files)}\n')
                f.write('=' * 60 + '\n\n')
                
                # All files
                f.write('ALL INDEXED FILES:\n')
                f.write('-' * 60 + '\n')
                for fp in sorted(files):
                    f.write(fp + '\n')
                
                # Summary at end
                f.write('\n' + '=' * 60 + '\n')
                f.write('Files by Submodule:\n')
                f.write('=' * 40 + '\n')
                for name, count in sorted(submodules.items(), key=lambda x: -x[1]):
                    f.write(f'{name:30} {count:5} files\n')
            
            logger.info(f"Generated indexed_files.txt with {len(files)} files")
        except Exception as e:
            logger.warning(f"Could not generate indexed_files.txt: {e}")
    
    def _wipe_repo_index(self) -> None:
        """Delete all indexed chunks for the configured repo_path (best-effort).

        This provides a clean re-index experience without deleting other repos
        that might share the same collection.
        """
        repo_path_str = str(self.config.repo_path)
        logger.warning(
            f"FORCE_REINDEX=1 -> deleting existing index entries for repo_path={repo_path_str}"
        )
        try:
            self.chroma_tool._run(
                "delete",
                collection_name=self.config.collection_name,
                where={"repo_path": repo_path_str},
            )
        except Exception as e:
            # Best-effort only: if deletion fails, indexing can still proceed.
            logger.error(f"Failed to wipe repo index for {repo_path_str}: {e}")
    
    def _check_needs_indexing(self) -> Tuple[bool, str, str, str]:
        """Check if repository needs indexing.
        
        Returns:
            (needs_indexing, fingerprint, fingerprint_type, reason)
        """
        if self.config.force_reindex:
            return True, "", "", "Force re-index"
        
        # Check if collection empty
        count_result = self.chroma_tool._run(
            operation="count",
            collection_name=self.config.collection_name
        )
        doc_count = count_result.get("count", 0)
        
        if not count_result.get("success") or doc_count == 0:
            return True, "", "", "Collection empty or missing"
        
        # Check fingerprint
        logger.info("Checking for repository changes...")
        current_fp, fp_type = _calculate_repo_fingerprint(
            self.config.repo_path,
            self.config.include_submodules,
            self.config.fingerprint_max_files
        )
        
        meta = self.chroma_tool._get_collection_metadata(self.config.collection_name)
        stored_fp = meta.get("repo_fingerprint") or meta.get("repo_hash") or ""
        
        if stored_fp and current_fp != stored_fp:
            return True, current_fp, fp_type, f"Changed: {stored_fp[:8]} -> {current_fp[:8]}"
        
        return False, current_fp, fp_type, f"Unchanged ({doc_count} chunks)"
    
    def _run_indexing_process(self, fingerprint: str, fp_type: str) -> str:
        """Run the core indexing process.
        
        Args:
            fingerprint: Repository fingerprint
            fp_type: Fingerprint type (git or fs)
            
        Returns:
            Status message
        """
        # Step 1: Discover files
        logger.info("Step 1/5: Discovering files...")
        all_file_paths = self._discover_files()
        self.metrics.total_files_discovered = len(all_file_paths)
        
        # Calculate and log estimated duration
        estimated_duration_s = self._estimate_duration(len(all_file_paths))
        hours = estimated_duration_s // 3600
        minutes = (estimated_duration_s % 3600) // 60
        logger.info(f"Found {len(all_file_paths)} files")
        logger.info(f"Estimated duration: {int(hours)}h {int(minutes)}m (with current config)")
        logger.info(f"   - Batch size: {self.config.batch_size} files")
        logger.info(f"   - Total batches: {(len(all_file_paths) + self.config.batch_size - 1) // self.config.batch_size}")
        logger.info(f"   - Embed delay: {self._get_embed_delay():.2f}s")
        logger.info(f"   - Pause every: {self._get_pause_every()} embeddings")
        
        # Step 2-5: Process in batches
        logger.info(f"Step 2-5: Processing {len(all_file_paths)} files in batches of {self.config.batch_size}...")
        self._process_batches(all_file_paths, fingerprint, fp_type)
        
        return f"Indexed {self.metrics.total_files_processed} files ({self.metrics.total_chunks_indexed} chunks)"
    
    def _discover_files(self) -> List[str]:
        """Discover all files to index.
        
        Returns:
            List of file paths
        """
        discovery = self.discovery_tool._run(
            str(self.config.repo_path),
            self.config.include_submodules
        )
        
        if not discovery.get("success"):
            raise RuntimeError(f"Discovery failed: {discovery.get('error')}")
        
        scan_paths = discovery.get("scan_paths", [])
        all_file_paths = []
        
        for sp in scan_paths:
            p = Path(sp).resolve()
            if p.exists():
                all_file_paths.extend([str(f) for f in collect_files(p)])
        
        # Apply file limit
        if len(all_file_paths) > self.config.max_total_files:
            logger.warning(
                f"Limiting {len(all_file_paths)} files to {self.config.max_total_files}"
            )
            all_file_paths = all_file_paths[:self.config.max_total_files]
        
        logger.info(f"Discovered {len(all_file_paths)} files to process")
        return all_file_paths
    
    def _process_batches(self, all_file_paths: List[str], fingerprint: str, fp_type: str) -> None:
        """Process files in batches.
        
        Args:
            all_file_paths: List of file paths to process
            fingerprint: Repository fingerprint
            fp_type: Fingerprint type
        """
        total_batches = (len(all_file_paths) + self.config.batch_size - 1) // self.config.batch_size
        
        for i in range(0, len(all_file_paths), self.config.batch_size):
            if self.metrics.total_chunks_indexed >= self.config.max_total_chunks:
                logger.warning(
                    f"Reached chunk limit ({self.metrics.total_chunks_indexed} >= "
                    f"{self.config.max_total_chunks}). Stopping."
                )
                break
            
            batch_num = (i // self.config.batch_size) + 1
            batch_paths = all_file_paths[i:i + self.config.batch_size]
            
            # Calculate progress and remaining time
            elapsed_s = time.time() - self.metrics.start_time
            batches_remaining = total_batches - batch_num
            if batch_num > 1:
                avg_batch_time = elapsed_s / (batch_num - 1)
                estimated_remaining_s = batches_remaining * avg_batch_time
                remaining_h = estimated_remaining_s // 3600
                remaining_m = (estimated_remaining_s % 3600) // 60
                eta_str = f" [ETA ~{int(remaining_h)}h {int(remaining_m)}m]"
            else:
                eta_str = ""
            
            logger.info(f"Batch {batch_num}/{total_batches}: Processing {len(batch_paths)} files...{eta_str}")
            
            try:
                self._process_batch(batch_paths, fingerprint, fp_type)
                self.metrics.batches_processed += 1
            except Exception as e:
                logger.error(f"Batch {batch_num} failed: {str(e)}")
                self.metrics.batches_failed += 1
    
    def _process_batch(self, batch_paths: List[str], fingerprint: str, fp_type: str) -> None:
        """Process a single batch of files.
        
        Args:
            batch_paths: File paths in this batch
            fingerprint: Repository fingerprint
            fp_type: Fingerprint type
        """
        # Read files
        read_res = self.reader_tool._run(
            str(self.config.repo_path),
            specific_files=batch_paths,
            max_file_bytes=self.config.max_file_bytes
        )
        
        if read_res is None:
            raise RuntimeError("Read failed: reader tool returned None")
        if not read_res.get("success"):
            raise RuntimeError(f"Read failed: {read_res.get('error')}")
        
        files_batch = read_res.get("files", [])
        if not files_batch:
            return

        repo_path_str = str(self.config.repo_path)

        # Incremental indexing (Continue-style): only embed files that are new/changed.
        # We store file_hash and repo_path in Chroma metadata so we can cheaply check.
        if self.config.incremental and not self.config.force_reindex:
            filtered_files: List[Dict[str, Any]] = []
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

                # File is new/changed: remove previous chunks for that file (best-effort).
                self.chroma_tool._run(
                    "delete",
                    collection_name=self.config.collection_name,
                    where={
                        "repo_path": repo_path_str,
                        "file_path": file_path,
                    },
                )
                filtered_files.append(file_info)

            files_batch = filtered_files

        if not files_batch:
            return
        
        self.metrics.total_files_processed += len(files_batch)
        
        # Chunk files
        chunk_res = self.chunker_tool._run(
            files_batch,
            chunk_chars=self.config.chunk_chars,
            chunk_overlap=self.config.chunk_overlap
        )
        
        if chunk_res is None:
            raise RuntimeError("Chunking failed: chunker tool returned None")
        if not chunk_res.get("success"):
            raise RuntimeError("Chunking failed")
        
        chunks_batch = chunk_res.get("chunks", [])
        if not chunks_batch:
            return
        
        self.metrics.total_chunks_created += len(chunks_batch)

        # Attach per-file metadata to each chunk for incremental indexing.
        file_hash_by_path = {
            f.get("path", ""): (f.get("file_hash") or hashlib.sha256((f.get("content") or "").encode("utf-8")).hexdigest())
            for f in files_batch
        }
        for chunk in chunks_batch:
            fp = chunk.get("file_path", "")
            chunk["file_hash"] = file_hash_by_path.get(fp, "")
            chunk["repo_path"] = repo_path_str
        
        # Embed chunks
        logger.info(f"   Embedding {len(chunks_batch)} chunks...")
        try:
            texts_to_embed = [c["text"] for c in chunks_batch]
            logger.debug(f"Calling embeddings tool with {len(texts_to_embed)} texts...")
            embed_res = self.embeddings_tool._run(texts=texts_to_embed)
            logger.debug(f"Embeddings tool returned: {type(embed_res)} = {str(embed_res)[:200] if embed_res else 'None'}")
            
            if embed_res is None:
                raise RuntimeError("Embedding tool returned None")
            
            if not embed_res.get("success"):
                raise RuntimeError(f"Embedding failed: {embed_res.get('error')}")
            
            embeddings_batch = embed_res.get("embeddings", [])
        except Exception as e:
            logger.error(f"Embedding error: {e}", exc_info=True)
            raise
        
        # Store in ChromaDB
        index_res = self.chroma_tool._run(
            "upsert",
            chunks=chunks_batch,
            embeddings=embeddings_batch,
            collection_name=self.config.collection_name,
            collection_metadata={
                "repo_fingerprint": fingerprint,
                "repo_fingerprint_type": fp_type,
                "repo_path": str(self.config.repo_path)
            }
        )
        
        if index_res is None:
            raise RuntimeError("Indexing failed: chroma tool returned None")
        if not index_res.get("success"):
            raise RuntimeError("Indexing failed")
        
        self.metrics.total_chunks_indexed += int(index_res.get("upserted_count", 0) or 0)

    def _get_embed_delay(self) -> float:
        """Get current embedding delay from environment."""
        return float(os.getenv("EMBED_DELAY_S", "0.05"))
    
    def _get_pause_every(self) -> int:
        """Get pause frequency from environment."""
        return int(os.getenv("EMBED_PAUSE_EVERY", "200"))
    
    def _estimate_duration(self, total_files: int) -> float:
        """Estimate total indexing duration in seconds.
        
        Args:
            total_files: Total files to index
            
        Returns:
            Estimated duration in seconds
        """
        # Configuration
        batch_size = self.config.batch_size
        embed_delay = self._get_embed_delay()
        pause_every = self._get_pause_every()
        pause_s = float(os.getenv("EMBED_PAUSE_S", "2"))
        
        # Estimates (conservative)
        chunks_per_file = 35  # Average chunks from 1800-char files
        file_io_per_batch_s = 90  # Read + chunk 30 files
        
        num_batches = (total_files + batch_size - 1) // batch_size
        
        # Calculate embedding time per batch
        chunks_per_batch = batch_size * chunks_per_file
        embed_time_per_batch = chunks_per_batch * embed_delay
        
        # Add pause time (every N embeddings)
        num_pauses_per_batch = max(1, chunks_per_batch // pause_every)
        pause_time_per_batch = num_pauses_per_batch * pause_s
        
        time_per_batch = file_io_per_batch_s + embed_time_per_batch + pause_time_per_batch
        
        total_s = (num_batches * time_per_batch) + 120  # +2min for discovery/indexing overhead
        
        return total_s


def _calculate_repo_fingerprint(
    repo_path: Path,
    include_submodules: bool,
    max_files: int = 2000
) -> Tuple[str, str]:
    """Calculate a stable fingerprint for "did repo change?".

    Best practice is to use Git state when available (fast + accurate).
    Fallback: filesystem stat sampling of included files (size + mtime).

    Returns:
        (fingerprint, fingerprint_type)
        fingerprint_type is "git" or "fs".
    """

    def _sha16(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    def _git(args: List[str]) -> str:
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

    # Prefer Git fingerprint when possible
    if (repo_path / ".git").exists():
        try:
            head = _git(["rev-parse", "HEAD"])
            status = _git(["status", "--porcelain"])

            parts = [f"head={head}", f"dirty={len(status.splitlines())}"]
            # Include filenames so changes outside "first N" still influence fingerprint.
            if status:
                parts.append("changed=" + "\n".join(status.splitlines()[:500]))

            if include_submodules:
                try:
                    sub = _git(["submodule", "status", "--recursive"])
                    if sub:
                        parts.append("submodules=" + sub)
                except Exception:
                    # Submodules may not be initialized; treat as no submodule info.
                    pass

            raw = "\n".join(parts)
            return _sha16(raw), "git"
        except Exception:
            pass

    # Filesystem fallback
    max_files = int(os.getenv("FINGERPRINT_MAX_FILES", "2000"))
    sample_per_side = max(100, max_files // 2)

    try:
        all_files = collect_files(repo_path)
    except Exception:
        all_files = []

    file_count = len(all_files)
    sampled = []
    if all_files:
        if file_count <= max_files:
            sampled = all_files
        else:
            sampled = list(all_files[:sample_per_side]) + list(all_files[-sample_per_side:])

    info = [f"count={file_count}"]
    for p in sampled:
        try:
            rel = p.relative_to(repo_path).as_posix()
            st = p.stat()
            info.append(f"{rel}|{st.st_size}|{int(st.st_mtime)}")
        except Exception:
            continue

    return _sha16("\n".join(info)), "fs"


def _check_needs_indexing(
    repo_path: Path,
    include_submodules: bool,
    force_reindex: bool,
    chroma_tool: ChromaIndexTool,
    collection_name: str
) -> Tuple[bool, str, str, str]:
    """Check if repository needs indexing based on fingerprint."""
    if force_reindex:
        return True, "", "", "Force re-index"

    # Check if collection is empty
    count_result = chroma_tool._run(operation="count", collection_name=collection_name)
    doc_count = count_result.get("count", 0)
    if not count_result.get("success") or doc_count == 0:
        return True, "", "", "Collection empty or missing"

    # Check fingerprint
    logger.info("Checking for repository changes...")
    discovery_tool = RepoDiscoveryTool()
    if not discovery_tool._run(repo_path=str(repo_path), include_submodules=include_submodules).get("success"):
        logger.warning("Could not check for repository changes - skipping check")
        return False, "", "", "Discovery failed" # Fail safe: don't reindex if check fails? Or should we?

    current_fp, fp_type = _calculate_repo_fingerprint(repo_path, include_submodules)
    meta = chroma_tool._get_collection_metadata(collection_name)
    stored_fp = meta.get("repo_fingerprint") or meta.get("repo_hash") or ""
    
    if stored_fp and current_fp != stored_fp:
        return True, current_fp, fp_type, f"Changed: {stored_fp[:8]} -> {current_fp[:8]}"
    
    return False, current_fp, fp_type, f"Unchanged ({doc_count} chunks)"


def _run_indexing_process(repo_path: Path, include_submodules: bool, collection_name: str, fingerprint: str, fp_type: str) -> str:
    """Run the core indexing steps: Discovery -> Read -> Chunk -> Embed -> Store (Batched)."""
    logger.info(f"Starting repository indexing for: {repo_path}")
    
    # Init tools
    reader_tool = RepoReaderTool()
    chunker_tool = ChunkerTool()
    embeddings_tool = OllamaEmbeddingsTool()
    chroma_tool = ChromaIndexTool()
        
    # Step 1: Discover all files first (low memory)
    logger.info("Step 1/5: Discovering structure...")
    discovery = RepoDiscoveryTool()._run(str(repo_path), include_submodules)
    if not discovery.get("success"): raise RuntimeError(f"Discovery failed: {discovery.get('error')}")
    scan_paths = discovery.get("scan_paths", [])

    all_file_paths = []
    for sp in scan_paths:
        p = Path(sp).resolve()
        if p.exists():
            all_file_paths.extend([str(f) for f in collect_files(p)])
    
    # Limit files globally if needed
    max_files = int(os.getenv("INDEX_MAX_TOTAL_FILES", "2000"))
    if len(all_file_paths) > max_files:
        logger.warning(f"Optimization: Limiting {len(all_file_paths)} files to {max_files}")
        all_file_paths = all_file_paths[:max_files]
    
    logger.info(f"Discovered {len(all_file_paths)} files to process")

    # Batched processing configuration
    BATCH_SIZE = int(os.getenv("INDEX_BATCH_SIZE", "50"))
    MAX_TOTAL_CHUNKS = int(os.getenv("INDEX_MAX_TOTAL_CHUNKS", "20000"))
    total_chunks_indexed = 0

    # Step 2-5: Process in batches
    logger.info(f"Step 2-5: Processing in batches of {BATCH_SIZE} files...")
    
    for i in range(0, len(all_file_paths), BATCH_SIZE):
        if total_chunks_indexed >= MAX_TOTAL_CHUNKS:
            logger.warning(f"Reached chunk limit ({total_chunks_indexed} >= {MAX_TOTAL_CHUNKS}). Stopping indexing.")
            break
            
        batch_paths = all_file_paths[i:i + BATCH_SIZE]
        current_batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(all_file_paths) + BATCH_SIZE - 1) // BATCH_SIZE
        
        logger.info(f"[BATCH] Batch {current_batch_num}/{total_batches}: Processing {len(batch_paths)} files...")

        # 2. Read Batch
        read_res = reader_tool._run(
            str(repo_path), 
            specific_files=batch_paths,
            max_file_bytes=int(os.getenv("MAX_FILE_BYTES", "2000000"))
        )
        if not read_res.get("success"): 
            logger.error(f"Batch {current_batch_num} read failed: {read_res.get('error')}")
            continue
        
        files_batch = read_res.get("files", [])
        if not files_batch:
            continue

        # 3. Chunk Batch
        chunk_res = chunker_tool._run(
            files_batch, 
            chunk_chars=int(os.getenv("CHUNK_CHARS", "1800")), 
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200"))
        )
        if not chunk_res.get("success"):
            logger.error(f"Batch {current_batch_num} chunk failed")
            continue
        
        chunks_batch = chunk_res.get("chunks", [])
        if not chunks_batch:
            continue

        # 4. Embed Batch
        logger.info(f"   Embedding {len(chunks_batch)} chunks...")
        embed_res = embeddings_tool._run([c["text"] for c in chunks_batch])
        if not embed_res.get("success"):
            logger.error(f"Batch {current_batch_num} embed failed")
            continue
            
        embeddings_batch = embed_res.get("embeddings", [])

        # 5. Store Batch
        index_res = chroma_tool._run(
            "upsert", 
            chunks=chunks_batch, 
            embeddings=embeddings_batch, 
            collection_name=collection_name,
            collection_metadata={
                "repo_fingerprint": fingerprint, 
                "repo_fingerprint_type": fp_type,
                "repo_path": str(repo_path)
            }
        )
        if not index_res.get("success"):
            logger.error(f"Batch {current_batch_num} index failed")
        else:
            total_chunks_indexed += len(chunks_batch)

    return f"Indexed {len(all_file_paths)} files ({total_chunks_indexed} chunks) in batches"


def ensure_repo_indexed(
    repo_path: str = None,
    force_reindex: bool = None,
    include_submodules: bool = None,
) -> str:
    """Ensure repository is indexed in ChromaDB.
    
    This is the main public API for the indexing pipeline.
    Uses the new class-based architecture with metrics tracking.
    
    Args:
        repo_path: Path to repository (defaults to env vars)
        force_reindex: Force re-indexing even if up-to-date
        include_submodules: Include git submodules in indexing
        
    Returns:
        Status message
        
    Example:
        >>> result = ensure_repo_indexed("/path/to/repo")
        >>> print(result)  # "Indexed 150 files (2500 chunks)"
    """
    try:
        # Create configuration from environment or parameters
        config = IndexingConfig.from_env(repo_path)
        
        # Override with explicit parameters
        if force_reindex is not None:
            config.force_reindex = force_reindex
        if include_submodules is not None:
            config.include_submodules = include_submodules
        
        # Create and run pipeline
        pipeline = IndexingPipeline(config)
        result = pipeline.run()
        
        # Log final metrics
        if pipeline.metrics.end_time:
            logger.info(
                f"Final Metrics: {pipeline.metrics.total_files_processed} files, "
                f"{pipeline.metrics.total_chunks_indexed} chunks in "
                f"{pipeline.metrics.duration_seconds:.1f}s "
                f"({pipeline.metrics.total_chunks_indexed / pipeline.metrics.duration_seconds:.1f} chunks/s)"
            )
        
        print(f"OK: {result}")
        return result
        
    except Exception as e:
        error_msg = f"Indexing failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(f"ERROR: {error_msg}")
        raise
