"""Implement Crew: Task definitions for single-agent execution.

Two tasks:
1. implement_task — Developer implements all code changes (output_pydantic=ImplementationResult)
2. fix_task — Developer fixes build errors (no output_pydantic — fixes are via write_code() tool)

CrewAI best practices:
- output_pydantic for structured implement results
- crewai_patches.py ensures max-iter handler returns text (not tool calls)
- Code is captured via write_code() tool calls into shared staging dict
"""

from .schemas import ImplementationResult

# =============================================================================
# TASK-TYPE INSTRUCTIONS (embedded in implement task description)
# =============================================================================


def _get_type_instructions(task_type: str, upgrade_plan: dict | None = None) -> str:
    """Return task-type-specific instructions for the agent."""
    if task_type == "upgrade":
        instructions = (
            "UPGRADE TASK RULES:\n"
            "- Follow migration rules from the upgrade plan exactly\n"
            "- Replace deprecated APIs with their modern equivalents\n"
            "- Update version-specific syntax and imports\n"
            "- Preserve all existing business logic while updating framework code\n"
            "- Do NOT change functionality — only upgrade the technical implementation"
        )
        if upgrade_plan:
            version_from = upgrade_plan.get("from_version", "unknown")
            version_to = upgrade_plan.get("to_version", "unknown")
            instructions += f"\n- Migrating from {version_from} to {version_to}"
            rules = upgrade_plan.get("migration_rules", [])
            if rules:
                instructions += "\n- Migration rules:\n"
                for rule in rules[:10]:
                    instructions += f"  * {rule}\n"
        return instructions

    if task_type == "bugfix":
        return (
            "BUGFIX TASK RULES:\n"
            "- Fix ONLY the described bug — do not refactor or improve surrounding code\n"
            "- Preserve all existing behavior except the buggy behavior\n"
            "- Add a comment explaining what was fixed and why\n"
            "- Ensure the fix handles edge cases that could trigger the same bug"
        )

    if task_type == "refactoring":
        return (
            "REFACTORING TASK RULES:\n"
            "- Change code structure without changing external behavior\n"
            "- Preserve all public interfaces (method signatures, return types)\n"
            "- Improve code organization, naming, or internal patterns\n"
            "- Do NOT add new features or fix bugs during refactoring"
        )

    # Default: feature
    return (
        "FEATURE TASK RULES:\n"
        "- Follow existing patterns and conventions in the codebase\n"
        "- Match the naming style, import organization, and code structure of sibling files\n"
        "- Implement only what the plan specifies — no extra features\n"
        "- Ensure all new code integrates with existing dependency injection and configuration"
    )


# =============================================================================
# TASK 1: IMPLEMENT CODE CHANGES
# =============================================================================


