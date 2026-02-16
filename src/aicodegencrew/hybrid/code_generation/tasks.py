"""
Implement Crew - Task Templates
================================
Dynamic task descriptions for code generation, build verification,
build healing, test generation, and build fixer (CrewAI fallback).

Each function returns (description, expected_output) for CrewAI Task construction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .schemas import CodegenPlanInput, FileContext


# =============================================================================
# TASK-TYPE INSTRUCTIONS (replaces strategy.build_prompt)
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
# MINI-CREW A: CODE GENERATION
# =============================================================================


def code_generation_task(
    container: dict,
    plan: CodegenPlanInput,
    files: list[FileContext],
) -> tuple[str, str]:
    """Build task description for code generation (Mini-Crew A).

    Args:
        container: Dict with id, name, root_path, build_system, language.
        plan: The validated plan input.
        files: FileContext objects for this container.

    Returns:
        (description, expected_output) tuple for CrewAI Task.
    """
    container_name = container.get("name", "unknown")
    container_id = container.get("id", "unknown")

    file_list = "\n".join(f"  - {f.file_path} ({f.language})" for f in files)
    steps_text = "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(plan.implementation_steps))
    type_instructions = _get_type_instructions(plan.task_type, plan.upgrade_plan)

    description = f"""\
Generate code changes for container "{container_name}" ({container_id}).

TASK: {plan.summary}
TYPE: {plan.task_type}

{type_instructions}

DESCRIPTION:
{plan.description}

IMPLEMENTATION STEPS:
{steps_text}

FILES TO MODIFY:
{file_list}

WORKFLOW — for EACH file listed above:
1. Call read_file(file_path) to read the current source code
2. Call query_facts(category="components") to understand the component's role and relations
3. Call rag_query("...") to search for related patterns or examples in the codebase
4. Apply the implementation steps to generate the modified file content
5. Call write_code(file_path, content, action="modify") with the COMPLETE file content

IMPORTANT:
- Generate COMPLETE file content (not fragments or patches)
- Preserve existing imports, annotations, and formatting
- Process ALL files in the list — do not skip any
- If a file cannot be modified, call write_code with action="modify" and include an error comment"""

    expected_output = (
        f"For container '{container_name}': a summary of all files written to staging "
        f"via write_code(), including file paths, actions taken, and any issues encountered. "
        f"Expected {len(files)} files processed."
    )

    return description, expected_output


# =============================================================================
# MINI-CREW B: BUILD VERIFICATION + HEALING
# =============================================================================


def build_verify_task(
    container_name: str,
    container_id: str,
) -> tuple[str, str]:
    """Build task description for build verification (Mini-Crew B, Task 1).

    Args:
        container_name: Human-readable container name (e.g. "backend").
        container_id: Container identifier (e.g. "container.backend").

    Returns:
        (description, expected_output) tuple for CrewAI Task.
    """
    description = f"""\
Verify the build for container "{container_name}" ({container_id}).

WORKFLOW — follow this EXACT sequence:
1. Call run_build(container_id="{container_id}", baseline=True) to verify the baseline compiles
2. If baseline FAILS: report baseline_broken=true and STOP — do not attempt staged build
3. Call run_build(container_id="{container_id}") to build with staged changes applied
4. If staged build FAILS: call parse_build_errors(build_output) to get structured error list
5. Report results clearly

OUTPUT FORMAT — include these fields:
- build_passed: true/false
- baseline_broken: true/false
- container_id: {container_id}
- container_name: {container_name}
- exit_code: <number>
- error_count: <number> (0 if passed)
- error_summary: <string> (list of errors with file paths and line numbers)"""

    expected_output = (
        f"Build verification result for '{container_name}': "
        f"build_passed (true/false), baseline status, exit code, "
        f"and structured error summary if build failed."
    )

    return description, expected_output


def build_heal_task(
    container: dict,
    task_id: str,
    error_summary: str,
) -> tuple[str, str]:
    """Build task description for build healing (Mini-Crew B, Task 2).

    Args:
        container: Dict with id, name, root_path, build_system, language.
        task_id: The plan task identifier.
        error_summary: Build error output from the DevOps agent.

    Returns:
        (description, expected_output) tuple for CrewAI Task.
    """
    container_name = container.get("name", "unknown")
    container_id = container.get("id", "unknown")

    # Truncate error summary to avoid exceeding context window
    truncated = error_summary[:3000] if len(error_summary) > 3000 else error_summary

    description = f"""\
Fix build errors for container "{container_name}" ({container_id}).
Task ID: {task_id}

The DevOps engineer found build errors. Fix them by modifying the staged files.

BUILD ERROR SUMMARY:
{truncated}

WORKFLOW — for EACH file with errors:
1. Call read_file(file_path) to read the current source (with staged changes applied)
2. Call query_facts(category="components") if you need to understand types or imports
3. Call rag_query("...") to find correct API usage or import patterns
4. Fix the compilation errors in the file
5. Call write_code(file_path, content, action="modify") with the corrected COMPLETE file

IMPORTANT:
- Fix ONLY the reported errors — do not refactor or add features
- Preserve all intentional changes from the previous code generation
- If an error is in an import, verify the correct import path using rag_query
- Generate COMPLETE file content, not just the fixed lines"""

    expected_output = (
        f"Summary of files healed for '{container_name}': "
        f"list of file paths modified via write_code(), errors fixed, "
        f"and any remaining issues that could not be resolved."
    )

    return description, expected_output


# =============================================================================
# MINI-CREW C: TEST GENERATION
# =============================================================================


def test_generation_task(
    container: dict,
    task_id: str,
    files: list[str],
) -> tuple[str, str]:
    """Build task description for test generation (Mini-Crew C).

    Args:
        container: Dict with id, name, root_path, build_system, language.
        task_id: The plan task identifier.
        files: List of file paths that were modified.

    Returns:
        (description, expected_output) tuple for CrewAI Task.
    """
    container_name = container.get("name", "unknown")
    container_id = container.get("id", "unknown")

    file_list = "\n".join(f"  - {f}" for f in files)

    description = f"""\
