"""Strategy for targeted bug fixes."""

from .base import BaseStrategy
from ..schemas import FileContext, CodegenPlanInput


class BugfixStrategy(BaseStrategy):
    """Generate minimal code changes for bug fixes."""

    def build_prompt(self, file_ctx: FileContext, plan: CodegenPlanInput) -> str:
        return f"""You are a senior developer fixing a bug with minimal, targeted changes.

BUG DESCRIPTION: {plan.summary}
{plan.description}

FILE TO FIX:
Path: {file_ctx.file_path}
Language: {file_ctx.language}

CURRENT CODE:
```{file_ctx.language}
{file_ctx.content}
```

IMPLEMENTATION STEPS:
{self._format_steps(plan.implementation_steps)}

ERROR HANDLING PATTERNS IN CODEBASE:
{self._format_patterns(file_ctx.related_patterns)}

INSTRUCTIONS:
- Fix ONLY the described bug
- Make MINIMAL changes — do not refactor or improve unrelated code
- Preserve existing behavior for all non-buggy paths
- Follow existing error handling patterns
- Return ONLY the complete updated file content
- Do NOT add explanations, only code

Return the complete file:"""

    def post_process(self, llm_output: str, file_ctx: FileContext) -> str:
        return self._extract_code_block(llm_output)
