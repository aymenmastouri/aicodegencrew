"""
Web Content Fetching via MCP for Phase 4 Planning.

Generic utility for fetching upgrade guides and documentation
for ANY framework. Uses Playwright MCP when available.

NOT Angular-specific - works with any framework/technology.
"""

from crewai import Agent, Crew, Task
from crewai.process import Process

from ...shared.mcp import get_phase4_mcps
from ...shared.utils.crew_callbacks import step_callback, task_callback
from ...shared.utils.embedder_config import get_crew_embedder
from ...shared.utils.llm_factory import create_llm


def create_web_fetch_agent() -> Agent:
    """Create a generic web fetch agent with Phase 4 MCPs.

    The agent discovers available tools automatically from MCPs.
    No hardcoded tool names - CrewAI handles tool discovery.
    """
    mcps = get_phase4_mcps()
    llm = create_llm()

    return Agent(
        role="Technical Documentation Researcher",
        goal="Fetch and analyze technical documentation from official sources.",
        backstory=(
            "You are an expert at finding and extracting structured information "
            "from official documentation sites. You work with any technology stack "
            "and always return structured, accurate results."
        ),
        llm=llm,
        mcps=mcps,
        allow_delegation=False,
        verbose=True,
        max_iter=10,
        respect_context_window=True,
        inject_date=True,
    )


def fetch_upgrade_guide(framework: str, from_version: str, to_version: str) -> dict:
    """Fetch upgrade guide for ANY framework.

    The agent uses its available tools to find and extract migration info.
    No hardcoded URLs or tool names.

    Args:
        framework: Framework name (e.g., "Angular", "Spring Boot", "React")
        from_version: Starting version (e.g., "18")
        to_version: Target version (e.g., "19")

    Returns:
        Dictionary with migration rules and steps
    """
    agent = create_web_fetch_agent()

    task = Task(
        name=f"Fetch {framework} {from_version}->{to_version} guide",
        description=(
            f"Find the official upgrade/migration guide for {framework} "
            f"from version {from_version} to version {to_version}.\n\n"
            f"Search for the official documentation, navigate to it if needed, "
            f"and extract all migration steps, breaking changes, and code examples.\n\n"
            f"Return a JSON object with:\n"
            f'{{"framework": "{framework}", "from_version": "{from_version}", '
            f'"to_version": "{to_version}", "migration_rules": [...]}}'
        ),
        expected_output=f"JSON object with {framework} migration rules",
        agent=agent,
    )

    from pathlib import Path as _Path

    log_dir = _Path("knowledge/plan/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
        step_callback=step_callback,
        task_callback=task_callback,
        output_log_file=str(log_dir / "web_fetch.json"),
        embedder=get_crew_embedder(),
    )

    result = crew.kickoff()

    import json

    try:
        if isinstance(result, str):
            return json.loads(result)
        elif hasattr(result, "raw"):
            return json.loads(result.raw)
        else:
            return {"error": "Unexpected result format", "raw_result": str(result)}
    except json.JSONDecodeError:
        return {"error": "Failed to parse JSON", "raw_result": str(result)}
