"""Implement Crew: Task definitions for hierarchical manager-driven execution.

Three tasks:
1. implement_task — Manager delegates code changes to Developer
2. build_task — Manager delegates build verification to Builder
3. test_task — Manager delegates test generation to Tester
"""

from __future__ import annotations


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
) -> tuple[str, str]:
    """Manager task: coordinate code implementation via delegation.

    Returns (description, expected_output) for CrewAI Task construction.
    """
    ordered = "\n".join(f"  {i+1}. {p}" for i, p in enumerate(dependency_order)) if dependency_order else "  (none)"
    steps_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(implementation_steps)) if implementation_steps else "  (none)"
    type_instructions = _get_type_instructions(task_type, upgrade_plan)

    task_description = f"""\
Implement code changes for task {task_id}.

TASK: {summary}
TYPE: {task_type}

{type_instructions}

DESCRIPTION:
{description}

IMPLEMENTATION STEPS:
{steps_text}

WORKFLOW — for EACH file in the dependency order below:
1. Read the current file content with read_file(file_path)
2. Look up correct imports with lookup_import(symbol, from_file, language)
3. Check dependencies with lookup_dependencies(file_path)
4. Query architecture facts and RAG search as needed
5. Generate the modified file content
6. Write the COMPLETE file via write_code(file_path, content, action="modify")

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
# TASK 2: BUILD VERIFICATION
# =============================================================================


def build_task(
    *,
    container_ids: list[str],
) -> tuple[str, str]:
    """Manager task: coordinate build verification via Builder agent.

    Returns (description, expected_output) for CrewAI Task construction.
    """
    cid_list = ", ".join(container_ids) if container_ids else "(none)"

    task_description = f"""\
Verify the build for affected containers: {cid_list}

WORKFLOW per container:
1. Call run_build(container_id, baseline=true) to verify baseline compiles
2. If baseline FAILS: report baseline_broken and skip staged build
3. Call run_build(container_id, baseline=false) to build with staged changes
4. If staged build FAILS: call parse_build_errors(build_output)

If a staged build fails:
- Report the structured errors back
- The manager should delegate fix instructions to the Developer
- After fix, re-run build (max 3 attempts per container)

OUTPUT FORMAT per container:
- build_passed: true/false
- baseline_broken: true/false
- container_id: <id>
- exit_code: <number>
- error_count: <number>
- error_summary: <structured errors with file paths and line numbers>
"""

    expected = (
        "Build verification result per container: pass/fail status, "
        "exit codes, and structured error summaries if failed."
    )
    return task_description, expected


# =============================================================================
# TASK 3: TEST GENERATION
# =============================================================================


def test_task(
    *,
    changed_files: list[str],
) -> tuple[str, str]:
    """Manager task: coordinate test generation via Tester agent.

    Returns (description, expected_output) for CrewAI Task construction.
    """
    files_text = "\n".join(f"  - {p}" for p in changed_files) if changed_files else "  (none)"

    task_description = f"""\
Generate unit tests for the changed files:
{files_text}

WORKFLOW per file:
1. Call query_test_patterns() to discover existing test framework and style
2. Call rag_query("test for <ComponentName>") to find similar test examples
3. Call read_file(file_path) to read the modified source file
4. Determine the correct test file path using existing conventions:
   - Java: src/test/java/... (mirror the main source path)
   - TypeScript: same directory as source with .spec.ts suffix
5. Call write_test(file_path, content, tested_component) with the complete test file

TEST GUIDELINES:
- Match the same test framework (JUnit 5, Jasmine, Jest, etc.)
- Follow existing assertion style and mocking patterns
- Test both happy path and at least one error/edge case
- Include proper imports matching the project test configuration

IMPORTANT:
- Generate tests for ALL changed files (not just one)
- Use write_test() (not write_code()) to write test files
- Each test file must be self-contained and compilable
"""

    expected = "Summary of generated test files: file paths, components tested, and test count per file."
    return task_description, expected
