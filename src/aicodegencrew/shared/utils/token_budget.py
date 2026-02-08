"""
Token Budget Configuration - Central limits for LLM context.

Reads from environment variables set in .env:
- MAX_LLM_INPUT_TOKENS: Total input tokens for LLM (default: 100000)
- MAX_LLM_OUTPUT_TOKENS: Max output tokens (default: 16000)

Budget allocation for tools:
- Tool responses should use ~25% of input budget
- Rest is reserved for system prompt, conversation history, etc.

Default model config: 100K input, 16K output (gpt-oss-120b)
"""

import os

# Read from environment
MAX_LLM_INPUT_TOKENS = int(os.getenv("MAX_LLM_INPUT_TOKENS", "100000"))
MAX_LLM_OUTPUT_TOKENS = int(os.getenv("MAX_LLM_OUTPUT_TOKENS", "16000"))

# Chars per token (conservative estimate)
CHARS_PER_TOKEN = 4

# Tool response budget: 25% of input tokens
TOOL_BUDGET_RATIO = 0.25
TOOL_MAX_TOKENS = int(MAX_LLM_INPUT_TOKENS * TOOL_BUDGET_RATIO)
TOOL_MAX_CHARS = TOOL_MAX_TOKENS * CHARS_PER_TOKEN

# Specific tool budgets (can be overridden)
MAX_RESPONSE_CHARS = TOOL_MAX_CHARS  # ~32000 chars for 32K model
MAX_SNIPPET_LENGTH = 1500  # Code snippet per RAG result

# For smaller responses (RAG with many results)
RAG_MAX_RESPONSE_CHARS = int(TOOL_MAX_CHARS * 0.75)  # ~24000 chars

def get_max_response_chars() -> int:
    """Get max response chars based on LLM config."""
    return TOOL_MAX_CHARS

def get_rag_max_chars() -> int:
    """Get max chars for RAG responses."""
    return RAG_MAX_RESPONSE_CHARS

def truncate_response(output: str, max_chars: int = None, hint: str = "") -> str:
    """Truncate response if too large.
    
    Args:
        output: The string to truncate
        max_chars: Max chars (defaults to TOOL_MAX_CHARS)
        hint: Hint message for user
    
    Returns:
        Truncated string with marker if needed
    """
    max_chars = max_chars or TOOL_MAX_CHARS
    
    if len(output) <= max_chars:
        return output
    
    truncated = output[:max_chars]
    marker = f"\n... [TRUNCATED at {max_chars} chars"
    if hint:
        marker += f" - {hint}"
    marker += "]"
    
    return truncated + marker


# Log config on import
if __name__ != "__main__":
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(
        f"Token Budget: {MAX_LLM_INPUT_TOKENS} input tokens, "
        f"Tool budget: {TOOL_MAX_TOKENS} tokens ({TOOL_MAX_CHARS} chars)"
    )
