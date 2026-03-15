"""LLMGenerator — single LLM call for chapter generation.

No agents, no tools, no loops. Just one completion call.
Supports retry with feedback when validation fails.
"""

import logging
import os

from dotenv import load_dotenv

# Ensure .env is loaded even when called outside CLI subprocess
load_dotenv(override=True)

logger = logging.getLogger(__name__)


class LLMGenerator:
    """Generates chapter content via a single LLM completion call."""

    def __init__(self, use_fast_model: bool = False):
        self._use_fast_model = use_fast_model

    def generate(self, messages: list[dict[str, str]]) -> str:
        """Generate chapter content from structured messages.

        Args:
            messages: Chat-format messages [{"role": "system", "content": "..."}, ...]

        Returns:
            Generated markdown content string.
        """
        import litellm

        model = self._resolve_model()
        api_base = os.getenv("API_BASE", "")
        api_key = os.getenv("OPENAI_API_KEY", "")
        max_tokens = int(os.getenv("MAX_LLM_OUTPUT_TOKENS", "65536"))

        logger.info("[LLMGenerator] Calling %s (max_tokens=%d)", model, max_tokens)

        response = litellm.completion(
            model=model,
            messages=messages,
            api_base=api_base,
            api_key=api_key,
            max_tokens=max_tokens,
            temperature=0.7,  # Balanced: creative enough for interpretation, stable enough for facts
            top_p=0.95,
            timeout=180,  # 3 min max per call — prevents indefinite hangs
            num_retries=3,
        )

        content = response.choices[0].message.content or ""

        # Strip markdown code fences if LLM wrapped the output
        content = self._strip_fences(content)

        # Log token usage
        usage = response.usage
        if usage:
            logger.info(
                "[LLMGenerator] Tokens: %d total (%d prompt, %d completion)",
                usage.total_tokens,
                usage.prompt_tokens,
                usage.completion_tokens,
            )

        return content

    def retry_with_feedback(
        self,
        original_messages: list[dict[str, str]],
        previous_output: str,
        issues: list[str],
    ) -> str:
        """Retry generation with specific feedback about what to fix.

        Args:
            original_messages: The original prompt messages.
            previous_output: The LLM's previous output that had issues.
            issues: List of specific validation issues to fix.

        Returns:
            Improved markdown content string.
        """
        issues_text = "\n".join(f"- {issue}" for issue in issues)

        feedback_msg = {
            "role": "user",
            "content": f"""<feedback>
Your previous output had these specific issues:
{issues_text}

Please fix ONLY the listed problems. Keep everything that was good.
Output the complete corrected chapter.
</feedback>

<previous_output>
{previous_output[:15000]}
</previous_output>""",
        }

        messages = [
            original_messages[0],  # system message
            original_messages[1],  # original user message
            {"role": "assistant", "content": previous_output[:15000]},
            feedback_msg,
        ]

        logger.info("[LLMGenerator] Retry with %d issues: %s", len(issues), issues[:3])
        return self.generate(messages)

    def _resolve_model(self) -> str:
        """Resolve model name from env vars.

        Uses MODEL/FAST_MODEL directly as configured in .env.
        No provider prefix added — litellm with api_base handles routing.
        """
        model = os.getenv("MODEL", "openai/code")
        return model

    @staticmethod
    def _strip_fences(content: str) -> str:
        """Strip markdown code fences if LLM wrapped output in ```markdown...```."""
        stripped = content.strip()
        if stripped.startswith("```markdown"):
            stripped = stripped[len("```markdown") :].strip()
        elif stripped.startswith("```md"):
            stripped = stripped[len("```md") :].strip()
        elif stripped.startswith("```"):
            stripped = stripped[3:].strip()
        if stripped.endswith("```"):
            stripped = stripped[:-3].strip()
        return stripped
