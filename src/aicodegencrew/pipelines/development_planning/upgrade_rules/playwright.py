"""
Playwright upgrade rules (declarative).

Generic rules for Playwright major version upgrades.
Scans for patterns in any Playwright project.
"""

from .base import (
    CodePattern,
    UpgradeCategory,
    UpgradeRule,
    UpgradeRuleSet,
    UpgradeSeverity,
)

# =============================================================================
# Playwright 1.x incremental upgrades
# =============================================================================

PLAYWRIGHT_GENERAL = UpgradeRuleSet(
    framework="Playwright",
    from_version="1",
    to_version="2",
    required_dependencies={
        "@playwright/test": "latest",
    },
    verification_commands=[
        "npx playwright test --list",
        "npx playwright install",
        "npx playwright test",
    ],
    rules=[
        UpgradeRule(
            id="pw-waitfor-deprecated",
            title="waitForNavigation -> waitForURL",
            description=(
                "page.waitForNavigation() is deprecated. Use page.waitForURL() or expect auto-waiting instead."
            ),
            severity=UpgradeSeverity.DEPRECATED,
            category=UpgradeCategory.API_CHANGE,
            from_version="1",
            to_version="2",
            detection_patterns=[
                CodePattern(
                    name="waitfor_navigation",
                    file_glob="*.ts",
                    regex=r"waitForNavigation\s*\(",
                    description="waitForNavigation() usage",
                ),
                CodePattern(
                    name="waitfor_navigation_js",
                    file_glob="*.js",
                    regex=r"waitForNavigation\s*\(",
                    description="waitForNavigation() usage (JS)",
                ),
            ],
            migration_steps=[
                "1. Replace page.waitForNavigation() with page.waitForURL(pattern)",
                "2. Alternatively, rely on Playwright auto-waiting (no explicit wait needed)",
                "3. For click + navigation: use await page.click() directly (auto-waits)",
            ],
            affected_stereotypes=[],
            effort_per_occurrence=5,
        ),
        UpgradeRule(
            id="pw-waitfor-selector",
            title="waitForSelector -> locator.waitFor",
            description="page.waitForSelector() is deprecated. Use locator.waitFor().",
            severity=UpgradeSeverity.DEPRECATED,
            category=UpgradeCategory.API_CHANGE,
            from_version="1",
            to_version="2",
            detection_patterns=[
                CodePattern(
                    name="waitfor_selector",
                    file_glob="*.ts",
                    regex=r"waitForSelector\s*\(",
                    description="waitForSelector() usage",
                ),
                CodePattern(
                    name="waitfor_selector_js",
                    file_glob="*.js",
                    regex=r"waitForSelector\s*\(",
                    description="waitForSelector() usage (JS)",
                ),
            ],
            migration_steps=[
                "1. Replace page.waitForSelector(sel) with page.locator(sel).waitFor()",
                "2. Use expect(locator).toBeVisible() for assertion-based waits",
            ],
            affected_stereotypes=[],
            effort_per_occurrence=3,
        ),
        UpgradeRule(
            id="pw-dollar-selector",
            title="page.$() -> page.locator()",
            description="page.$() and page.$$() are discouraged. Use locator API.",
            severity=UpgradeSeverity.RECOMMENDED,
            category=UpgradeCategory.API_CHANGE,
            from_version="1",
            to_version="2",
            detection_patterns=[
                CodePattern(
                    name="dollar_selector",
                    file_glob="*.ts",
                    regex=r"page\.\$\s*\(|page\.\$\$\s*\(",
                    description="page.$() or page.$$() usage",
                ),
                CodePattern(
                    name="dollar_selector_js",
                    file_glob="*.js",
                    regex=r"page\.\$\s*\(|page\.\$\$\s*\(",
                    description="page.$() or page.$$() usage (JS)",
                ),
            ],
            migration_steps=[
                "1. Replace page.$('selector') with page.locator('selector')",
                "2. Replace page.$$('selector') with page.locator('selector').all()",
                "3. Locator API has better auto-waiting and retry logic",
            ],
            affected_stereotypes=[],
            effort_per_occurrence=3,
        ),
        UpgradeRule(
            id="pw-elementhandle-deprecated",
            title="ElementHandle -> Locator API",
            description="ElementHandle methods are deprecated. Use Locator-based API.",
            severity=UpgradeSeverity.DEPRECATED,
            category=UpgradeCategory.API_CHANGE,
            from_version="1",
            to_version="2",
            detection_patterns=[
                CodePattern(
                    name="elementhandle_type",
                    file_glob="*.ts",
                    regex=r"ElementHandle|\.asElement\(\)|\.boundingBox\(\)",
                    description="ElementHandle usage",
                ),
            ],
            migration_steps=[
                "1. Replace ElementHandle operations with Locator methods",
                "2. locator.click() instead of elementHandle.click()",
                "3. locator.boundingBox() instead of elementHandle.boundingBox()",
            ],
            affected_stereotypes=[],
            effort_per_occurrence=5,
        ),
        UpgradeRule(
            id="pw-config-migration",
            title="Playwright config format changes",
            description="Playwright config API evolves. Check for deprecated config options.",
            severity=UpgradeSeverity.RECOMMENDED,
            category=UpgradeCategory.BUILD_CONFIG,
            from_version="1",
            to_version="2",
            detection_patterns=[
                CodePattern(
                    name="pw_config_ts",
                    file_glob="playwright.config.ts",
                    regex=r"defineConfig|PlaywrightTestConfig",
                    description="Playwright config file",
                ),
                CodePattern(
                    name="pw_config_js",
                    file_glob="playwright.config.js",
                    regex=r"defineConfig|PlaywrightTestConfig",
                    description="Playwright config file (JS)",
                ),
            ],
            migration_steps=[
                "1. Use defineConfig() wrapper (recommended since PW 1.30)",
                "2. Review webServer config (changed in recent versions)",
                "3. Check reporter config format for breaking changes",
            ],
            affected_stereotypes=[],
            effort_per_occurrence=15,
        ),
        UpgradeRule(
            id="pw-cucumber-compat",
            title="Playwright-BDD / Cucumber compatibility",
            description="Playwright-BDD and Cucumber versions must match Playwright version.",
            severity=UpgradeSeverity.DEPRECATED,
            category=UpgradeCategory.DEPENDENCY,
            from_version="1",
            to_version="2",
            detection_patterns=[
                CodePattern(
                    name="playwright_bdd_dep",
                    file_glob="package.json",
                    regex=r'"playwright-bdd"\s*:|"@cucumber/cucumber"\s*:',
                    description="Playwright-BDD or Cucumber dependency",
                ),
            ],
            migration_steps=[
                "1. Check playwright-bdd compatibility matrix for target Playwright version",
                "2. Update @cucumber/cucumber to compatible version",
                "3. Review step definitions for API changes",
            ],
            affected_stereotypes=[],
            effort_per_occurrence=30,
        ),
    ],
)


# =============================================================================
# Combined export
# =============================================================================

PLAYWRIGHT_UPGRADE_RULES: list = [
    PLAYWRIGHT_GENERAL,
]
