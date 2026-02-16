#!/usr/bin/env python3
"""
Web Fetch MCP Server with Playwright - for CrewAI integration.

Provides web fetching tools (including Angular upgrade guides) via MCP protocol.
Auto-started by Phase 4 when needed.

Usage:
    python web_fetch_mcp.py
"""

import json
import logging
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Configure logging to stderr ONLY (MCP requirement)
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)

logger = logging.getLogger(__name__)

# Import FastMCP
from mcp.server.fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("web-fetch-playwright")


@mcp.tool()
def fetch_angular_guide(from_version: str, to_version: str) -> str:
    """
    Fetch Angular official update guide using Playwright.

    Args:
        from_version: Starting Angular version (e.g., "18")
        to_version: Target Angular version (e.g., "19")

    Returns:
        JSON string with migration rules, steps, and code examples
    """
    url = f"https://angular.dev/update-guide?v={from_version}.0-{to_version}.0&l=3"

    try:
        logger.info(f"Fetching Angular guide: {from_version} -> {to_version}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Navigate and wait for content
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_selector("main", timeout=10000)

            # Extract page title
            title = page.title()

            # Extract all step sections
            steps = page.query_selector_all("section, article, .step, .update-step, [class*='step']")

            migration_rules = []

            for step in steps[:20]:  # Limit to 20 sections
                # Extract heading
                heading_elem = step.query_selector("h1, h2, h3, h4, h5, h6")
                if not heading_elem:
                    continue

                heading_text = heading_elem.inner_text()

                # Skip navigation/footer
                if any(skip in heading_text.lower() for skip in ["navigation", "footer", "menu", "search", "cookie"]):
                    continue

                # Extract description
                paragraphs = step.query_selector_all("p")
                description = " ".join(p.inner_text() for p in paragraphs[:3])

                # Extract migration steps (list items)
                list_items = step.query_selector_all("li")
                steps_list = [li.inner_text() for li in list_items[:15]]

                # Extract code blocks
                code_blocks = step.query_selector_all("code, pre")
                code_snippets = [code.inner_text() for code in code_blocks[:5]]

                if steps_list or description or code_snippets:
                    # Infer severity
                    text = (heading_text + " " + description).lower()
                    if any(word in text for word in ["breaking", "required", "must", "critical"]):
                        severity = "breaking"
                    elif any(word in text for word in ["deprecated", "should", "recommended"]):
                        severity = "recommended"
                    else:
                        severity = "info"

                    migration_rules.append({
                        "title": heading_text,
                        "description": description[:1000],
                        "migration_steps": steps_list,
                        "code_examples": code_snippets,
                        "severity": severity,
                    })

            browser.close()

            result = {
                "framework": "Angular",
                "from_version": from_version,
                "to_version": to_version,
                "source_url": url,
                "page_title": title,
                "migration_rules": migration_rules,
                "total_rules": len(migration_rules),
                "status": "success",
            }

            return json.dumps(result, indent=2)

    except PlaywrightTimeout:
        error = {
            "error": "Timeout fetching Angular guide (30s)",
            "from_version": from_version,
            "to_version": to_version,
            "status": "timeout",
        }
        return json.dumps(error)
    except Exception as e:
        error = {
            "error": str(e),
            "from_version": from_version,
            "to_version": to_version,
            "status": "error",
        }
        return json.dumps(error)


@mcp.tool()
def fetch_webpage(url: str, wait_for_selector: str = "body", timeout_ms: int = 30000) -> str:
    """
    Fetch any webpage using Playwright (with JavaScript rendering).

    Args:
        url: The URL to fetch
        wait_for_selector: CSS selector to wait for (default: "body")
        timeout_ms: Timeout in milliseconds (default: 30000)

    Returns:
        JSON string with page title and text content
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_selector(wait_for_selector, timeout=timeout_ms)

            title = page.title()
            content = page.content()

            # Extract text
            text = page.inner_text("body")

            browser.close()

            result = {
                "url": url,
                "title": title,
                "text": text[:50000],  # Limit to 50K chars
                "html_length": len(content),
                "text_length": len(text),
                "status": "success",
            }

            return json.dumps(result, indent=2)

    except Exception as e:
        error = {"error": str(e), "url": url, "status": "error"}
        return json.dumps(error)


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
