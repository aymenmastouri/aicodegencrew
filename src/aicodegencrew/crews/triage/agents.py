"""Triage Crew Agent — single synthesis agent."""

from crewai import Agent

from ...shared.tools import FactsQueryTool, RAGQueryTool, SymbolQueryTool
from ...shared.utils.llm_factory import create_llm


def create_triage_agent(facts_dir: str, chroma_dir: str) -> Agent:
    """Create the Issue Triage Analyst agent.

    Synthesises deterministic findings into dual output:
    customer summary + developer brief.

    Args:
        facts_dir:  Path to dimension files (e.g. ``knowledge/extract``).
        chroma_dir: Path to ChromaDB directory (e.g. ``knowledge/discover``).
    """
    return Agent(
        role="Issue Triage Analyst",
        goal=(
            "Analyse issue reports and deterministic findings to produce "
            "a non-technical customer summary AND a detailed technical "
            "developer brief with file paths, root cause hypothesis, "
            "and prioritised action steps."
        ),
        backstory=(
            "You are a senior software engineer and support lead with deep "
            "expertise in triaging production issues. You bridge the gap "
            "between customers and developers by producing clear, actionable "
            "summaries for both audiences.\n\n"
            "GOLDEN RULES:\n"
            "1. The customer summary must be plain language — no code, no jargon.\n"
            "2. The developer brief MUST include file paths and component names.\n"
            "3. Action steps must be specific: 'Fix X in Y (path/to/file.java)'\n"
            "4. When unsure, say 'needs investigation' rather than guessing.\n"
            "5. Use query_facts and rag_query to verify your hypotheses."
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
