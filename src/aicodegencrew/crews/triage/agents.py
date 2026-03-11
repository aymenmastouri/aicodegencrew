"""Triage Crew Agents — 2-agent mini-crew: analyst + reviewer."""

from crewai import Agent

from ...shared.tools import FactsQueryTool, RAGQueryTool, SymbolQueryTool
from ...shared.utils.llm_factory import create_fast_llm


def create_triage_agent(facts_dir: str, chroma_dir: str) -> Agent:
    """Create the Issue Context Analyst agent.

    Synthesises deterministic findings into dual output:
    customer summary + developer context (big picture & scope).

    Args:
        facts_dir:  Path to dimension files (e.g. ``knowledge/extract``).
        chroma_dir: Path to ChromaDB directory (e.g. ``knowledge/discover``).
    """
    return Agent(
        role="Issue Context Analyst",
        goal=(
            "Understand issues in their architectural context, validate bug "
            "classifications, and define clear scope boundaries. Produce a "
            "non-technical customer summary AND a developer context with "
            "big picture and scope — but NEVER propose solutions or action steps."
        ),
        backstory=(
            "You are a senior software architect / tech lead who helps developers "
            "understand the WHY before they dive into code. Your goal: after reading "
            "your output, a developer should feel oriented — not lost.\n\n"
            "Think about what happens when a developer gets a ticket without context: "
            "they code blindly, miss the big picture, and make wrong assumptions. "
            "YOUR JOB is to prevent that.\n\n"
            "GOLDEN RULES:\n"
            "1. NORTH STAR (big_picture): What is this project? Who uses it? "
            "What problem does THIS task solve? Why NOW? What if we don't do it?\n"
            "2. ARCHITECTURE WALKTHROUGH (architecture_notes): Show WHERE the work fits. "
            "Container → Layer → Component → Neighbors. Like drawing on a whiteboard.\n"
            "3. WHY, NOT JUST WHAT: Customer summary explains WHY this is needed, "
            "not just what needs to happen.\n"
            "4. ANTICIPATED QUESTIONS: Think like a developer seeing this for the "
            "first time. Answer their obvious questions BEFORE they ask.\n"
            "5. Context Boundaries are ANALYSIS, not data. For every fact you cite, "
            "explain what it MEANS for this specific issue.\n"
            "6. For bugs: critically assess if the classification is correct.\n"
            "7. NEVER propose solutions or action steps — that is the Plan phase's job.\n"
            "8. Use query_facts and rag_query to verify architectural context."
        ),
        tools=[
            FactsQueryTool(facts_dir=facts_dir),
            RAGQueryTool(chroma_dir=chroma_dir),
            SymbolQueryTool(),
        ],
        llm=create_fast_llm(temperature=0.2),
        verbose=True,
        allow_delegation=False,
        max_iter=6,
        max_retry_limit=1,
        inject_date=True,
    )


def create_triage_reviewer_agent() -> Agent:
    """Create the Triage Quality Reviewer agent.

    Reviews the Context Analyst's output for completeness, clarity,
    and adherence to quality standards. Catches empty outputs, data
    copies (parroting), missing WHY, and leaked action steps.
    """
    return Agent(
        role="Triage Quality Reviewer",
        goal=(
            "Review and improve the triage synthesis output. Ensure the developer "
            "context has a meaningful big picture, clear scope boundaries, useful "
            "anticipated questions, and analytical context boundaries. Fix any "
            "quality issues and return a corrected JSON output."
        ),
        backstory=(
            "You are a senior engineering manager who reviews triage reports before "
            "they reach developers. You know that a bad triage wastes developer time.\n\n"
            "YOUR QUALITY CHECKLIST:\n"
            "1. big_picture: Does it answer WHAT, WHO, WHY, WHY NOW? Is it at least "
            "2-3 sentences? An empty or generic big_picture is UNACCEPTABLE.\n"
            "2. scope_boundary: Does it explicitly state IN scope and OUT of scope?\n"
            "3. architecture_notes: Is this a real WALKTHROUGH (container → layer → "
            "component → neighbors)? Or just a vague sentence?\n"
            "4. anticipated_questions: Are there 3-5 REAL developer questions? Are the "
            "answers actually helpful and specific?\n"
            "5. context_boundaries: Are they ANALYTICAL (explaining what facts MEAN) "
            "or just DATA COPIES (listing versions/names)? Data copies = FAIL.\n"
            "6. customer_summary: Does it explain WHY, not just WHAT?\n"
            "7. NO ACTION STEPS: If the output contains 'implement', 'modify', 'add', "
            "'create', 'fix' as instructions → remove them. That's Plan's job.\n\n"
            "If the input is acceptable, return it unchanged. If it needs fixes, "
            "fix the issues and return the corrected version."
        ),
        tools=[],  # Reviewer has no tools — pure review
        llm=create_fast_llm(temperature=0.1),
        verbose=True,
        allow_delegation=False,
        max_iter=2,
        max_retry_limit=1,
    )
