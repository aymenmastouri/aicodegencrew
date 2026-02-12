"""Base strategy for code generation."""

from abc import ABC, abstractmethod

from ..schemas import CodegenPlanInput, FileContext


class BaseStrategy(ABC):
    """Abstract base for task-type-specific code generation strategies."""

    @abstractmethod
    def build_prompt(self, file_ctx: FileContext, plan: CodegenPlanInput) -> str:
        """Build LLM prompt for generating/modifying a single file.

        Args:
            file_ctx: Context for the file to generate/modify.
            plan: The overall codegen plan input.

        Returns:
            Complete prompt string for the LLM.
        """
        ...

    @abstractmethod
    def post_process(self, llm_output: str, file_ctx: FileContext) -> str:
        """Post-process LLM output before writing.

        Args:
            llm_output: Raw code from LLM response.
            file_ctx: Context for the file.

        Returns:
            Cleaned/validated code string.
        """
        ...

    @staticmethod
    def _extract_code_block(text: str) -> str:
        """Extract code from markdown code blocks if present."""
        text = text.strip()

        # Try to extract from ```language ... ``` blocks
        if "```" in text:
            lines = text.split("\n")
            in_block = False
            code_lines = []
            for line in lines:
                if line.strip().startswith("```") and not in_block:
                    in_block = True
                    continue
                elif line.strip() == "```" and in_block:
                    in_block = False
                    continue
                elif in_block:
                    code_lines.append(line)
            if code_lines:
                return "\n".join(code_lines)

        return text

    @staticmethod
    def _format_steps(steps: list) -> str:
        """Format implementation steps for prompt."""
        if not steps:
            return "  (none)"
        return "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(steps))

    @staticmethod
    def _format_patterns(patterns: list) -> str:
        """Format related patterns for prompt."""
        if not patterns:
            return "  (none)"
        return "\n".join(f"  - {p}" for p in patterns[:5])
