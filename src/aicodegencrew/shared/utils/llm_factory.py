"""Shared LLM factory - single source of truth for CrewAI LLM creation.

All crews import `create_llm()` from here instead of duplicating the logic.
"""

import os

from crewai import LLM

# Default model - used when MODEL env var is not set.
# In production, MODEL is always set via .env file.
_DEFAULT_MODEL = "gpt-4o-mini"


def create_llm(
    *,
    temperature: float = 0.1,
    timeout: int = 300,
) -> LLM:
    """Create a CrewAI LLM instance from environment variables.

    Reads: MODEL, API_BASE, MAX_LLM_OUTPUT_TOKENS, LLM_CONTEXT_WINDOW.

    Args:
        temperature: LLM temperature (default 0.1 for deterministic output).
        timeout: Request timeout in seconds.
    """
    model = os.getenv("MODEL", _DEFAULT_MODEL)
    api_base = os.getenv("API_BASE", "")
    max_tokens = int(os.getenv("MAX_LLM_OUTPUT_TOKENS", "4000"))
    context_window = int(os.getenv("LLM_CONTEXT_WINDOW", "120000"))

    if max_tokens < 1:
        max_tokens = 4000

    llm = LLM(
        model=model,
        base_url=api_base,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    # Set context window size directly (not via constructor kwargs,
    # which would pass it as additional_params to the API call)
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
