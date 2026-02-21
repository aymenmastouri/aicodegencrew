"""Phase 7: Review Crew Agent."""

from crewai import Agent

from ...shared.tools import FactsQueryTool, RAGQueryTool, SymbolQueryTool
from ...shared.utils.llm_factory import create_llm


def create_quality_reviewer(facts_dir: str, chroma_dir: str) -> Agent:
    """Create the Architecture Quality Reviewer agent.

    Queries architecture facts and codebase snippets via tools, then
    synthesises all deterministic findings into a Markdown quality report.

    Args:
        facts_dir:  Path to dimension files (e.g. ``knowledge/extract``).
        chroma_dir: Path to ChromaDB directory (e.g. ``knowledge/discover``).
    """
    return Agent(
        role="Architecture Quality Reviewer",
        goal=(
            "Synthesise consistency-check results and quality findings into a "
            "comprehensive, actionable architecture quality report in Markdown."
        ),
        backstory=(
            "You are a senior architecture quality engineer with deep expertise in "
            "C4 model and arc42 documentation standards. "
            "You analyse consistency between architecture facts and generated "
            "documentation, identify gaps, hallucinations, and placeholder text, "
            "and produce a clear quality report with prioritised recommendations."
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
