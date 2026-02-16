"""Implement Crew: Task definitions for single-agent execution.

Two tasks:
1. implement_task — Developer implements all code changes
2. fix_task — Developer fixes build errors from previous attempt
"""

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
) -> tuple[str, str]:
    """Developer task: implement code changes using all available tools.

    Returns (description, expected_output) for CrewAI Task construction.
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
1. FIRST call read_task_source(task_id="{task_id}") and use it as intent source.
2. Treat read_plan() and implementation_steps as GUIDANCE, not ground truth.
3. Resolve conflicts by prioritizing: actual task source -> architecture facts -> codebase evidence.
4. For each major change, call facts_query and rag_query before code writing.
5. Never implement requirements that are only in the plan but absent from the original task/evidence.

DESCRIPTION:
{description}

IMPLEMENTATION STEPS:
{steps_text}

WORKFLOW — for EACH file in the dependency order below:
1. Re-check task intent with read_task_source(task_id) when scope is unclear
2. Read current file content with read_file(file_path)
3. Look up correct imports with lookup_import(symbol, from_file, language)
4. Check dependencies with lookup_dependencies(file_path)
5. Query architecture facts and RAG search as needed
6. Generate modified file content
7. Write COMPLETE file via write_code(file_path, content, action="modify")

FILES IN DEPENDENCY ORDER (process in this order):
{ordered}

IMPORTANT:
- Generate COMPLETE file content (not fragments or patches)
- Preserve existing imports, annotations, and formatting
- Process ALL files — do not skip any
- If a file cannot be modified, include an error note in the output
"""

    expected = (
        f"Summary of all files written to staging via write_code() for task {task_id}, "
        f"including file paths, actions taken, and any issues encountered."
    )
    return task_description, expected


# =============================================================================
# TASK 2: FIX BUILD ERRORS
# =============================================================================


def fix_task(
    *,
    task_id: str,
    build_errors: str,
    failed_files: list[str],
    dependency_order: list[str],
) -> tuple[str, str]:
    """Developer task: correct build errors in previously generated code.

    Returns (description, expected_output) for CrewAI Task construction.
    """
    files_text = "\n".join(f"  - {f}" for f in failed_files) if failed_files else "  (none)"

    task_description = f"""\
Fix build errors for task {task_id}.

BUILD ERRORS:
{build_errors}

FAILED FILES (focus on these):
{files_text}

WORKFLOW:
1. Read each failed file with read_file(file_path) to see current content
2. Analyze the build errors to understand what's wrong
3. Look up correct imports with lookup_import(symbol, from_file, language)
4. Query architecture facts if needed for correct types/interfaces
5. Write the COMPLETE fixed file via write_code(file_path, content, action="modify")

RULES:
- Fix ONLY the build errors — do not refactor or change functionality
- Generate COMPLETE file content (not fragments)
- Preserve all existing business logic
- If an error is in a file you didn't generate, read it and fix it too
"""
    expected = f"Summary of fixed files for task {task_id} with build errors resolved."
    return task_description, expected
