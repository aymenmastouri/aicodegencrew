"""Shared LLM factory - single source of truth for CrewAI LLM creation.

All crews import `create_llm()` from here instead of duplicating the logic.
"""

import logging
import os

# Inject the OS/Windows certificate store BEFORE any HTTP library is imported
# so that corporate self-signed CAs are trusted by Python's SSL stack.
# (certifi bundle does not include corporate / on-prem CA certificates)
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass  # truststore not installed — fall back to certifi bundle

from crewai import LLM

logger = logging.getLogger(__name__)

# Default model - used when MODEL env var is not set.
# In production, MODEL is always set via .env file.
_DEFAULT_MODEL = "gpt-4o-mini"


def create_llm(
    *,
    temperature: float = 0.1,
    timeout: int = 300,
    model_override: str | None = None,
) -> LLM:
    """Create a CrewAI LLM instance from environment variables.

    Reads: MODEL, API_BASE, MAX_LLM_OUTPUT_TOKENS, LLM_CONTEXT_WINDOW.

    Args:
        temperature: LLM temperature (default 0.1 for deterministic output).
        timeout: Request timeout in seconds.
        model_override: If provided, use this model instead of MODEL env var.
    """
    model = model_override or os.getenv("MODEL", _DEFAULT_MODEL)
    api_base = os.getenv("API_BASE", "")
    api_key = os.getenv("OPENAI_API_KEY", "")
    max_tokens = int(os.getenv("MAX_LLM_OUTPUT_TOKENS", "4000"))
    context_window = int(os.getenv("LLM_CONTEXT_WINDOW", "120000"))

    if not api_key:
        logger.warning("[LLM] OPENAI_API_KEY is empty — LLM calls will fail")

    if max_tokens < 1:
        max_tokens = 4000

    model = _ensure_provider_prefix(model)

    llm = LLM(
        model=model,
        base_url=api_base,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    # Set context window size directly (not via constructor kwargs,
    # which would pass it as additional_params to the API call)
    llm.context_window_size = context_window
    return llm


def _ensure_provider_prefix(model: str) -> str:
    """Add 'openai/' prefix if model lacks a litellm provider prefix.

    litellm auto-detects provider from prefixes like 'gpt-', 'claude-', etc.
    Custom model names (e.g. 'Qwen/...') need an explicit 'openai/' prefix
    when served via an OpenAI-compatible API.
    """
    _KNOWN_PREFIXES = ("openai/", "anthropic/", "azure/", "gpt-", "claude-", "o1-", "o3-")
    if any(model.lower().startswith(p) for p in _KNOWN_PREFIXES):
        return model
    return f"openai/{model}"


def check_llm_connectivity(*, timeout: int = 10) -> tuple[bool, str]:
    """Quick health check — can we reach the LLM API?

    Returns (reachable, message). Does NOT consume tokens.
    Tries a HEAD/GET on the base URL to verify network connectivity.
    """
    api_base = os.getenv("API_BASE", "")
    if not api_base:
        return True, "No API_BASE set — using default provider (assumed reachable)"

    import urllib.request
    import urllib.error

    # Try /models endpoint (OpenAI-compatible) or just the base URL
    for suffix in ("/v1/models", "/models", "/health", ""):
        url = api_base.rstrip("/") + suffix
        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header("Authorization", f"Bearer {os.getenv('OPENAI_API_KEY', 'test')}")
            urllib.request.urlopen(req, timeout=timeout)
            return True, f"LLM API reachable at {api_base}"
        except urllib.error.HTTPError as e:
            # 401/403 = server is reachable, just auth issue (that's OK for health check)
            if e.code in (401, 403, 404, 405):
                return True, f"LLM API reachable at {api_base} (HTTP {e.code})"
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            last_err = str(e)
            continue

    return False, f"LLM API UNREACHABLE at {api_base}: {last_err}"


def create_fast_llm(
    *,
    temperature: float = 0.1,
    timeout: int = 120,
) -> LLM:
    """Create a CrewAI LLM instance for simple, fast tasks.

    Reads FAST_MODEL (falls back to MODEL) — intended for light tasks like
    triage, classification, and formatting where speed matters more than depth.
    """
    model = os.getenv("FAST_MODEL") or os.getenv("MODEL") or _DEFAULT_MODEL
    api_base = os.getenv("API_BASE", "")
    max_tokens = int(os.getenv("MAX_LLM_OUTPUT_TOKENS", "4000"))
    context_window = int(os.getenv("LLM_CONTEXT_WINDOW", "120000"))

    if max_tokens < 1:
        max_tokens = 4000

    model = _ensure_provider_prefix(model)

    llm = LLM(
        model=model,
        base_url=api_base,
        api_key=os.getenv("OPENAI_API_KEY", ""),
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    llm.context_window_size = context_window
    return llm


def create_vision_llm(
    *,
    temperature: float = 0.1,
    timeout: int = 300,
) -> LLM:
    """Create a CrewAI LLM instance for vision/multimodal tasks.

    Reads VISION_MODEL (falls back to MODEL) — intended for tasks that process
    images, diagrams, screenshots, or OCR-heavy documents.
    """
    model = os.getenv("VISION_MODEL") or os.getenv("MODEL") or _DEFAULT_MODEL
    api_base = os.getenv("API_BASE", "")
    max_tokens = int(os.getenv("MAX_LLM_OUTPUT_TOKENS", "4000"))
    context_window = int(os.getenv("LLM_CONTEXT_WINDOW", "120000"))

    if max_tokens < 1:
        max_tokens = 4000

    model = _ensure_provider_prefix(model)

    llm = LLM(
        model=model,
        base_url=api_base,
        api_key=os.getenv("OPENAI_API_KEY", ""),
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    llm.context_window_size = context_window
    return llm


def create_codegen_llm(
    *,
    temperature: float = 0.1,
    timeout: int = 300,
) -> LLM:
    """Create a CrewAI LLM instance for code-writing agents.

    Reads:
    - CODEGEN_MODEL or MODEL
    - CODEGEN_API_BASE or API_BASE
    - CODEGEN_API_KEY or OPENAI_API_KEY
    - MAX_LLM_OUTPUT_TOKENS
    - LLM_CONTEXT_WINDOW

    Falls back to the default model configuration when CODEGEN_* variables
    are not present, so existing deployments continue to work unchanged.
    """
    model = os.getenv("CODEGEN_MODEL") or os.getenv("MODEL") or _DEFAULT_MODEL
    api_base = os.getenv("CODEGEN_API_BASE") or os.getenv("API_BASE", "")
    api_key = os.getenv("CODEGEN_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    max_tokens = int(os.getenv("MAX_LLM_OUTPUT_TOKENS", "4000"))
    context_window = int(os.getenv("LLM_CONTEXT_WINDOW", "120000"))

    if max_tokens < 1:
        max_tokens = 4000

    model = _ensure_provider_prefix(model)

    llm = LLM(
        model=model,
        base_url=api_base,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    llm.context_window_size = context_window
    return llm
