"""Triage Crew Task — embeds all context for dual-output synthesis."""

from crewai import Agent, Task


def create_triage_task(
    agent: Agent,
    task_context: str,
    findings_summary: str,
    supplementary_context: str,
) -> Task:
    """Create the triage synthesis task.

    All deterministic findings and supplementary context are injected directly
    into the task description so the agent has full context.

    Args:
        agent:                 The triage analyst agent.
        task_context:          Issue title + description + parsed task info.
        findings_summary:      Pre-computed deterministic findings (JSON text).
        supplementary_context: Requirements + logs text.
    """
    return Task(
        description=f"""TASK: Triage Issue and Produce Dual Output

You must analyse the issue and findings below, then produce a JSON response
with two sections: `customer_summary` and `developer_brief`.

--- ISSUE CONTEXT ---
{task_context}
--- END ISSUE CONTEXT ---

--- SUPPLEMENTARY CONTEXT (requirements, logs) ---
{supplementary_context or "(none)"}
--- END SUPPLEMENTARY ---

--- DETERMINISTIC FINDINGS ---
{findings_summary}
--- END FINDINGS ---

STEPS:
1. Review the classification, entry points, and blast radius from findings.
2. Use query_facts(category="components") to verify affected components.
3. Use rag_query to find relevant code context for root cause analysis.
4. (Optional) Use symbol_query to locate specific classes/methods mentioned.
5. Produce JSON output with BOTH sections.

OUTPUT FORMAT (strict JSON):
{{
  "customer_summary": {{
    "summary": "Plain-language explanation of the issue for non-technical stakeholders",
    "impact_level": "low|medium|high|critical",
    "is_bug": true/false,
    "workaround": "Suggested workaround if any, or empty string",
    "eta_category": "quick-fix|short|medium|long|unknown"
  }},
  "developer_brief": {{
    "root_cause_hypothesis": "Technical root cause analysis",
    "affected_files": ["path/to/file1.java", "path/to/file2.ts"],
    "affected_components": ["ComponentName1", "ComponentName2"],
    "action_steps": [
      "1. Fix X in ComponentName (path/to/file.java) — description",
      "2. Update Y in AnotherComponent (path/to/other.ts) — description"
    ],
    "linked_tasks": ["TASK-123"],
    "test_strategy": "Describe what tests to write/run",
    "architecture_notes": "Any architectural concerns or patterns to follow"
  }}
}}

IMPORTANT:
- customer_summary must be understandable by non-technical people
- developer_brief action_steps MUST include file paths
- If data is insufficient, mark as "needs investigation"
""",
        expected_output=(
            "A JSON object with customer_summary and developer_brief sections "
            "providing actionable triage information for both audiences."
        ),
        agent=agent,
    )
