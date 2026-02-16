"""
Microsoft Playwright MCP Integration for Phase 4 Planning.

Uses official @playwright/mcp server to fetch Angular upgrade guides.
Auto-starts MCP server when Phase 4 needs to fetch web content.
"""

from crewai import Agent, Task, Crew
from crewai.mcp import MCPServerStdio
from crewai.process import Process


def create_web_fetch_agent() -> Agent:
    """
    Create a CrewAI agent with Playwright MCP for web fetching.

    The agent can fetch Angular upgrade guides and other web content
    using the official Microsoft Playwright MCP server.

    Returns:
        Agent configured with Playwright MCP tools
    """
    # Configure Playwright MCP server
    playwright_mcp = MCPServerStdio(
        command="npx",
        args=[
            "@playwright/mcp@latest",
            "--headless",  # Run in headless mode
            "--timeout-action", "30000",  # 30s timeout for actions
            "--isolated",  # Don't persist profile
        ],
        cache_tools_list=True,
    )

    agent = Agent(
        role="Web Content Researcher",
        goal="Fetch and extract structured information from web pages, especially Angular upgrade guides",
        backstory=(
            "You are a web research specialist who fetches official documentation "
            "from framework websites. You use Playwright to navigate pages, wait for "
            "content to load, and extract structured information accurately."
        ),
        mcps=[playwright_mcp],
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