def implement_task(
    *,
    task_id: str,
    summary: str,
    description: str,
    task_type: str,
    implementation_steps: list[str],
    upgrade_plan: dict | None,
    dependency_order: list[str],
    task_source_snapshot: str = "",
) -> tuple[str, str, type[ImplementationResult]]:
    """Developer task: implement code changes using all available tools.

    Returns (description, expected_output, output_pydantic) for CrewAI Task construction.
    Uses ImplementationResult Pydantic model (CrewAI best practice).
    crewai_patches.py ensures max-iter handler returns text, preventing validation errors.
    """
    ordered = "\n".join(f"  {i+1}. {p}" for i, p in enumerate(dependency_order)) if dependency_order else "  (none)"
    steps_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(implementation_steps)) if implementation_steps else "  (none)"
    type_instructions = _get_type_instructions(task_type, upgrade_plan)
    task_source_snapshot = task_source_snapshot or "(not available)"

    task_description = f"""\
Implement code changes for task {task_id}.

TASK: {summary}
TYPE: {task_type}

{type_instructions}

PRIMARY INTENT SOURCE (actual task from TASK_INPUT_DIR):
{task_source_snapshot}

SOURCE-OF-TRUTH RULES:
1. FIRST read the original task source and use it as intent source.
2. Treat implementation_steps as GUIDANCE, not ground truth.
3. Resolve conflicts by prioritizing: actual task source -> architecture facts -> codebase evidence.
4. Query architecture facts before code writing.
5. Never implement requirements that are only in the plan but absent from the original task/evidence.

DESCRIPTION:
{description}

IMPLEMENTATION STEPS:
{steps_text}

WORKFLOW — for EACH file in the dependency order below:
1. Read the original task source when scope is unclear
2. Read current file content before modifying
3. Identify external dependencies (node_modules, Maven jars) vs. internal project imports
4. Look up internal imports using your available tools
5. Preserve external dependency imports from the original file
6. Check file dependencies
7. Query architecture facts and search the codebase as needed
8. Generate COMPLETE file content with correct imports
9. Write the complete file using your available tools
10. REPEAT for EVERY file in the list below

DO NOT skip files just because external dependency imports can't be resolved - preserve existing external imports!

IMPORT RULES (CRITICAL):
- Use your import lookup tool for project-internal imports
- For external dependencies, preserve existing imports from the original file
- NEVER write absolute paths like "import X from '/full/path/to/file'"
- NEVER write deep parent-traversal paths
- If import lookup returns nothing, search the codebase before guessing
- For framework/3rd-party imports, READ the existing file and PRESERVE its imports

FILES IN DEPENDENCY ORDER (process ALL of these in order):
{ordered}

CRITICAL REQUIREMENTS:
- Process ALL {len(dependency_order)} files in the list above - DO NOT STOP EARLY
- Generate COMPLETE file content (not fragments or patches)
- Preserve existing imports, annotations, and formatting
- If a file cannot be modified, write an error note and continue to the next file

OUTPUT FORMAT (structured JSON):
After writing ALL files, return a JSON object with this structure:
{{
  "task_id": "{task_id}",
  "files_processed": [
    {{"file_path": "file1.ts", "status": "SUCCESS", "action": "modify", "message": "Updated imports"}},
    {{"file_path": "file2.ts", "status": "SUCCESS", "action": "modify", "message": "Migrated to Angular 19"}},
    {{"file_path": "file3.ts", "status": "ERROR", "action": "modify", "message": "Could not resolve dependency"}}
  ],
  "total_files": {len(dependency_order)},
  "summary": "Processed all X files: Y succeeded, Z failed"
}}

DO NOT call any more tools after writing all files - just return the JSON.
"""

    expected = (
        f"A JSON object conforming to ImplementationResult schema with: task_id={task_id}, "
        f"files_processed array with {len(dependency_order)} entries (one per file in dependency order), "
        f"total_files={len(dependency_order)}, and a summary string."
    )
    return task_description, expected, ImplementationResult


# =============================================================================
# TASK 2: FIX BUILD ERRORS
# =============================================================================


def fix_task(
    *,
    task_id: str,
    build_errors: str,
    failed_files: list[str],
    dependency_order: list[str],
) -> tuple[str, str, None]:
    """Developer task: correct build errors in previously generated code.

    Returns (description, expected_output, output_pydantic) for CrewAI Task construction.
    Uses Pydantic output to prevent validation errors and ensure structured responses.
    """
    files_text = "\n".join(f"  - {f}" for f in failed_files) if failed_files else "  (none)"

    task_description = f"""\
Fix build errors for task {task_id}.

BUILD ERRORS:
{build_errors}

FAILED FILES (focus on these):
{files_text}

WORKFLOW:
1. Read each failed file to see current content
2. Analyze the build errors to understand what's wrong
3. Look up correct imports using your available tools
4. Query architecture facts if needed for correct types/interfaces
5. Write the COMPLETE fixed file
6. REPEAT for all failed files

RULES:
- Fix ONLY the build errors — do not refactor or change functionality
- Generate COMPLETE file content (not fragments)
- Preserve all existing business logic
- If an error is in a file you didn't generate, read it and fix it too

OUTPUT FORMAT (structured JSON):
After fixing ALL files, return a JSON object with this structure:
{{
  "task_id": "{task_id}",
  "files_fixed": [
    {{"file_path": "file1.ts", "status": "SUCCESS", "action": "modify", "message": "Fixed import error"}},
    {{"file_path": "file2.ts", "status": "SUCCESS", "action": "modify", "message": "Resolved type mismatch"}}
  ],
  "total_failed": {len(failed_files)},
  "summary": "Fixed X of Y files with build errors"
}}

DO NOT call any more tools after writing all files - just return the JSON.
"""
    expected = (
        f"A summary of which files were fixed for task {task_id}. "
        f"List each file path and what was changed."
    )
    return task_description, expected, None
