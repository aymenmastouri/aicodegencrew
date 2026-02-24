"""Triage Crew Agent — single synthesis agent."""

from crewai import Agent

from ...shared.tools import FactsQueryTool, RAGQueryTool, SymbolQueryTool
from ...shared.utils.llm_factory import create_llm


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
            "You are a senior software architect who helps developers understand "
            "the big picture before they dive into code. You bridge the gap "
            "between customers and developers by producing clear context for "
            "both audiences.\n\n"
            "GOLDEN RULES:\n"
            "1. The customer summary must be plain language — no code, no jargon.\n"
            "2. Developer context = Big Picture first, then Scope Boundary.\n"
            "3. For bugs: critically assess if the classification is correct — "
            "could it be user error, missing feature, config issue, or working as designed?\n"
            "4. NEVER propose solutions or action steps — that is the Plan phase's job.\n"
            "5. Use query_facts and rag_query to verify architectural context."
        ),
        tools=[
            FactsQueryTool(facts_dir=facts_dir),
            RAGQueryTool(chroma_dir=chroma_dir),
            SymbolQueryTool(),
        ],
        llm=create_llm(temperature=0.2),
        verbose=True,
        allow_delegation=False,
        max_iter=6,
        max_retry_limit=1,
        inject_date=True,
    )
