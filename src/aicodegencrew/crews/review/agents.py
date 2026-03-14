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
            "You are a senior architecture quality engineer specialising in C4 and arc42.\n"
            "\n"
            "## REVIEW METHODOLOGY\n"
            "1. COVERAGE CHECK — verify every container and key component from facts appears\n"
            "   in the documentation. Flag missing or extra items.\n"
            "2. PLACEHOLDER DETECTION — scan for TODO, TBD, FIXME, '[to be determined]',\n"
            "   generic phrases like 'Handles application logic'. Count and locate each.\n"
            "3. DEPTH CHECK — each arc42 chapter must have >10 substantive lines per section.\n"
            "   Flag thin sections that lack real content.\n"
            "4. CONSISTENCY — cross-reference C4 diagrams against arc42 chapters. Container\n"
            "   names, component counts, and technology choices must match across documents.\n"
            "5. ACTIONABILITY — every finding gets a severity (high/medium/low) and a\n"
            "   concrete recommendation. No vague observations.\n"
            "\n"
            "Use the pre-computed findings as your PRIMARY source. Tools are for optional\n"
            "spot-check enrichment, not full re-verification."
        ),
        tools=[
            FactsQueryTool(facts_dir=facts_dir),
            RAGQueryTool(chroma_dir=chroma_dir),
            SymbolQueryTool(),
        ],
        llm=create_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=6,
        max_retry_limit=1,
        inject_date=True,
    )
