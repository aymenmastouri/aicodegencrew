"""Strategy for code restructuring/refactoring."""

from ..schemas import CodegenPlanInput, FileContext
from .base import BaseStrategy


class RefactoringStrategy(BaseStrategy):
    """Generate code changes for refactoring tasks."""

    def build_prompt(self, file_ctx: FileContext, plan: CodegenPlanInput) -> str:
        return f"""You are a senior developer restructuring code while preserving behavior.

REFACTORING GOAL: {plan.summary}
{plan.description}

FILE TO REFACTOR:
Path: {file_ctx.file_path}
Language: {file_ctx.language}

CURRENT CODE:
```{file_ctx.language}
{file_ctx.content}
```

IMPLEMENTATION STEPS:
{self._format_steps(plan.implementation_steps)}

ARCHITECTURE CONTEXT:
- Style: {plan.architecture_context.get("style", "layered")}
- Layer Pattern: {plan.architecture_context.get("layer_pattern", "Controller → Service → Repository")}

RELATED PATTERNS:
{self._format_patterns(file_ctx.related_patterns)}

INSTRUCTIONS:
- Restructure the code following the implementation steps
- PRESERVE all public method signatures and behavior
- Improve internal structure, readability, and maintainability
- Follow SOLID principles
- Keep existing imports unless they become unused
- Return ONLY the complete updated file content
- Do NOT add explanations, only code

Return the complete file:"""

    def post_process(self, llm_output: str, file_ctx: FileContext) -> str:
        return self._extract_code_block(llm_output)
