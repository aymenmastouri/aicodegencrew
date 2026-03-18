"""Ollama HTTP API client for embeddings."""

import os
import time

import requests

from .logger import setup_logger

logger = setup_logger(__name__)


class OllamaClient:
    """Client for Ollama HTTP API."""

    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        timeout: int | None = None,
        max_retries: int = None,
    ):
        """Initialize Ollama client.

        Args:
            base_url: Ollama API base URL
            model: Embedding model name
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        # If API_BASE is set (e.g. LiteLLM / Sovereign AI Platform),
        # use its OpenAI-compatible /v1/embeddings endpoint instead of Ollama.
        api_base = os.getenv("API_BASE", "")
        if api_base and not base_url and not os.getenv("OLLAMA_BASE_URL"):
            self.base_url = api_base.rstrip("/")
            self._openai_compat = True
            self._api_key = os.getenv("OPENAI_API_KEY", "")
        else:
            self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
            self._openai_compat = False
            self._api_key = ""

        self.model = model or os.getenv("EMBED_MODEL", "nomic-embed-text:latest")
        # Explicit constructor args should override env vars; env is the fallback.
        if timeout is None:
            timeout = int(os.getenv("OLLAMA_TIMEOUT_S", "60"))
        self.timeout = int(timeout)
        if max_retries is None:
            max_retries = int(os.getenv("OLLAMA_MAX_RETRIES", "10"))
        self.max_retries = max(1, int(max_retries))

        # Create session for reuse
        self._session = requests.Session()
        if not self._openai_compat:
            # For local Ollama only: ignore proxy env vars that can cause
            # localhost requests to hang on Windows/corporate setups.
            self._session.trust_env = False

        # Remove trailing slash
        self.base_url = self.base_url.rstrip("/")

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            RuntimeError: If embedding generation fails after retries
        """
        if self._openai_compat:
            return self._embed_openai([text])[0]

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
                    logger.warning(
                        f"Ollama server error {response.status_code} (attempt {attempt + 1}/{self.max_retries}). Server might be overloaded."
                    )
                    # Escalating backoff for server errors: 5s, 10s, 20s...
                    sleep_time = min(30.0, 5.0 * (2**attempt))
                    time.sleep(sleep_time)
                    response.raise_for_status()  # Trigger exception to retry loop

                response.raise_for_status()

                data = response.json()
                # Ollama /api/embed returns "embeddings" array (plural)
                embeddings = data.get("embeddings", [])

                if not embeddings or not embeddings[0]:
                    raise ValueError("Empty embedding returned from Ollama API")

                return embeddings[0]  # Return first embedding

            except requests.exceptions.RequestException as e:
                logger.warning(f"Ollama API request failed (attempt {attempt + 1}/{self.max_retries}): {e}")

                if attempt < self.max_retries - 1:
                    # General backoff for connection errors etc.
                    sleep_time = min(10.0, 2.0 * (2**attempt))
                    time.sleep(sleep_time)
                else:
                    raise RuntimeError(
                        f"Embedding API at {self.base_url} failed after {self.max_retries} attempts. "
                        f"Check server status and network connectivity. Last error: {e}"
                    )

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
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

        if self._openai_compat:
            return self._embed_openai(texts)

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
                    sleep_time = min(30.0, 5.0 * (2**attempt))
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
                        f"Expected {len(texts)} embeddings, got {len(embeddings)}. Possible batch size limit exceeded."
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
                        f"Batch embedding timed out after {self.max_retries} attempts. Try reducing EMBED_BATCH_SIZE."
                    )

            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"Ollama batch request failed (attempt {attempt + 1}/{self.max_retries}, "
                    f"batch_size={len(texts)}): {e}"
                )

                if attempt < self.max_retries - 1:
                    sleep_time = min(10.0, 2.0 * (2**attempt))
                    time.sleep(sleep_time)
                else:
                    raise RuntimeError(
                        f"Embedding API at {self.base_url} batch request failed after {self.max_retries} attempts. "
                        f"Check server status and network connectivity. Last error: {e}"
                    )

    def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings via OpenAI-compatible API (LiteLLM / SAI Platform)."""
        url = f"{self.base_url}/embeddings"
        payload = {
            "model": self.model,
            "input": texts,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }
        timeout = (10, max(30, len(texts) * 0.5))

        for attempt in range(self.max_retries):
            try:
                response = self._session.post(url, json=payload, headers=headers, timeout=timeout)
                if response.status_code >= 500:
                    logger.warning(
                        f"Embedding API error {response.status_code} (attempt {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(min(30.0, 5.0 * (2 ** attempt)))
                    response.raise_for_status()
                response.raise_for_status()
                data = response.json()
                # OpenAI format: {"data": [{"embedding": [...], "index": 0}, ...]}
                embeddings = [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]
                if len(embeddings) != len(texts):
                    raise ValueError(f"Expected {len(texts)} embeddings, got {len(embeddings)}")
                return embeddings
            except requests.exceptions.RequestException as e:
                logger.warning(f"Embedding API request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(min(10.0, 2.0 * (2 ** attempt)))
                else:
                    raise RuntimeError(
                        f"Embedding API at {self.base_url} is unreachable after {self.max_retries} attempts. "
                        f"Check server status and network connectivity. Last error: {e}"
                    )

    def health_check(self) -> bool:
        """Check if embedding API is accessible."""
        try:
            if self._openai_compat:
                # OpenAI-compatible: try /models endpoint
                headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
                response = self._session.get(f"{self.base_url}/models", headers=headers, timeout=(5, 10))
            else:
                response = self._session.get(f"{self.base_url}/api/tags", timeout=(2, 5))
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
