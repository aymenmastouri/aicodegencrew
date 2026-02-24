"""Triage Crew Task — embeds all context for dual-output synthesis."""

from crewai import Agent, Task


def create_triage_task(
    agent: Agent,
    task_context: str,
    findings_summary: str,
    supplementary_context: str,
    *,
    is_bug: bool = False,
) -> Task:
    """Create the triage synthesis task.

    All deterministic findings and supplementary context are injected directly
    into the task description so the agent has full context.

    Args:
        agent:                 The triage analyst agent.
        task_context:          Issue title + description + parsed task info.
        findings_summary:      Pre-computed deterministic findings (JSON text).
        supplementary_context: Requirements + logs text.
        is_bug:                Whether the issue is classified as a bug.
    """
    if is_bug:
        steps = """\
STEPS:
1. Review the classification and deterministic findings.
2. VALIDATE: Is this really a bug? Check the codebase context — could it be:
   - User error / misunderstanding?
   - Missing feature / enhancement?
   - Configuration issue?
   - Already fixed in another branch?
   - Working as designed?
3. Use query_facts(category="components") to understand which architectural layer/container this issue belongs to.
4. Use query_facts for the MOST RELEVANT dimensions (technologies, patterns, conventions, etc.) — summarize what the developer NEEDS TO KNOW for this specific issue.
5. Provide the BIG PICTURE: Where does this issue sit in the overall architecture?
6. Define the SCOPE: What parts of the system are involved? What is NOT involved?
7. Produce JSON output."""
    else:
        steps = """\
STEPS:
1. Review the issue context and deterministic findings.
2. Use query_facts(category="components") to understand which architectural layer/container this affects.
3. Use query_facts for the MOST RELEVANT dimensions (technologies, patterns, conventions, etc.) — summarize what the developer NEEDS TO KNOW for this specific issue.
4. Provide the BIG PICTURE: Where does this fit in the overall architecture?
5. Define the SCOPE: What parts of the system need attention? What is out of scope?
6. Produce JSON output."""

    return Task(
        description=f"""TASK: Analyse Issue Context and Produce Dual Output

You must analyse the issue and findings below, then produce a JSON response
with two sections: `customer_summary` and `developer_context`.

--- ISSUE CONTEXT ---
{task_context}
--- END ISSUE CONTEXT ---

--- SUPPLEMENTARY CONTEXT (requirements, logs) ---
{supplementary_context or "(none)"}
--- END SUPPLEMENTARY ---

--- DETERMINISTIC FINDINGS ---
{findings_summary}
--- END FINDINGS ---

{steps}

OUTPUT FORMAT (strict JSON):
{{
  "customer_summary": {{
    "summary": "Plain-language explanation of the issue for non-technical stakeholders",
    "impact_level": "low|medium|high|critical",
    "is_bug": true/false,
    "workaround": "Suggested workaround if any, or empty string",
    "eta_category": "quick-fix|short|medium|long|unknown"
  }},
  "developer_context": {{
    "big_picture": "Architectural context — which layers, containers, patterns are involved",
    "scope_boundary": "What's IN scope vs OUT of scope for this issue",
    "classification_assessment": "For bugs: is the classification correct? Reasoning. For CR/Task: empty string",
    "affected_components": ["ComponentName1 (layer)", "ComponentName2 (layer)"],
    "relevant_dimensions": [
      {{"dimension": "Technologies", "insight": "What the developer needs to know about the tech stack here"}},
      {{"dimension": "Patterns", "insight": "Relevant design patterns used in this area"}},
      {{"dimension": "Conventions", "insight": "Coding conventions the developer should follow"}}
    ],
    "architecture_notes": "Relevant patterns, constraints, risks to be aware of",
    "linked_tasks": []
  }}
}}

IMPORTANT:
- customer_summary must be understandable by non-technical people
- developer_context must focus on Big Picture and Scope — NO action steps, NO file paths, NO root cause
- affected_components are high-level component names, NOT file paths
- relevant_dimensions: query the MOST RELEVANT dimensions only (2-5), not all of them. Each insight should be specific to THIS issue, not generic.
- If data is insufficient, mark as "needs investigation"
- NEVER propose solutions or action steps — that is the Plan phase's job
""",
        expected_output=(
            "A JSON object with customer_summary and developer_context sections "
            "providing big-picture context and scope for both audiences."
        ),
        agent=agent,
    )
