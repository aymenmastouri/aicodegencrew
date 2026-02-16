"""
Microsoft Playwright MCP Integration for Phase 4 Planning.

Uses official @playwright/mcp server to fetch Angular upgrade guides.
Auto-starts MCP server when Phase 4 needs to fetch web content.
"""

from crewai import Agent, Task, Crew
from crewai.process import Process

from ...shared.mcp import get_phase4_mcps


def create_web_fetch_agent() -> Agent:
    """
    Create a CrewAI agent with multiple MCPs for web fetching and reasoning.

    The agent has access to:
    - Playwright: Web navigation and content extraction
    - Sequential Thinking: Complex reasoning
    - Memory: Learning from previous fetches
    - Brave Search: Searching for additional context

    Returns:
        Agent configured with Phase 4 MCP tools
    """
    # Get all Phase 4 MCPs (Playwright, Sequential Thinking, Memory, Brave Search)
    mcps = get_phase4_mcps()

    agent = Agent(
        role="Web Content Researcher & Analyzer",
        goal=(
            "Fetch Angular upgrade guides from official sources, analyze migration patterns, "
            "and extract structured migration rules. Learn from previous fetches and use "
            "web search to find additional context when needed."
        ),
        backstory=(
            "You are an expert web research analyst specializing in technical documentation. "
            "You use Playwright to navigate modern SPAs, Sequential Thinking to analyze complex "
            "migration patterns, Memory to remember user preferences and past findings, and "
            "Brave Search to find additional context. You always verify information from "
            "official sources and provide structured, accurate results."
        ),
        mcps=mcps,
        verbose=True,
        allow_delegation=False,
    )

    return agent


def fetch_angular_guide_with_playwright(from_version: str, to_version: str) -> dict:
    """
    Fetch Angular upgrade guide using CrewAI agent with Playwright MCP.

    Args:
        from_version: Starting Angular version (e.g., "18")
        to_version: Target Angular version (e.g., "19")

    Returns:
        Dictionary with migration rules and steps

    Example:
        >>> guide = fetch_angular_guide_with_playwright("18", "19")
        >>> print(guide["migration_rules"])
    """
    agent = create_web_fetch_agent()

    url = f"https://angular.dev/update-guide?v={from_version}.0-{to_version}.0&l=3"

    task = Task(
        description=f"""
Fetch the Angular upgrade guide from {url} and extract migration information.

WORKFLOW:
1. Use playwright_navigate to go to {url}
2. Use playwright_snapshot to get the page content after it loads
3. Extract all migration steps, rules, and code examples
4. Identify breaking changes vs recommended changes
5. Return a structured summary

REQUIRED OUTPUT FORMAT (JSON):
{{
  "framework": "Angular",
  "from_version": "{from_version}",
  "to_version": "{to_version}",
  "source_url": "{url}",
  "migration_rules": [
    {{
      "title": "Rule title",
      "description": "What needs to change",
      "migration_steps": ["Step 1", "Step 2", ...],
      "severity": "breaking|recommended|info",
      "code_examples": ["example code if available"]
    }}
  ]
}}

CRITICAL:
- Extract ALL migration rules from the page
- Identify severity based on keywords: "breaking", "deprecated", "recommended"
- Include specific migration steps, not just descriptions
- Capture code examples where provided
""",
        expected_output="JSON object with Angular migration rules",
        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()

    # Parse result
    import json
    try:
        if isinstance(result, str):
            return json.loads(result)
        elif hasattr(result, 'raw'):
            return json.loads(result.raw)
        else:
            return {"error": "Unexpected result format", "raw_result": str(result)}
    except json.JSONDecodeError:
        return {"error": "Failed to parse JSON", "raw_result": str(result)}


if __name__ == "__main__":
    # Test fetching
    import sys
    from_v = sys.argv[1] if len(sys.argv) > 1 else "18"
    to_v = sys.argv[2] if len(sys.argv) > 2 else "19"

    print(f"Fetching Angular {from_v} -> {to_v} upgrade guide...")
    guide = fetch_angular_guide_with_playwright(from_v, to_v)

    import json
    print(json.dumps(guide, indent=2))
