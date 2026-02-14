"""Strategy for new feature implementation."""

from ..schemas import CodegenPlanInput, FileContext
from .base import BaseStrategy


class FeatureStrategy(BaseStrategy):
    """Generate code for new features."""

    def build_prompt(self, file_ctx: FileContext, plan: CodegenPlanInput) -> str:
        stereotype = ""
        layer = ""
        if file_ctx.component:
            stereotype = file_ctx.component.stereotype
            layer = file_ctx.component.layer

        # For new files, show sibling files as pattern reference
        sibling_hint = ""
        if file_ctx.sibling_files:
            sibling_hint = "\nSIBLING FILES (for pattern reference):\n"
            sibling_hint += "\n".join(f"  - {s}" for s in file_ctx.sibling_files[:5])

        arch_ctx = plan.architecture_context
        arch_style = arch_ctx.get("style", "layered")
        layer_pattern = arch_ctx.get("layer_pattern", "Controller → Service → Repository")

        if file_ctx.content:
            # Modifying existing file
            return f"""You are a senior developer adding a new feature to an existing file.

TASK: {plan.summary}
{plan.description}

FILE TO MODIFY:
Path: {file_ctx.file_path}
Language: {file_ctx.language}
Stereotype: {stereotype}
Layer: {layer}

CURRENT CODE:
```{file_ctx.language}
{file_ctx.content}
```

IMPLEMENTATION STEPS:
{self._format_steps(plan.implementation_steps)}

ARCHITECTURE CONTEXT:
- Style: {arch_style}
- Layer Pattern: {layer_pattern}

RELATED PATTERNS:
{self._format_patterns(file_ctx.related_patterns)}
{sibling_hint}

INSTRUCTIONS:
- Add the new feature following existing code patterns
- Maintain consistent naming conventions
- Follow the {arch_style} architecture ({layer_pattern})
- Preserve all existing functionality
- Return ONLY the complete updated file content
- Do NOT add explanations, only code

Return the complete file:"""
        else:
            # Creating new file
            return f"""You are a senior developer creating a new {stereotype} file.

TASK: {plan.summary}
{plan.description}

NEW FILE TO CREATE:
Path: {file_ctx.file_path}
Language: {file_ctx.language}
Stereotype: {stereotype}
Layer: {layer}

IMPLEMENTATION STEPS:
{self._format_steps(plan.implementation_steps)}

ARCHITECTURE CONTEXT:
- Style: {arch_style}
- Layer Pattern: {layer_pattern}

RELATED PATTERNS:
{self._format_patterns(file_ctx.related_patterns)}
{sibling_hint}

INSTRUCTIONS:
- Create a complete {stereotype} following existing patterns in this codebase
- Use consistent naming conventions matching sibling files
- Follow the {arch_style} architecture ({layer_pattern})
- Include all necessary imports
- Return ONLY the complete file content
- Do NOT add explanations, only code

Return the complete file:"""

    def post_process(self, llm_output: str, file_ctx: FileContext) -> str:
        return self._extract_code_block(llm_output)
