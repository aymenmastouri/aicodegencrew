"""
Indexing Pipeline (Phase 0)

Non-CrewAI pipeline for repository indexing.
Deterministic process - only Ollama embeddings, no LLM.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

from ...shared.utils.logger import logger
from ...shared.utils.smart_index_config import SmartIndexConfig

from .indexing_pipeline import ensure_repo_indexed, IndexingConfig, IndexingMetrics
from .chroma_index_tool import ChromaIndexTool


class IndexingPipeline:
    """
    Repository Indexing Pipeline (Phase 0)
    
    This is a PIPELINE, not a CrewAI Crew!
    No LLM needed - only Ollama embeddings.
    
    INDEX_MODE controls behavior:
    - off: Skip indexing, use existing index
    - auto: Index only if needed (default)
    - force: Clear cache and reindex from scratch
    - smart: Incremental update (changed files only)
    """
    
    def __init__(
        self,
        repo_path: str,
        chroma_db_path: Optional[str] = None,
        index_mode: str = "auto"
    ):
        """
        Initialize the indexing pipeline.
        
        Args:
            repo_path: Path to the repository to index
            chroma_db_path: Optional path to ChromaDB storage
            index_mode: Indexing mode - off/auto/force/smart
        """
        self.repo_path = Path(repo_path)
        self.chroma_db_path = chroma_db_path or os.getenv(
            'CHROMA_DB_PATH',
            str(Path.cwd() / '.cache' / '.chroma')
        )
        self.index_mode = index_mode.lower().strip()
        
        if self.index_mode not in ("off", "auto", "force", "smart"):
            logger.warning(f"[WARN] Unknown INDEX_MODE '{self.index_mode}', defaulting to 'auto'")
            self.index_mode = "auto"
        
        logger.info(f"[CONFIG] IndexingPipeline INDEX_MODE = {self.index_mode}")
        
        if self.index_mode == "force":
            self._clear_cache()
        
        self.config = SmartIndexConfig(repo_path=str(self.repo_path))
        self.chroma_tool = ChromaIndexTool(db_path=self.chroma_db_path)
        
        logger.info(f"[OK] IndexingPipeline initialized for {self.repo_path}")
    
    def _clear_cache(self):
        """Clear ChromaDB cache for force reindex."""
        chroma_path = Path(self.chroma_db_path)
        if chroma_path.exists():
            logger.info(f"[FORCE] Clearing cache: {chroma_path}")
            try:
                shutil.rmtree(chroma_path)
                logger.info("[FORCE] Cache cleared")
            except Exception as e:
                logger.error(f"[FORCE] Failed to clear cache: {e}")
    
    def kickoff(self, inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the indexing pipeline.
        
        Args:
            inputs: Optional input parameters (for orchestrator compatibility)
        
        Returns:
            Dictionary with indexing results
        """
        logger.info("[START] Repository Indexing Pipeline")
        logger.info(f"[CONFIG] INDEX_MODE = {self.index_mode}")
        logger.info(f"[CONFIG] Repository: {self.repo_path}")
        
        # Handle INDEX_MODE=off
        if self.index_mode == "off":
            logger.info("[SKIP] INDEX_MODE=off - Using existing index")
            status = self.get_index_status()
            return {
                'phase': 'phase0_indexing',
                'status': 'success',
                'message': 'Skipped (INDEX_MODE=off)',
                'statistics': status,
                'skipped': True,
                'index_mode': self.index_mode
            }
        
        try:
            force_reindex = self.index_mode == "force"
            
            # For auto mode, check if already indexed
            if self.index_mode == "auto":
                try:
                    status = self.get_index_status()
                    if status.get('indexed') and status.get('total_chunks', 0) > 0:
                        logger.info(f"[SKIP] Already indexed ({status['total_chunks']} chunks)")
                        return {
                            'phase': 'phase0_indexing',
                            'status': 'success',
                            'message': 'Already indexed (INDEX_MODE=auto)',
                            'statistics': status,
                            'skipped': True,
                            'index_mode': self.index_mode
                        }
                except:
                    pass
            
            # Perform indexing
            logger.info(f"[INDEX] Running (force={force_reindex})")
            stats = ensure_repo_indexed(str(self.repo_path), force_reindex=force_reindex)
            
            return {
                'phase': 'phase0_indexing',
                'status': 'success',
                'repo_path': str(self.repo_path),
                'chroma_db_path': self.chroma_db_path,
                'statistics': stats,
                'message': f'Indexed successfully (INDEX_MODE={self.index_mode})',
                'skipped': False,
                'index_mode': self.index_mode
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Indexing failed: {e}")
            return {
                'phase': 'phase0_indexing',
                'status': 'failed',
                'error': str(e),
                'index_mode': self.index_mode
            }
    
    def get_index_status(self) -> Dict[str, Any]:
        """Check current indexing status."""
        try:
            info = self.chroma_tool.get_collection_info('repo_docs')
            return {
                'indexed': True,
                'collection': 'repo_docs',
                'total_chunks': info.get('count', 0),
                'repo_path': str(self.repo_path)
            }
        except:
            return {'indexed': False, 'repo_path': str(self.repo_path)}


__all__ = [
    "IndexingPipeline",
    "ensure_repo_indexed",
    "IndexingConfig",
    "IndexingMetrics",
]
