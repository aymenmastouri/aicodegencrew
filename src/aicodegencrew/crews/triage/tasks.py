"""Triage Crew Task — embeds all context for dual-output synthesis."""

from crewai import Agent, Task


def create_triage_task(
    agent: Agent,
    task_context: str,
    findings_summary: str,
    supplementary_context: str,
    *,
    is_bug: bool = False,
    dimension_context: str = "",
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
        dimension_context:     Pre-loaded architectural dimension data.
    """
    if is_bug:
        steps = """\
STEPS:
1. Review the classification, deterministic findings, AND the SUPPLEMENTARY CONTEXT (requirements, references, logs) carefully.
2. VALIDATE: Is this really a bug? Build a structured argument:
   a) List evidence FOR it being a bug (error logs, stack traces, spec violations, reference documents).
   b) List evidence AGAINST (user error, missing feature, config issue, working as designed).
   c) Check supplementary references (PDFs, requirements docs) — do they confirm or contradict the bug claim?
   d) Rate your confidence and explain your reasoning.
3. Review the PRE-LOADED DIMENSIONS below — they contain the architectural context already.
4. Provide the BIG PICTURE: Where does this issue sit in the overall architecture?
5. Define the SCOPE: What parts of the system are involved? What is NOT involved?
6. Summarize the relevant dimensions into developer-friendly insights.
7. Produce JSON output."""
    else:
        steps = """\
STEPS:
1. Review the issue context, deterministic findings, AND the SUPPLEMENTARY CONTEXT (requirements, references, logs).
2. Review the PRE-LOADED DIMENSIONS below — they contain the architectural context already.
3. Provide the BIG PICTURE: Where does this fit in the overall architecture? Use references/requirements to understand the intent.
4. Define the SCOPE: What parts of the system need attention? What is out of scope?
5. Summarize the relevant dimensions into developer-friendly insights.
6. Produce JSON output."""

    dimension_block = f"""
--- PRE-LOADED DIMENSIONS (from knowledge/extract) ---
{dimension_context or "(none available)"}
--- END DIMENSIONS ---
""" if dimension_context else ""

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
{dimension_block}
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
    "classification_assessment": "For bugs: structured argument — evidence FOR being a bug, evidence AGAINST, reference to supplementary docs. For CR/Task: empty string",
    "classification_confidence": 0.0-1.0 or -1,
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
- relevant_dimensions: summarize the PRE-LOADED DIMENSIONS into 2-5 developer-friendly insights. Each insight must be specific to THIS issue, not generic.
- classification_assessment: For bugs, provide a STRUCTURED ARGUMENT: what evidence supports it being a bug, what contradicts it, and reference any supplementary documents (requirements, PDFs) that confirm or deny the claim.
- classification_confidence: For bugs, rate 0.0 (definitely NOT a bug) to 1.0 (confirmed bug). For CR/Task set to -1.
- If dimensions are pre-loaded, use them directly — do NOT waste tool calls on query_facts for dimensions.
- If data is insufficient, mark as "needs investigation"
- NEVER propose solutions or action steps — that is the Plan phase's job
""",
        expected_output=(
            "A JSON object with customer_summary and developer_context sections "
            "providing big-picture context and scope for both audiences."
        ),
        agent=agent,
    )
