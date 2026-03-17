"""LLMGenerator — centralized LLM call for all pipelines.

Single source of truth for all LLM configuration:
  MODEL, API_BASE, OPENAI_API_KEY, MAX_LLM_OUTPUT_TOKENS,
  LLM_TEMPERATURE, LLM_TOP_P, LLM_TOP_K, LLM_CHUNK_TIMEOUT.

No agents, no tools, no loops. One completion call per invocation.
Supports retry-with-feedback when validation fails.

Usage::

    generator = LLMGenerator()
    content = generator.generate([
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."},
    ])
"""

import logging
import os

from dotenv import load_dotenv

# Ensure .env is loaded even when called outside CLI subprocess
load_dotenv(override=True)

logger = logging.getLogger(__name__)


class LLMGenerator:
    """Executes a single streaming LLM completion call.

    All configuration is read from environment variables at call time so
    that changes to the .env file are picked up without restarting the
    process.

    Env vars consumed:
        MODEL              — litellm model identifier (default: "openai/code")
        API_BASE           — litellm api_base URL
        OPENAI_API_KEY     — API key forwarded to litellm
        MAX_LLM_OUTPUT_TOKENS — max tokens in response (default: 65536)
        LLM_TEMPERATURE    — sampling temperature (default: 1.0)
        LLM_TOP_P          — nucleus sampling p (default: 0.95)
        LLM_TOP_K          — top-k sampling (default: 40; via extra_body)
        LLM_CHUNK_TIMEOUT  — seconds to wait between stream chunks (default: 60)

    Note:
        ``use_fast_model`` is accepted for API compatibility but currently
        ignored — all pipelines always use MODEL for quality output.
    """

    def __init__(self, use_fast_model: bool = False):
        # Reserved for future use; see note in class docstring.
        self._use_fast_model = use_fast_model

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def generate(self, messages: list[dict[str, str]]) -> str:
        """Execute a single streaming LLM call and return the raw response.

        Args:
            messages: Chat-format messages, e.g.
                      [{"role": "system", "content": "..."}, ...].

        Returns:
            Raw LLM output string.  Callers are responsible for any
            post-processing (fence stripping, JSON parsing, etc.).
        """
        import litellm

        model, api_base, api_key, max_tokens, temperature, top_p, top_k, chunk_timeout = (
            self._read_config()
        )

        logger.info("[LLMGenerator] Calling %s (max_tokens=%d)", model, max_tokens)

        stream = litellm.completion(
            model=model,
            messages=messages,
            api_base=api_base,
            api_key=api_key,
            max_tokens=max_tokens,
            # Qwen3-Coder-Next best practice: temperature=1.0, top_p=0.95, top_k=40
            temperature=temperature,
            top_p=top_p,
            extra_body={"top_k": top_k},
            timeout=chunk_timeout,
            num_retries=3,
            stream=True,
        )

        chunks: list[str] = []
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                chunks.append(delta)
        content = "".join(chunks)

        logger.info("[LLMGenerator] Received %d chars", len(content))
        return content

    def generate_text(self, messages: list[dict[str, str]]) -> str:
        """Generate text content, stripping markdown code fences from the output.

        Convenience method for pipelines that produce Markdown — the LLM
        sometimes wraps its output in ``` fences which are removed transparently.

        Args:
            messages: Chat-format messages.

        Returns:
            LLM output with code fences stripped.
        """
        return self._strip_fences(self.generate(messages))

    def retry_with_feedback(
        self,
        original_messages: list[dict[str, str]],
        previous_output: str,
        issues: list[str],
    ) -> str:
        """Retry generation with specific feedback about what to fix.

        Appends the previous output and a list of issues to the message
        history and re-generates.  Useful for validation → retry loops.

        Args:
            original_messages: The original [system, user] prompt messages.
            previous_output:   The LLM's previous output that had issues.
            issues:            List of specific validation issues to fix.

        Returns:
            New raw LLM output string.
        """
        issues_text = "\n".join(f"- {issue}" for issue in issues)
        feedback_msg = {
            "role": "user",
            "content": (
                f"<feedback>\n"
                f"Your previous output had these specific issues:\n"
                f"{issues_text}\n\n"
                f"Please fix ONLY the listed problems. Keep everything that was good.\n"
                f"Output the complete corrected result.\n"
                f"</feedback>\n\n"
                f"<previous_output>\n"
                f"{previous_output[:15000]}\n"
                f"</previous_output>"
            ),
        }
        messages = [
            original_messages[0],  # system message
            original_messages[1],  # original user message
            {"role": "assistant", "content": previous_output[:15000]},
            feedback_msg,
        ]
        logger.info("[LLMGenerator] Retry with %d issues: %s", len(issues), issues[:3])
        return self.generate(messages)

    def retry_with_feedback_text(
        self,
        original_messages: list[dict[str, str]],
        previous_output: str,
        issues: list[str],
    ) -> str:
        """Retry with feedback, stripping markdown code fences from the result.

        Convenience wrapper for Markdown-generating pipelines.

        Args:
            original_messages: The original prompt messages.
            previous_output:   The LLM's previous output that had issues.
            issues:            List of specific validation issues to fix.

        Returns:
            Improved content string with code fences stripped.
        """
        return self._strip_fences(
            self.retry_with_feedback(original_messages, previous_output, issues)
        )

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    @staticmethod
    def _strip_fences(content: str) -> str:
        """Strip markdown code fences if the LLM wrapped its output.

        Handles: ```markdown, ```md, ```json, and plain ```.
        """
        stripped = content.strip()
        for prefix in ("```markdown", "```md", "```json", "```"):
            if stripped.startswith(prefix):
                stripped = stripped[len(prefix):].strip()
                break
        if stripped.endswith("```"):
            stripped = stripped[:-3].strip()
        return stripped

    # -------------------------------------------------------------------------
    # Config
    # -------------------------------------------------------------------------

    def _resolve_model(self) -> str:
        """Resolve model name from env vars.

        Uses MODEL directly as configured in .env.
        No provider prefix added — litellm with api_base handles routing.
        """
        return os.getenv("MODEL", "openai/code")

    def _read_config(self) -> tuple:
        """Read all LLM configuration from environment variables.

        Returns:
            Tuple of (model, api_base, api_key, max_tokens, temperature,
                      top_p, top_k, chunk_timeout).
        """
        return (
            self._resolve_model(),
            os.getenv("API_BASE", ""),
            os.getenv("OPENAI_API_KEY", ""),
            int(os.getenv("MAX_LLM_OUTPUT_TOKENS", "65536")),
            float(os.getenv("LLM_TEMPERATURE", "1.0")),
            float(os.getenv("LLM_TOP_P", "0.95")),
            int(os.getenv("LLM_TOP_K", "40")),
            int(os.getenv("LLM_CHUNK_TIMEOUT", "60")),
        )