Generate unit tests for the modified files in container "{container_name}" ({container_id}).
Task ID: {task_id}

FILES THAT WERE MODIFIED:
{file_list}

WORKFLOW — for EACH modified file:
1. Call query_test_patterns(container="{container_name}") to discover existing test style
2. Call rag_query("test for <ComponentName>") to find similar test examples
3. Call read_file(file_path) to read the modified source file
4. Determine the correct test file path using existing test directory conventions
5. Call write_test(file_path, content, tested_component) with the complete test file

TEST GUIDELINES:
- Use the same test framework found by query_test_patterns (JUnit 5, Jasmine, Jest, etc.)
- Follow the same assertion style and mocking patterns as existing tests
- Place test files in the conventional location for the container:
  * Java: src/test/java/... (mirror the main source path)
  * TypeScript: same directory as source with .spec.ts suffix
- Test both happy path and at least one error/edge case
- Include proper imports matching the project's test configuration

IMPORTANT:
- Generate tests for ALL modified files (not just one)
- Use write_test() (not write_code()) to write test files
- Each test file must be self-contained and compilable"""

    expected_output = (
        f"Summary of test files generated for '{container_name}': "
        f"list of test file paths written via write_test(), "
        f"components tested, and test count per file."
    )

    return description, expected_output


# =============================================================================
# BUILD FIXER: Developer fix iteration (CrewAI fallback)
# =============================================================================


def build_fixer_fix_task(
    container_name: str,
    container_id: str,
    plan: "CodegenPlanInput",
    staged_files: list[str],
    build_errors: str,
    iteration: int,
    max_iterations: int,
) -> tuple[str, str]:
    """Build task description for the fixer developer agent.

    The fixer has FULL repo access — it can read/write any file,
    not just the ones in the original scope.

    Args:
        container_name: Human-readable container name.
        container_id: Container identifier.
        plan: The plan context (task_id, summary, upgrade_plan).
        staged_files: File paths currently in staging.
        build_errors: Raw build error output (truncated to 4000 chars).
        iteration: Current fixer iteration (1-based).
        max_iterations: Maximum fixer iterations.

    Returns:
        (description, expected_output) tuple for CrewAI Task.
    """
    changed_files = "\n".join(f"  - {fp}" for fp in staged_files)
    error_text = build_errors[:4000]

    upgrade_context = ""
    if plan.upgrade_plan:
        up = plan.upgrade_plan
        upgrade_context = (
            f"\nUPGRADE CONTEXT: {up.get('framework', '?')} "
            f"{up.get('from_version', '?')} -> {up.get('to_version', '?')}\n"
        )

    description = f"""\
Fix build errors for container "{container_name}" ({container_id}).
Task: {plan.task_id} — {plan.summary}
{upgrade_context}
This is fixer iteration {iteration}/{max_iterations}.
The build failed AFTER the pipeline already attempted to heal the errors.
The remaining errors are likely in files OUTSIDE the original scope.

FILES ALREADY MODIFIED (in staging):
{changed_files}

BUILD ERRORS TO FIX:
{error_text}

WORKFLOW:
1. Read the error output carefully — identify WHICH files have errors
2. For EACH file with errors:
   a. Call read_file(file_path) to read the current source
   b. If the file is already in staging, the read will include staged changes
   c. Fix the compilation/build error
   d. Call write_code(file_path, content, action="modify") with the COMPLETE fixed file
3. If errors reference files NOT in staging (cascading breakage):
   a. Read those files too — they may need imports or declarations updated
   b. Fix them and write_code() them as well
4. Use rag_query() to find correct import paths or API usage if unsure

IMPORTANT:
- You have FULL repo access — you are NOT limited to the original file scope
- Fix ONLY build errors — do not refactor or add features
- Generate COMPLETE file content, not fragments
- Pay attention to import statements and module declarations"""

    expected_output = (
        f"Summary of all files fixed via write_code() for {container_name}, "
        f"including newly-discovered files outside original scope."
    )

    return description, expected_output


# =============================================================================
# BUILD FIXER: DevOps build check (CrewAI fallback)
# =============================================================================


def build_fixer_verify_task(
    container_name: str,
    container_id: str,
    iteration: int,
) -> tuple[str, str]:
    """Build task description for the fixer DevOps build check.

    Args:
        container_name: Human-readable container name.
        container_id: Container identifier.
        iteration: Current fixer iteration (1-based).

    Returns:
        (description, expected_output) tuple for CrewAI Task.
    """
    description = f"""\
Verify the build for container "{container_name}" ({container_id}).
This is build check after fixer iteration {iteration}.

WORKFLOW:
1. Call run_build(container_id="{container_id}") to build with ALL staged changes
2. If build FAILS: call parse_build_errors(build_output) to get structured errors
3. Report results clearly

OUTPUT FORMAT:
- build_passed: true/false
- exit_code: <number>
- error_count: <number>
- error_summary: <detailed errors with file paths and line numbers>"""

    expected_output = (
        f"Build result for {container_name}: build_passed (true/false), "
        f"exit code, and error summary if failed."
    )

    return description, expected_output
