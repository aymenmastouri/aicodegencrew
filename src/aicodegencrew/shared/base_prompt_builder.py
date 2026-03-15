"""BasePromptBuilder — abstract base class for all prompt builders.

Prompt builders are pure functions: receive collected data as a dict,
return chat-format message dicts for LLMGenerator.  No LLM calls, no I/O.

Contract: every PromptBuilder implements exactly one method::

    def build(self, data: dict) -> list[dict]:
        ...

All inputs (recipe, section_id, sections, …) are passed inside the data dict.
This uniform interface makes pipelines composable and testable.
"""

from abc import ABC, abstractmethod


class BasePromptBuilder(ABC):
    """Abstract base for all PromptBuilder implementations.

    Every subclass must implement ``build(data) -> list[dict]``.
    The keys inside ``data`` are defined by the concrete builder's
    pipeline contract — see each subclass's docstring.
    """

    @abstractmethod
    def build(self, data: dict) -> list[dict]:
        """Build chat-format messages from collected data.

        Args:
            data: Dict of pre-collected facts.  Required keys are
                  defined by the concrete builder.

        Returns:
            List of ``{"role": ..., "content": ...}`` message dicts.
        """
