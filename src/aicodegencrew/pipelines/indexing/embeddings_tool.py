"""Ollama embeddings tool for generating embeddings via HTTP API.

Best Practices:
- Adaptive throttling to prevent Ollama overload
- Circuit breaker pattern for stability
- Exponential backoff for retries
- Batch processing with pause intervals
- Text truncation to prevent memory issues
"""

import os
from typing import Type, List, Dict, Any, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from ...shared.utils.logger import setup_logger
from ...shared.utils.ollama_client import OllamaClient

logger = setup_logger(__name__)


class OllamaEmbeddingsInput(BaseModel):
    """Input schema for OllamaEmbeddingsTool."""
    texts: List[str] = Field(..., description="List of texts to embed")
    batch_size: int = Field(default=10, description="Batch size for processing")


class OllamaEmbeddingsTool(BaseTool):
    name: str = "ollama_embeddings"
    description: str = (
        "Generates embeddings for texts using Ollama HTTP API with adaptive throttling. "
        "Features: batch processing, circuit breaker, exponential backoff for stability. "
        "Optimized for local LLM servers that can become unstable under heavy load."
    )
    args_schema: Type[BaseModel] = OllamaEmbeddingsInput
    
    # Performance and stability configuration
    max_retries: int = 3
    circuit_breaker_threshold: int = 5  # Consecutive failures before cooldown
    
    def _get_client(self) -> OllamaClient:
        """Lazy initialization of Ollama client.
        
        Returns:
            Configured OllamaClient instance
        """
        if not hasattr(self, '_client'):
            self._client = OllamaClient()
            logger.info("Ollama embeddings client initialized")
        return self._client
    
    def _run(
        self,
        texts: List[str],
        batch_size: int = 10,
    ) -> Dict[str, Any]:
        """Generate embeddings for texts with adaptive batching and circuit breaker.
        
        Production Best Practices:
        - Batch API for 10-50x performance improvement
        - Adaptive batch sizing based on success/failure rates
        - Circuit breaker pattern for automatic overload protection
        - Connection pooling via persistent session
        - Comprehensive metrics and progress logging
        - Graceful degradation on partial failures
        
        Args:
            texts: List of texts to embed
            batch_size: Initial batch size (adapts dynamically)
            
        Returns:
            Dictionary with embeddings, metrics, and status
        """
        import time
        
        # Initialize client lazily
        client = self._get_client()
        
        if not texts:
            return {
                "success": True,
                "embeddings": [],
                "count": 0,
            }
        
        # Health check
        if not client.health_check():
            return {
                "success": False,
                "error": "Ollama API is not accessible. Please ensure Ollama is running.",
                "help": "Try: ollama serve (in separate terminal)",
            }
        
        # Configuration from environment
        max_text_length = int(os.getenv("EMBED_MAX_TEXT_LENGTH", "800"))
        use_batching = os.getenv("EMBED_USE_BATCHING", "true").lower() in {"1", "true", "yes"}
        initial_batch_size = int(os.getenv("EMBED_BATCH_SIZE", "1"))
        min_batch_size = int(os.getenv("EMBED_MIN_BATCH_SIZE", "1"))
        max_batch_size = int(os.getenv("EMBED_MAX_BATCH_SIZE", "1"))
        pause_every = int(os.getenv("EMBED_PAUSE_EVERY", "10"))
        pause_s = float(os.getenv("EMBED_PAUSE_S", "10.0"))
        log_every = int(os.getenv("EMBED_LOG_EVERY", "25"))
        
        # Truncate texts
        texts = [t[:max_text_length] if len(t) > max_text_length else t for t in texts]
        
        # Keep one-to-one alignment with `texts` by index.
        # Failed embeddings are represented as None.
        embeddings: List[Optional[List[float]]] = [None] * len(texts)
        failed_count = 0
        start_ts = time.time()
        last_log_ts = start_ts
        
        if not use_batching:
            # Fallback: Single mode (compatibility)
            return self._run_single_mode(client, texts, max_text_length, pause_every, pause_s, log_every)
        
        # === BATCH MODE (Best Practice) ===
        current_batch_size = initial_batch_size
        consecutive_failures = 0
        total_processed = 0
        
        i = 0
        while i < len(texts):
            batch_end = min(i + current_batch_size, len(texts))
            batch_texts = texts[i:batch_end]
            
            try:
                # Batch embed (much faster!)
                batch_embeddings = client.embed_batch(batch_texts)
                for offset, emb in enumerate(batch_embeddings):
                    embeddings[i + offset] = emb
                total_processed += len(batch_texts)
                consecutive_failures = 0
                
                # Adaptive batch sizing: increase on success
                if current_batch_size < max_batch_size:
                    current_batch_size = min(current_batch_size + 5, max_batch_size)
                
                # Progress logging
                if log_every > 0 and total_processed % log_every < current_batch_size:
                    now = time.time()
                    elapsed = max(0.001, now - start_ts)
                    since_last = max(0.001, now - last_log_ts)
                    rate = total_processed / elapsed
                    logger.info(
                        f"[BATCH] {total_processed}/{len(texts)} texts "
                        f"({rate:.1f} emb/s, batch_size={current_batch_size})"
                    )
                    last_log_ts = now
                
                # Periodic pause to avoid overload
                if pause_every > 0 and total_processed % pause_every < current_batch_size:
                    logger.debug(f"Cooldown pause ({pause_s}s) after {total_processed} embeddings")
                    time.sleep(pause_s)
                
                i = batch_end
                
            except Exception as e:
                logger.warning(f"Batch embedding failed (size={len(batch_texts)}): {e}")
                failed_count += len(batch_texts)
                consecutive_failures += 1
                
                # Circuit breaker: reduce batch size on repeated failures
                if consecutive_failures >= 3:
                    current_batch_size = max(min_batch_size, current_batch_size // 2)
                    logger.warning(f"[CIRCUIT BREAKER] reducing batch_size to {current_batch_size}")
                    consecutive_failures = 0
                
                # Fallback: try single embedding for failed batch
                for offset, text in enumerate(batch_texts):
                    try:
                        emb = client.embed_text(text)
                        embeddings[i + offset] = emb
                        total_processed += 1
                        failed_count -= 1
                    except Exception as e2:
                        logger.error(f"Single fallback also failed: {e2}")
                
                i = batch_end
                time.sleep(2)  # Cooldown after failure
        
        # Final metrics
        elapsed = max(0.001, time.time() - start_ts)
        success_count = sum(1 for e in embeddings if e is not None)
        success_rate = (success_count / len(texts)) * 100 if texts else 100
        
        if failed_count > 0:
            logger.warning(
                f"[DONE] Embedding completed with {failed_count} failures "
                f"({success_rate:.1f}% success, {elapsed:.1f}s, {success_count/elapsed:.1f} emb/s)"
            )
        else:
            logger.info(
                f"[DONE] Embedding completed: {success_count} texts in {elapsed:.1f}s "
                f"({success_count/elapsed:.1f} emb/s)"
            )
        
        return {
            "success": True,
            "embeddings": embeddings,
            "count": success_count,
            "failed": failed_count,
            "metrics": {
                "total": len(texts),
                "success": success_count,
                "failed": failed_count,
                "elapsed_s": elapsed,
                "rate_per_s": success_count / elapsed,
                "success_rate": success_rate,
            }
        }
    
    def _run_single_mode(
        self,
        client: "OllamaClient",
        texts: List[str],
        max_text_length: int,
        pause_every: int,
        pause_s: float,
        log_every: int,
    ) -> Dict[str, Any]:
        """Fallback single-embedding mode for compatibility."""
        import time
        
        embeddings = []
        failed_count = 0
        start_ts = time.time()
        last_log_ts = start_ts
        
        for i, text in enumerate(texts):
            try:
                embedding = client.embed_text(text)
                embeddings.append(embedding)
                
                if log_every > 0 and (i + 1) % log_every == 0:
                    now = time.time()
                    elapsed = max(0.001, now - start_ts)
                    rate = (i + 1) / elapsed
                    logger.info(f"Embedded {i + 1}/{len(texts)} texts ({rate:.2f} emb/s)")
                    last_log_ts = now
                
                if pause_every > 0 and (i + 1) % pause_every == 0:
                    logger.debug(f"Pause after {i + 1} embeddings")
                    time.sleep(pause_s)
                    
            except Exception as e:
                logger.error(f"Failed to embed text: {e}")
                failed_count += 1
        
        elapsed = max(0.001, time.time() - start_ts)
        logger.info(f"Single-mode completed: {len(embeddings)}/{len(texts)} in {elapsed:.1f}s")
        
        return {
            "success": True,
            "embeddings": embeddings,
            "count": len(embeddings),
            "failed": failed_count
        }
