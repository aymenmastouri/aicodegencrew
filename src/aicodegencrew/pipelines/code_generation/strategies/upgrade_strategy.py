"""Strategy for framework upgrade tasks (Angular, Spring, Java)."""

from ..schemas import CodegenPlanInput, FileContext
from .base import BaseStrategy


class UpgradeStrategy(BaseStrategy):
    """Generate code changes for framework upgrades."""

    def build_prompt(self, file_ctx: FileContext, plan: CodegenPlanInput) -> str:
        upgrade = plan.upgrade_plan or {}
        framework = upgrade.get("framework", "Unknown")
        # Handle both Phase 4 schema names and possible LLM-generated variants
        from_ver = upgrade.get("from_version") or upgrade.get("current_version", "?")
        to_ver = upgrade.get("to_version") or upgrade.get("target_version", "?")

        # Collect migration rules relevant to this file
        migration_steps = []
        for rule in upgrade.get("migration_sequence", []):
            affected = rule.get("affected_files", [])
            # Check if this file is in the affected files
            if any(file_ctx.file_path.endswith(af) or af in file_ctx.file_path for af in affected):
                migration_steps.append(rule)

        rules_text = self._format_migration_rules(migration_steps)

        return f"""You are a senior developer performing a {framework} upgrade from {from_ver} to {to_ver}.

FILE TO MODIFY:
Path: {file_ctx.file_path}
Language: {file_ctx.language}

CURRENT CODE:
```{file_ctx.language}
{file_ctx.content}
```

MIGRATION RULES TO APPLY:
{rules_text}

IMPLEMENTATION STEPS:
{self._format_steps(plan.implementation_steps)}

RELATED PATTERNS IN CODEBASE:
{self._format_patterns(file_ctx.related_patterns)}

INSTRUCTIONS:
- Apply ALL relevant migration rules to this file
- Update imports, APIs, and syntax to {framework} {to_ver}
- Remove deprecated API usage
- Preserve existing business logic
- Return ONLY the complete updated file content
- Do NOT add explanations, only code
- Do NOT change code that is unrelated to the upgrade

Return the complete file:"""

    def post_process(self, llm_output: str, file_ctx: FileContext) -> str:
        code = self._extract_code_block(llm_output)
        # Verify imports are present for Java/TypeScript
        if file_ctx.language in ("java", "typescript") and "import" not in code:
            if "import" in file_ctx.content:
                # LLM dropped imports — prepend originals
                original_imports = [line for line in file_ctx.content.split("\n") if line.strip().startswith("import ")]
                code = "\n".join(original_imports) + "\n\n" + code
        return code

    @staticmethod
    def _format_migration_rules(rules: list) -> str:
        if not rules:
            return "  (no specific rules for this file)"
        lines = []
        for r in rules:
            severity = r.get("severity", "recommended")
            lines.append(f"  [{severity.upper()}] {r.get('title', '')}")
            for step in r.get("migration_steps", []):
                lines.append(f"    - {step}")
            schematic = r.get("schematic")
            if schematic:
                lines.append(f"    Schematic: {schematic}")
        return "\n".join(lines)
