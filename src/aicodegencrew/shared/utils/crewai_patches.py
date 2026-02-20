"""
CrewAI Runtime Patches
======================
Fixes on-prem LLM compatibility issues with CrewAI.

Patch 1: handle_max_iterations_exceeded
  Problem: When max iterations is exceeded, CrewAI calls llm.call(messages)
           WITHOUT tools=[] — so the on-prem LLM returns tool calls instead
           of text. This causes TaskOutput.raw validation to fail because
           raw expects a string, not a list of ChatCompletionMessageToolCall.
  Fix:     Monkey-patch to pass tools=[] in the final LLM call, forcing
           a text-only response.

Usage:
    # Call once at module level (before any crew.kickoff())
    from aicodegencrew.shared.utils.crewai_patches import apply_patches
    apply_patches()
"""

import logging

logger = logging.getLogger(__name__)

_patches_applied = False


def apply_patches() -> None:
    """Apply all CrewAI patches. Safe to call multiple times (idempotent)."""
    global _patches_applied
    if _patches_applied:
        return

    _patch_max_iterations_handler()
    _patches_applied = True
    logger.info("[PATCH] CrewAI patches applied (max_iterations text-only)")


def _patch_max_iterations_handler() -> None:
    """Patch handle_max_iterations_exceeded to force text-only final LLM call.

    CrewAI's default implementation calls llm.call(messages, callbacks=...)
    without tools=[], allowing the LLM to return tool calls. On-prem LLMs
    (gpt-oss-120b via vLLM) often return tool calls even when asked to
    summarize, causing TaskOutput.raw validation errors.

    The patch adds tools=[] to the final llm.call(), forcing a text response.
    """
    from crewai.utilities import agent_utils

    def patched_handler(formatted_answer, printer, i18n, messages, llm, callbacks, verbose=True):
        """Patched: forces tools=[] on final LLM call to prevent tool-call responses."""
        from crewai.utilities.agent_utils import (
            AgentFinish,
            format_answer,
            format_message_for_llm,
        )

        if verbose:
            printer.print(
                content="Maximum iterations reached. Requesting final answer (text-only).",
                color="yellow",
            )

        if formatted_answer and hasattr(formatted_answer, "text"):
            assistant_message = formatted_answer.text + f"\n{i18n.errors('force_final_answer')}"
        else:
            assistant_message = i18n.errors("force_final_answer")

        messages.append(format_message_for_llm(assistant_message, role="assistant"))

        # PATCH: Pass tools=[] to force text-only response from on-prem LLM
        try:
            answer = llm.call(
                messages,
                callbacks=callbacks,
                tools=[],  # Force text-only response
            )
        except TypeError:
            # Fallback: some LLM implementations don't accept tools kwarg
            answer = llm.call(
                messages,
                callbacks=callbacks,
            )

        if answer is None or answer == "":
            if verbose:
                printer.print(
                    content="Received None or empty response from LLM call.",
                    color="red",
                )
            raise ValueError("Invalid response from LLM call - None or empty.")

        # Ensure answer is a string (handle tool call objects from on-prem LLMs)
        if not isinstance(answer, str):
            if hasattr(answer, "content"):
                answer = str(answer.content or "")
            elif isinstance(answer, list):
                # Tool calls returned as list — extract text content
                texts = []
                for item in answer:
                    if hasattr(item, "content") and item.content:
                        texts.append(str(item.content))
                    elif hasattr(item, "text") and item.text:
                        texts.append(str(item.text))
                answer = "\n".join(texts) if texts else str(answer)
            else:
                answer = str(answer)

        formatted = format_answer(answer=answer)

        if isinstance(formatted, AgentFinish):
            return formatted
        return AgentFinish(
            thought=formatted.thought,
            output=formatted.text,
            text=formatted.text,
        )

    agent_utils.handle_max_iterations_exceeded = patched_handler
