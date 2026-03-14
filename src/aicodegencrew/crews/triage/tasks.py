"""Triage Crew Tasks — analyst synthesis + reviewer validation (mini-crew)."""

from crewai import Agent, Task


def create_triage_task(
    agent: Agent,
    task_context: str,
    findings_summary: str,
    supplementary_context: str,
    *,
    is_bug: bool = False,
    analysis_inputs: str = "",
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
        analysis_inputs:       Pre-loaded analysis data from knowledge/extract.
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
3. Review the ANALYSIS INPUTS below — they contain raw facts from the codebase.
4. For EACH relevant fact: What does it MEAN for this issue? What constraint, risk, or boundary does it create?
5. Provide the BIG PICTURE (North Star): What is this project? Who is the customer? What problem does this solve? Why is this task needed NOW?
6. ARCHITECTURE WALKTHROUGH: Where does this piece fit? Which container, which layer, what neighbors?
7. Define the SCOPE: What parts of the system are involved (IN)? What is NOT involved (OUT)?
8. ANTICIPATED QUESTIONS: What would a developer ask before starting? Answer 3-5 obvious questions.
9. Produce JSON output."""
    else:
        steps = """\
STEPS:
1. Review the issue context, deterministic findings, AND the SUPPLEMENTARY CONTEXT (requirements, references, logs).
2. Review the ANALYSIS INPUTS below — they contain raw facts from the codebase.
3. For EACH relevant fact: What does it MEAN for this issue? What constraint, risk, or boundary does it create?
4. Provide the BIG PICTURE (North Star): What is this project? Who is the customer? What problem does this solve? Why is this task needed NOW? What happens if we DON'T do it?
5. ARCHITECTURE WALKTHROUGH: Where does this piece fit in the architecture? Which container, which layer? What are the neighbors? The developer should know WHERE their work fits.
6. Define the SCOPE: What parts of the system need attention (IN)? What is out of scope (OUT)?
7. ANTICIPATED QUESTIONS: What would a developer ask before starting work? Think like a junior dev seeing this ticket for the first time. Answer 3-5 obvious questions.
8. Produce JSON output."""

    analysis_block = f"""
--- ANALYSIS INPUTS (DO NOT REPEAT — ANALYZE!) ---
The following are RAW FACTS from the codebase. Your job is to ANALYZE what they MEAN
for this specific issue, NOT to copy them into your output.

ANALYSIS RULE: For each fact, explain what it MEANS for this issue.
Example: "ServiceB delegates to ServiceA via internal API — changes here must
verify the cross-boundary contract."

{analysis_inputs or "(none available)"}
--- END ANALYSIS INPUTS ---
""" if analysis_inputs else ""

    return Task(
        description=f"""TASK: Analyse Issue Context and Produce Dual Output

You must analyse the issue and findings below, then produce a JSON response
with two sections: `customer_summary` and `developer_context`.

Your output serves ONE PURPOSE: after reading it, a developer should UNDERSTAND
the task deeply before writing a single line of code. No guessing, no ambiguity.

--- ISSUE CONTEXT ---
{task_context}
--- END ISSUE CONTEXT ---

--- SUPPLEMENTARY CONTEXT (requirements, logs) ---
{supplementary_context or "(none)"}
--- END SUPPLEMENTARY ---

--- DETERMINISTIC FINDINGS ---
{findings_summary}
--- END FINDINGS ---
{analysis_block}
{steps}

OUTPUT FORMAT (strict JSON):
{{
  "customer_summary": {{
    "summary": "Plain-language explanation INCLUDING why this is needed. Not just WHAT, but WHY and what happens if we don't do it.",
    "impact_level": "low|medium|high|critical",
    "is_bug": true/false,
    "workaround": "Suggested workaround if any, or empty string",
    "eta_category": "quick-fix|short|medium|long|unknown"
  }},
  "developer_context": {{
    "big_picture": "NORTH STAR — answer these: (1) What is this project/system about? (2) Who uses it? (3) What problem does THIS task solve? (4) Why is it needed NOW? (5) What happens if we don't do it?",
    "scope_boundary": "What's IN scope vs OUT of scope for this issue",
    "classification_assessment": "For bugs: structured argument with evidence FOR and AGAINST. For CR/Task: empty string",
    "classification_confidence": 0.0-1.0 or -1,
    "affected_components": ["ComponentName1 (layer)", "ComponentName2 (layer)"],
    "context_boundaries": [
      {{
        "category": "integration_boundary|technology_constraint|dependency_risk|pattern_constraint|data_boundary|security_boundary|testing_constraint|workflow_constraint|infrastructure_constraint",
        "boundary": "What does this fact MEAN for this issue? What constraint or risk arises?",
        "severity": "info|caution|blocking",
        "source_facts": ["tech_versions.json: LibX 6.4.3", "relations.json: ServiceA -> ServiceB"]
      }}
    ],
    "architecture_notes": "WALKTHROUGH: Where does this piece fit in the architecture? Which container(s), which layer(s)? What are the neighboring components? How do they connect? A developer reading this should know EXACTLY where their work fits — like a map with 'YOU ARE HERE'.",
    "anticipated_questions": [
      {{
        "question": "An obvious question a developer would ask before starting",
        "answer": "The answer based on what you know from the codebase analysis"
      }}
    ],
    "linked_tasks": ["Related task IDs or descriptions if identifiable from context"]
  }}
}}

RULES:
- context_boundaries: 2-6 boundaries, each must explain what a fact MEANS (not data copy), include source_facts citing extract file names, and use correct severity (info/caution/blocking)
- If analysis inputs are pre-loaded, use them — do not repeat query_facts calls for data already provided
- Triage is for UNDERSTANDING only — do not propose solutions or action steps
""",
        expected_output=(
            "A JSON object with customer_summary and developer_context sections "
            "providing big-picture context, scope boundaries, architectural walkthrough, "
            "anticipated questions, and analytical insights."
        ),
        agent=agent,
    )


def create_review_task(reviewer_agent: Agent) -> Task:
    """Create the triage quality review task.

    The reviewer validates the Context Analyst's output and fixes quality issues.
    Runs as Task 2 in the sequential mini-crew — receives Task 1's output as context.
    """
    return Task(
        description="""\
TASK: Review and Validate Triage Synthesis Output

You receive the output from the Issue Context Analyst (Task 1). Your job is to
VALIDATE it against quality standards and FIX any issues.

QUALITY CHECKLIST — check each point:

1. big_picture (NORTH STAR):
   - Must answer: What? Who? Why? Why NOW? What if we don't?
   - Must be at least 2-3 sentences, not a single vague line
   - Must contain a motivation word (why, because, needed, risk, etc.)
   - FAIL if empty, too short (<50 chars), or missing WHY

2. scope_boundary:
   - Must explicitly state what's IN scope and OUT of scope
   - FAIL if it doesn't mention both IN and OUT

3. architecture_notes (WALKTHROUGH):
   - Must show WHERE the work fits: container → layer → component → neighbors
   - Must be at least 2 sentences
   - FAIL if it's just "See components" or a single-line placeholder

4. anticipated_questions:
   - Must have 3-5 developer-relevant Q&A pairs
   - Questions must be specific to THIS issue (not generic like "How to test?")
   - Answers must be concrete and based on codebase knowledge
   - FAIL if fewer than 3 questions

5. context_boundaries:
   - Must be ANALYTICAL (explain what facts MEAN for this issue)
   - Must NOT be data copies (just listing versions/names = FAIL)
   - Each must have source_facts citing file names
   - Must have at least 2 boundaries
   - FAIL if boundaries are just version listings

6. customer_summary:
   - summary must explain WHY, not just WHAT
   - impact_level must be appropriate
   - is_bug must be correct

7. NO ACTION STEPS:
   - Remove any "implement", "modify", "create", "fix the" instructions
   - Triage context is for UNDERSTANDING, not PLANNING

INSTRUCTIONS:
- If ALL checks pass: return the JSON UNCHANGED
- If issues found: FIX them and return the CORRECTED JSON
- Your output must be VALID JSON with the same structure
- Do NOT add new fields or change the structure
- Do NOT add explanatory text outside the JSON""",
        expected_output=(
            "A validated and potentially corrected JSON object with customer_summary "
            "and developer_context, meeting all quality standards."
        ),
        agent=reviewer_agent,
    )
