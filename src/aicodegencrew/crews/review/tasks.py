"""Phase 7: Review Crew Task."""

from crewai import Agent, Task


def create_synthesis_task(
    agent: Agent,
    findings_summary: str,
    output_path: str,
) -> Task:
    """Create the synthesis task that turns deterministic findings into a Markdown report.

    The deterministic findings are injected directly into the task description so
    the agent has the full context without needing to read from disk.

    Args:
        agent:            The quality reviewer agent.
        findings_summary: Pre-computed consistency + quality findings (JSON text).
        output_path:      Absolute path where the Markdown report will be written
                          by the crew (informational — actual write is done by
                          ReviewCrew._run_llm_synthesis after crew.kickoff()).
    """
    return Task(
        description=f"""TASK: Generate Architecture Quality Report

You have been provided with pre-computed consistency and quality findings below.
Your job is to synthesise them into a professional architecture quality report.

--- DETERMINISTIC FINDINGS ---
{findings_summary}
--- END FINDINGS ---

STEPS:
1. Use query_facts(category="containers") to verify the container names from
   source facts and enrich the coverage analysis.
2. Use query_facts(category="components", limit=20) to spot-check component
   coverage in the generated documentation.
3. (Optional) Use rag_query to find specific code evidence for critical gaps.
4. Write a complete Markdown report with the following sections:

   ## Executive Summary
   - Overall quality score (given in findings above)
   - Top 3 findings by severity (high / medium / low)

   ## Consistency Analysis
   - Container coverage: missing vs. extra containers
   - Component coverage: spot-check result
   - Arc42 chapter completeness

   ## Quality Findings
   - Placeholder / TODO count and locations
   - Documentation gaps

   ## Recommendations
   - **High severity** — Immediate fixes required
   - **Medium severity** — Short-term improvements
   - **Low severity** — Long-term enhancements

IMPORTANT: Produce the full Markdown report as your final answer.
The report will be saved to: {output_path}
""",
        expected_output=(
            "A complete Markdown architecture quality report covering "
            "executive summary, consistency analysis, quality findings, "
            "and prioritised recommendations."
        ),
        agent=agent,
    )
