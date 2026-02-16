"""
Angular Update Guide Fetcher using Playwright.

Fetches official Angular upgrade guides from angular.dev at runtime.
No hardcoded rules - always uses the latest official documentation.
"""

import json
import logging
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


def fetch_angular_guide(from_version: str, to_version: str, cache_dir: Path | None = None) -> dict[str, Any]:
    """
    Fetch Angular official update guide using Playwright.

    Args:
        from_version: Starting version (e.g., "18")
        to_version: Target version (e.g., "19")
        cache_dir: Optional directory to cache fetched guides

    Returns:
        Dictionary with migration rules and steps

    Example:
        >>> guide = fetch_angular_guide("18", "19")
        >>> print(guide["migration_rules"])
    """
    # Check cache first
    if cache_dir:
        cache_file = cache_dir / f"angular_{from_version}_to_{to_version}.json"
        if cache_file.exists():
            logger.info(f"Using cached Angular guide: {cache_file}")
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Cache read failed: {e}, fetching fresh")

    # Fetch from angular.dev
    url = f"https://angular.dev/update-guide?v={from_version}.0-{to_version}.0&l=3"

    try:
        logger.info(f"Fetching Angular guide from {url}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Navigate and wait for content
            page.goto(url, wait_until="networkidle", timeout=30000)

            # Wait for main content to load
            page.wait_for_selector("main", timeout=10000)

            # Extract title
            title = page.title()

            # Extract all step sections
            steps = page.query_selector_all("section, article, .step, .update-step")

            migration_rules = []

            for step in steps[:20]:  # Limit to first 20 sections
                # Extract heading
                heading_elem = step.query_selector("h1, h2, h3, h4, h5")
                if not heading_elem:
                    continue

                heading_text = heading_elem.inner_text()

                # Skip navigation/footer sections
                if any(skip in heading_text.lower() for skip in ["navigation", "footer", "menu", "search"]):
                    continue

                # Extract description paragraphs
                paragraphs = step.query_selector_all("p")
                description = " ".join(p.inner_text() for p in paragraphs[:3])

                # Extract migration steps (list items)
                list_items = step.query_selector_all("li")
                steps_list = [li.inner_text() for li in list_items[:15]]  # Limit to 15 steps

                # Extract code blocks
                code_blocks = step.query_selector_all("code, pre")
                code_snippets = [code.inner_text() for code in code_blocks[:5]]

                if steps_list or description or code_snippets:
                    migration_rules.append({
                        "title": heading_text,
                        "description": description[:1000],  # Limit description length
                        "migration_steps": steps_list,
                        "code_examples": code_snippets,
                        "severity": _infer_severity(heading_text, description),
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
            }

            # Cache the result
            if cache_dir:
                cache_dir.mkdir(parents=True, exist_ok=True)
                cache_file = cache_dir / f"angular_{from_version}_to_{to_version}.json"
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                logger.info(f"Cached Angular guide: {cache_file}")

            return result

    except PlaywrightTimeout:
        logger.error(f"Timeout fetching Angular guide from {url}")
        return _fallback_guide(from_version, to_version, "timeout")
    except Exception as e:
        logger.error(f"Error fetching Angular guide: {e}")
        return _fallback_guide(from_version, to_version, str(e))


def _infer_severity(title: str, description: str) -> str:
    """Infer severity from title and description keywords."""
    text = (title + " " + description).lower()

    if any(word in text for word in ["breaking", "required", "must", "critical"]):
        return "breaking"
    elif any(word in text for word in ["deprecated", "should", "recommended"]):
        return "recommended"
    else:
        return "info"


def _fallback_guide(from_version: str, to_version: str, error_reason: str) -> dict[str, Any]:
    """Return minimal fallback guide when fetching fails."""
    logger.warning(f"Using fallback guide for Angular {from_version}->{to_version} (reason: {error_reason})")

    return {
        "framework": "Angular",
        "from_version": from_version,
        "to_version": to_version,
        "source_url": "fallback",
        "error": error_reason,
        "migration_rules": [
            {
                "title": f"Angular {from_version} to {to_version} Upgrade",
                "description": f"Upgrade failed to fetch from angular.dev. Use ng update and check official docs.",
                "migration_steps": [
                    "CRITICAL: Fetch failed - refer to https://angular.dev/update-guide manually",
                    f"Run: ng update @angular/core@{to_version} @angular/cli@{to_version}",
                    "Follow prompts and fix errors",
                    "Run: ng build --configuration production",
                    "Run: ng test",
                ],
                "code_examples": [],
                "severity": "breaking",
            }
        ],
        "total_rules": 1,
    }


if __name__ == "__main__":
    # Test fetching
    import sys
    from_v = sys.argv[1] if len(sys.argv) > 1 else "18"
    to_v = sys.argv[2] if len(sys.argv) > 2 else "19"

    guide = fetch_angular_guide(from_v, to_v, cache_dir=Path("knowledge/upgrade_guides"))
    print(json.dumps(guide, indent=2))
