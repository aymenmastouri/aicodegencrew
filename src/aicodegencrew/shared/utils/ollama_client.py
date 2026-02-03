"""Ollama HTTP API client for embeddings."""

import os
import time
import requests
from typing import List, Dict, Any
from .logger import setup_logger

logger = setup_logger(__name__)


class OllamaClient:
    """Client for Ollama HTTP API."""
    
    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        timeout: int = 60,
        max_retries: int = None,
    ):
        """Initialize Ollama client.
        
        Args:
            base_url: Ollama API base URL
            model: Embedding model name
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model or os.getenv("EMBED_MODEL", "nomic-embed-text:latest")
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT_S", str(timeout)))
        if max_retries is None:
            max_retries = int(os.getenv("OLLAMA_MAX_RETRIES", "10"))
        self.max_retries = max(1, int(max_retries))

        # Create session for reuse
        self._session = requests.Session()
        # On Windows/corporate setups, env proxies can cause localhost requests to hang.
        # We explicitly ignore proxy env vars for Ollama (local service).
        self._session.trust_env = False
        
        # Remove trailing slash
        self.base_url = self.base_url.rstrip("/")
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
            
        Raises:
            RuntimeError: If embedding generation fails after retries
        """
        url = f"{self.base_url}/api/embed"
        payload = {
            "model": self.model,
            "input": text,
        }

        # Use explicit connect/read timeouts. A single int in requests is applied to both,
        # but setting a small connect timeout avoids long hangs on connect/proxy issues.
        timeout = (5, self.timeout)

        headers = {
            # Avoid some keep-alive edge cases on Windows/proxy layers.
            "Connection": "close",
        }
        
        for attempt in range(self.max_retries):
            # Reuse a configured session (trust_env=False) to avoid proxy surprises.
            session = self._session
            
            try:
                response = session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=timeout,
                )
                
                # Special handling for 500 errors (Ollama overloaded)
                if response.status_code >= 500:
                    logger.warning(f"Ollama server error {response.status_code} (attempt {attempt + 1}/{self.max_retries}). Server might be overloaded.")
                    # Escalating backoff for server errors: 5s, 10s, 20s...
                    sleep_time = min(30.0, 5.0 * (2 ** attempt))
                    time.sleep(sleep_time)
                    response.raise_for_status() # Trigger exception to retry loop
                
                response.raise_for_status()
                
                data = response.json()
                # Ollama /api/embed returns "embeddings" array (plural)
                embeddings = data.get("embeddings", [])
                
                if not embeddings or not embeddings[0]:
                    raise ValueError(f"Empty embedding returned from Ollama API")
                
                return embeddings[0]  # Return first embedding
                
            except requests.exceptions.RequestException as e:
                status = None
                try:
                    status = response.status_code  # type: ignore[name-defined]
                except Exception:
                    status = None

                logger.warning(
                    f"Ollama API request failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )

                if attempt < self.max_retries - 1:
                    # General backoff for connection errors etc.
                    sleep_time = min(10.0, 2.0 * (2 ** attempt))
                    time.sleep(sleep_time)
                else:
                    raise RuntimeError(f"Failed to generate embedding after {self.max_retries} attempts: {e}")
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in ONE request (Production Best Practice).
        
        Batch API provides 10-50x performance improvement over individual requests:
        - Single HTTP round-trip for multiple texts
        - Ollama can optimize GPU batch processing
        - Reduced connection overhead
        - Better throughput under load
        
        Args:
            texts: List of texts to embed (recommended: 10-100 texts per batch)
            
        Returns:
            List of embedding vectors (same order as input)
            
        Raises:
            RuntimeError: If embedding generation fails after retries
        """
        if not texts:
            return []
        
        url = f"{self.base_url}/api/embed"
        payload = {
            "model": self.model,
            "input": texts,  # Send array of texts
        }

        # Adaptive timeout: base + per-text overhead
        base_timeout = 10
        per_text_timeout = 0.5
        read_timeout = base_timeout + (len(texts) * per_text_timeout)
        timeout = (5, read_timeout)
        
        headers = {
            "Connection": "close",
        }
        
        for attempt in range(self.max_retries):
            try:
                response = self._session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=timeout,
                )
                
                # Handle server errors with exponential backoff
                if response.status_code >= 500:
                    logger.warning(
                        f"Ollama batch error {response.status_code} "
                        f"(attempt {attempt + 1}/{self.max_retries}, batch_size={len(texts)})"
                    )
                    sleep_time = min(30.0, 5.0 * (2 ** attempt))
                    time.sleep(sleep_time)
                    response.raise_for_status()
                
                response.raise_for_status()
                data = response.json()
                embeddings = data.get("embeddings", [])
                
                # Validation
                if not embeddings:
                    raise ValueError("Empty embeddings array returned from Ollama API")
                    
                if len(embeddings) != len(texts):
                    raise ValueError(
                        f"Expected {len(texts)} embeddings, got {len(embeddings)}. "
                        f"Possible batch size limit exceeded."
                    )
                
                return embeddings
                
            except requests.exceptions.Timeout as e:
                logger.warning(
                    f"Batch timeout (attempt {attempt + 1}/{self.max_retries}, "
                    f"batch_size={len(texts)}, timeout={read_timeout}s): {e}"
                )
                if attempt < self.max_retries - 1:
                    # Increase timeout for retry
                    read_timeout *= 1.5
                    timeout = (5, read_timeout)
                    time.sleep(2)
                else:
                    raise RuntimeError(
                        f"Batch embedding timed out after {self.max_retries} attempts. "
                        f"Try reducing EMBED_BATCH_SIZE."
                    )
                    
            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"Ollama batch request failed (attempt {attempt + 1}/{self.max_retries}, "
                    f"batch_size={len(texts)}): {e}"
                )
                
                if attempt < self.max_retries - 1:
                    sleep_time = min(10.0, 2.0 * (2 ** attempt))
                    time.sleep(sleep_time)
                else:
                    raise RuntimeError(
                        f"Failed to generate batch embeddings after {self.max_retries} attempts: {e}"
                    )
    
    def health_check(self) -> bool:
        """Check if Ollama API is accessible.
        
        Returns:
            True if API is healthy
        """
        try:
            response = self._session.get(
                f"{self.base_url}/api/tags",
                timeout=(2, 5),
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
