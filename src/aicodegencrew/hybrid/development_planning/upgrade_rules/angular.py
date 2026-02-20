"""
Angular upgrade rules (dynamic from official source).

IMPORTANT: Rules are fetched dynamically from https://angular.dev/update-guide
using Microsoft Playwright MCP. No hardcoded rules.

This ensures upgrade guidance is always current with official Angular documentation.
"""

from .base import (
    CodePattern,
    UpgradeCategory,
    UpgradeRule,
    UpgradeRuleSet,
    UpgradeSeverity,
)

# Flag to control whether to fetch dynamically or use fallback.
# Dynamic fetch requires Playwright MCP + working LLM auth.
# When disabled, uses comprehensive static rules with regex detection patterns.
USE_DYNAMIC_FETCH = False

# =============================================================================
# Angular 18 -> 19
# =============================================================================

ANGULAR_18_TO_19 = UpgradeRuleSet(
    framework="Angular",
    from_version="18",
    to_version="19",
    required_dependencies={
        "typescript": ">=5.6",
        "@angular/core": "^19.0.0",
        "zone.js": ">=0.15.0",
    },
    verification_commands=["ng build", "ng test"],
    rules=[
        UpgradeRule(
            id="ng19-standalone-default",
            title="Standalone components are now default",
            description=(
                "Angular 19 treats components as standalone by default. "
                "Components in NgModule declarations need explicit standalone:false "
                "or should be migrated to standalone."
            ),
            severity=UpgradeSeverity.BREAKING,
            category=UpgradeCategory.MIGRATION,
            from_version="18",
            to_version="19",
            detection_patterns=[
                CodePattern(
                    name="ngmodule_declarations",
                    file_glob="*.module.ts",
                    regex=r"declarations\s*:\s*\[",
                    description="NgModule with declarations array",
                ),
                CodePattern(
                    name="component_without_standalone",
                    file_glob="*.component.ts",
                    regex=r"@Component\s*\(\s*\{",
                    description="Component decorator (needs standalone check)",
                ),
            ],
            migration_steps=[
                "1. Run: ng generate @angular/core:standalone-migration",
                "2. Review generated changes per module",
                "3. Remove empty NgModules after migration",
                "4. Update test imports to use component directly",
            ],
            schematic="ng generate @angular/core:standalone-migration",
            affected_stereotypes=["component", "directive", "pipe", "module"],
            effort_per_occurrence=10,
        ),
        UpgradeRule(
            id="ng19-builder-migration",
            title="Browser builder -> Application builder",
            description=(
                "@angular-devkit/build-angular:browser is replaced by @angular/build:application (esbuild-based)."
            ),
            severity=UpgradeSeverity.BREAKING,
            category=UpgradeCategory.BUILD_CONFIG,
            from_version="18",
            to_version="19",
            detection_patterns=[
                CodePattern(
                    name="browser_builder",
                    file_glob="angular.json",
                    regex=r"@angular-devkit/build-angular:browser",
                    description="Legacy browser builder",
                ),
            ],
            migration_steps=[
                "1. Run: ng update @angular/cli",
                "2. Accept builder migration prompt",
                "3. Remove buildOptimizer and vendorChunk (not needed with esbuild)",
                "4. Update output path configuration",
            ],
            affected_stereotypes=[],
            effort_per_occurrence=30,
        ),
        # NOTE: ng19-app-initializer rule REMOVED - provideAppInitializer() does NOT exist in Angular 19
        # APP_INITIALIZER with provider pattern is still valid in Angular 19
        # Migration handled by ng-httpclient-module rule which includes APP_INITIALIZER guidance
        UpgradeRule(
            id="ng19-http-client-migration",
            title="HttpClientModule -> provideHttpClient",
            description=(
                "Angular 19 deprecates HttpClientModule. Migrate to functional provideHttpClient(). "
                "IMPORTANT: APP_INITIALIZER still uses provider pattern - do NOT use provideAppInitializer (doesn't exist)."
            ),
            severity=UpgradeSeverity.BREAKING,
            category=UpgradeCategory.API_CHANGE,
            from_version="18",
            to_version="19",
            detection_patterns=[
                CodePattern(
                    name="httpclient_module_import",
                    file_glob="*.module.ts",
                    regex=r"HttpClientModule",
                    description="HttpClientModule in imports",
                ),
                CodePattern(
                    name="app_initializer_provider",
                    file_glob="*.module.ts",
                    regex=r"provide:\s*APP_INITIALIZER",
                    description="APP_INITIALIZER provider (still valid, DO NOT change)",
                ),
            ],
            migration_steps=[
                "SEARCH FIRST: Use rag_query(query='provideHttpClient Angular', limit=10) to find migration patterns in codebase",
                "SEARCH: Use rag_query(query='APP_INITIALIZER provide useFactory multi', limit=5) to find existing initializer patterns",
                "In NgModule imports array, REMOVE HttpClientModule",
                "In NgModule providers array, ADD provideHttpClient(withInterceptorsFromDi())",
                "Import: import { provideHttpClient, withInterceptorsFromDi } from '@angular/common/http'",
                "CRITICAL: APP_INITIALIZER uses provider pattern { provide: APP_INITIALIZER, useFactory: ..., multi: true, deps: [...] }",
                "DO NOT use provideAppInitializer() - it does NOT exist in Angular 19",
            ],
            affected_stereotypes=["module"],
            effort_per_occurrence=15,
        ),
        UpgradeRule(
            id="ng19-sass-compiler",
            title="node-sass -> Dart Sass (sass)",
            description=(
                "Angular 19 application builder only supports Dart Sass (sass package). "
                "node-sass is deprecated and incompatible. SCSS files using node-sass "
                "specific syntax (e.g. / for division) must migrate to math.div()."
            ),
            severity=UpgradeSeverity.BREAKING,
            category=UpgradeCategory.BUILD_CONFIG,
            from_version="18",
            to_version="19",
            detection_patterns=[
                CodePattern(
                    name="node_sass_dependency",
                    file_glob="package.json",
                    regex=r'"node-sass"\s*:',
                    description="node-sass in dependencies",
                ),
                CodePattern(
                    name="sass_division_slash",
                    file_glob="*.scss",
                    regex=r"(?<!\/)(\$[\w-]+)\s*\/\s*\d+",
                    description="Sass / division (deprecated, use math.div())",
                ),
                CodePattern(
                    name="sass_deep_deprecated",
                    file_glob="*.scss",
                    regex=r"\/deep\/|::ng-deep",
                    description="::ng-deep or /deep/ (deprecated in Angular)",
                ),
            ],
            migration_steps=[
                "1. Replace node-sass with sass: npm uninstall node-sass && npm install -D sass",
                "2. Add @use 'sass:math' in SCSS files using division",
                "3. Replace $var / 2 with math.div($var, 2)",
                "4. Review ::ng-deep usage (deprecated, plan removal)",
                "5. Test: ng build --watch to verify all SCSS compiles",
            ],
            affected_stereotypes=["component"],
            effort_per_occurrence=5,
        ),
        UpgradeRule(
            id="ng19-typescript-56",
            title="TypeScript 5.4 -> 5.6",
            description="Angular 19 requires TypeScript 5.6+.",
            severity=UpgradeSeverity.BREAKING,
            category=UpgradeCategory.DEPENDENCY,
            from_version="18",
            to_version="19",
            detection_patterns=[
                CodePattern(
                    name="typescript_version",
                    file_glob="package.json",
                    regex=r'"typescript"\s*:\s*"[~^]?5\.[0-5]',
                    description="TypeScript below 5.6",
                ),
            ],
            migration_steps=[
                "1. Run: npm install typescript@~5.6.0",
                "2. Fix any new strict type errors from TS 5.5/5.6",
            ],
            affected_stereotypes=[],
            effort_per_occurrence=60,
        ),
        UpgradeRule(
            id="ng19-zonejs-015",
            title="Zone.js 0.14 -> 0.15",
            description="Angular 19 requires Zone.js 0.15+.",
            severity=UpgradeSeverity.BREAKING,
            category=UpgradeCategory.DEPENDENCY,
            from_version="18",
            to_version="19",
            detection_patterns=[
                CodePattern(
                    name="zonejs_version",
                    file_glob="package.json",
                    regex=r'"zone\.js"\s*:\s*"[~^]?0\.1[0-4]',
                    description="Zone.js below 0.15",
                ),
            ],
            migration_steps=[
                "1. Run: npm install zone.js@~0.15.0",
            ],
            affected_stereotypes=[],
            effort_per_occurrence=10,
        ),
    ],
)


# =============================================================================
# Angular 19 -> 20
# =============================================================================

ANGULAR_19_TO_20 = UpgradeRuleSet(
    framework="Angular",
    from_version="19",
    to_version="20",
    required_dependencies={
        "typescript": ">=5.8",
        "@angular/core": "^20.0.0",
    },
    verification_commands=["ng build", "ng test"],
    rules=[
        UpgradeRule(
            id="ng20-control-flow",
            title="ngIf/ngFor/ngSwitch -> @if/@for/@switch control flow",
            description=(
                "Structural directives *ngIf, *ngFor, *ngSwitch are deprecated. "
                "Migrate to built-in @if/@for/@switch template syntax."
            ),
            severity=UpgradeSeverity.DEPRECATED,
            category=UpgradeCategory.SYNTAX,
            from_version="19",
            to_version="20",
            detection_patterns=[
                CodePattern(
                    name="ngif_usage",
                    file_glob="*.html",
                    regex=r"\*ngIf\s*=",
                    description="*ngIf directive in template",
                ),
                CodePattern(
                    name="ngfor_usage",
                    file_glob="*.html",
                    regex=r"\*ngFor\s*=",
                    description="*ngFor directive in template",
                ),
                CodePattern(
                    name="ngswitch_usage",
                    file_glob="*.html",
                    regex=r"\[ngSwitch\]",
                    description="[ngSwitch] directive in template",
                ),
            ],
            migration_steps=[
                "1. Run: ng generate @angular/core:control-flow-migration",
                "2. Review @if blocks (handle else/else-if manually)",
                "3. Review @for blocks (track expression is required)",
                "4. Review @switch blocks",
                "5. Remove CommonModule imports where only used for ngIf/ngFor",
            ],
            schematic="ng generate @angular/core:control-flow-migration",
            affected_stereotypes=["component"],
            effort_per_occurrence=3,
        ),
        UpgradeRule(
            id="ng20-karma-deprecated",
            title="Karma test runner -> Vitest/Web Test Runner",
            description="Karma is deprecated in Angular 20. Migrate to Vitest or Web Test Runner.",
            severity=UpgradeSeverity.DEPRECATED,
            category=UpgradeCategory.TEST_RUNNER,
            from_version="19",
            to_version="20",
            detection_patterns=[
                CodePattern(
                    name="karma_config",
                    file_glob="karma.conf.js",
                    regex=r"module\.exports",
                    description="Karma configuration file",
                ),
                CodePattern(
                    name="karma_dependency",
                    file_glob="package.json",
                    regex=r'"karma"\s*:',
                    description="Karma in dependencies",
                ),
            ],
            migration_steps=[
                "1. Install Vitest: npm install -D vitest @analogjs/vite-plugin-angular",
                "2. Create vitest.config.ts with Angular plugin",
                "3. Migrate TestBed imports (mostly compatible)",
                "4. Remove karma.conf.js and karma dependencies",
                "5. Update angular.json test architect",
            ],
            affected_stereotypes=[],
            effort_per_occurrence=120,
        ),
        UpgradeRule(
            id="ng20-inject-flags-removed",
            title="InjectFlags API removed",
            description="InjectFlags enum removed. Use inject() options object instead.",
            severity=UpgradeSeverity.BREAKING,
            category=UpgradeCategory.API_CHANGE,
            from_version="19",
            to_version="20",
            detection_patterns=[
                CodePattern(
                    name="inject_flags",
                    file_glob="*.ts",
                    regex=r"InjectFlags",
                    description="InjectFlags enum usage",
                ),
            ],
            migration_steps=[
                "1. Replace InjectFlags.Optional with { optional: true }",
                "2. Replace InjectFlags.Self with { self: true }",
                "3. Replace InjectFlags.SkipSelf with { skipSelf: true }",
            ],
            affected_stereotypes=["service", "component"],
            effort_per_occurrence=5,
        ),
        UpgradeRule(
            id="ng20-hammerjs-deprecated",
            title="HammerJS support deprecated",
            description="HammerJS gesture support deprecated. Use native pointer events.",
            severity=UpgradeSeverity.DEPRECATED,
            category=UpgradeCategory.DEPENDENCY,
            from_version="19",
            to_version="20",
            detection_patterns=[
                CodePattern(
                    name="hammerjs_import",
                    file_glob="*.ts",
                    regex=r"import.*hammerjs|HammerModule",
                    description="HammerJS import or HammerModule",
                ),
            ],
            migration_steps=[
                "1. Replace HammerJS gestures with pointer events",
                "2. Remove HammerModule from imports",
                "3. Remove hammerjs from package.json",
            ],
            affected_stereotypes=["component", "module"],
            effort_per_occurrence=30,
        ),
    ],
)


# =============================================================================
# Cross-version Signal Migration (recommended, not version-gated)
# =============================================================================

ANGULAR_SIGNAL_MIGRATION = UpgradeRuleSet(
    framework="Angular",
    from_version="18",
    to_version="20",
    verification_commands=["ng build", "ng test"],
    rules=[
        UpgradeRule(
            id="ng-signal-inputs",
            title="@Input() -> input() signal",
            description="Migrate decorator-based inputs to signal-based inputs.",
            severity=UpgradeSeverity.RECOMMENDED,
            category=UpgradeCategory.MIGRATION,
            from_version="18",
            to_version="20",
            detection_patterns=[
                CodePattern(
                    name="decorator_input",
                    file_glob="*.component.ts",
                    regex=r"@Input\s*\(",
                    description="@Input() decorator",
                ),
            ],
            migration_steps=[
                "1. Run: ng generate @angular/core:signal-input-migration",
                "2. Review required vs optional inputs",
                "3. Update template access: myInput -> myInput()",
            ],
            schematic="ng generate @angular/core:signal-input-migration",
            affected_stereotypes=["component", "directive"],
            effort_per_occurrence=5,
        ),
        UpgradeRule(
            id="ng-signal-outputs",
            title="@Output() -> output() signal",
            description="Migrate EventEmitter outputs to signal-based outputs.",
            severity=UpgradeSeverity.RECOMMENDED,
            category=UpgradeCategory.MIGRATION,
            from_version="18",
            to_version="20",
            detection_patterns=[
                CodePattern(
                    name="decorator_output",
                    file_glob="*.component.ts",
                    regex=r"@Output\s*\(",
                    description="@Output() decorator",
                ),
            ],
            migration_steps=[
                "1. Run: ng generate @angular/core:output-migration",
                "2. Replace EventEmitter with OutputEmitterRef",
                "3. Update emit() calls",
            ],
            schematic="ng generate @angular/core:output-migration",
            affected_stereotypes=["component", "directive"],
            effort_per_occurrence=5,
        ),
        UpgradeRule(
            id="ng-signal-viewchild",
            title="@ViewChild -> viewChild() signal query",
            description="Migrate @ViewChild/@ViewChildren to signal-based queries.",
            severity=UpgradeSeverity.RECOMMENDED,
            category=UpgradeCategory.MIGRATION,
            from_version="18",
            to_version="20",
            detection_patterns=[
                CodePattern(
                    name="viewchild_decorator",
                    file_glob="*.component.ts",
                    regex=r"@ViewChild\s*\(",
                    description="@ViewChild() decorator",
                ),
                CodePattern(
                    name="viewchildren_decorator",
                    file_glob="*.component.ts",
                    regex=r"@ViewChildren\s*\(",
                    description="@ViewChildren() decorator",
                ),
            ],
            migration_steps=[
                "1. Run: ng generate @angular/core:signal-queries-migration",
                "2. Replace @ViewChild with viewChild()",
                "3. Replace @ViewChildren with viewChildren()",
                "4. Update access patterns to use signal calls",
            ],
            schematic="ng generate @angular/core:signal-queries-migration",
            affected_stereotypes=["component"],
            effort_per_occurrence=5,
        ),
        # NOTE: ng-httpclient-module rule moved to ANGULAR_18_TO_19 with BREAKING severity and RAG search instructions
    ],
)


# =============================================================================
# Third-party Dependency Compatibility
# =============================================================================

ANGULAR_THIRD_PARTY = UpgradeRuleSet(
    framework="Angular",
    from_version="18",
    to_version="20",
    rules=[
        UpgradeRule(
            id="ng-aggrid-compat",
            title="AG Grid compatibility check",
            description="AG Grid 31.x may need upgrade for Angular 19/20 compatibility.",
            severity=UpgradeSeverity.DEPRECATED,
            category=UpgradeCategory.DEPENDENCY,
            from_version="18",
            to_version="20",
            detection_patterns=[
                CodePattern(
                    name="aggrid_dependency",
                    file_glob="package.json",
                    regex=r'"ag-grid-angular"\s*:\s*"[~^]?31\.',
                    description="AG Grid 31.x",
                ),
            ],
            migration_steps=[
                "1. Check AG Grid compatibility matrix for target Angular version",
                "2. Upgrade to ag-grid-angular 32.x+ if needed",
                "3. Review AG Grid changelog for breaking changes",
            ],
            affected_stereotypes=["component"],
            effort_per_occurrence=60,
        ),
        UpgradeRule(
            id="ng-ngbootstrap-compat",
            title="ng-bootstrap compatibility check",
            description="ng-bootstrap 17.x needs upgrade for Angular 19/20.",
            severity=UpgradeSeverity.DEPRECATED,
            category=UpgradeCategory.DEPENDENCY,
            from_version="18",
            to_version="20",
            detection_patterns=[
                CodePattern(
                    name="ngbootstrap_dependency",
                    file_glob="package.json",
                    regex=r'"@ng-bootstrap/ng-bootstrap"\s*:\s*"[~^]?17\.',
                    description="ng-bootstrap 17.x",
                ),
            ],
            migration_steps=[
                "1. Upgrade to @ng-bootstrap/ng-bootstrap 18.x+",
                "2. Review component API changes in changelog",
            ],
            affected_stereotypes=["component"],
            effort_per_occurrence=45,
        ),
        UpgradeRule(
            id="ng-ngxtranslate-compat",
            title="ngx-translate compatibility check",
            description="ngx-translate 15.x may need upgrade for Angular 19/20.",
            severity=UpgradeSeverity.DEPRECATED,
            category=UpgradeCategory.DEPENDENCY,
            from_version="18",
            to_version="20",
            detection_patterns=[
                CodePattern(
                    name="ngxtranslate_dependency",
                    file_glob="package.json",
                    regex=r'"@ngx-translate/core"\s*:\s*"[~^]?15\.',
                    description="ngx-translate 15.x",
                ),
            ],
            migration_steps=[
                "1. Check ngx-translate Angular 19/20 compatibility",
                "2. Consider migration to @angular/localize if ngx-translate is unmaintained",
            ],
            affected_stereotypes=["module", "component"],
            effort_per_occurrence=30,
        ),
    ],
)


# =============================================================================
# Dynamic Rule Fetching (NEW - uses Playwright MCP)
# =============================================================================


def fetch_angular_rules_dynamic(from_version: str, to_version: str) -> UpgradeRuleSet:
    """
    Fetch Angular upgrade rules dynamically from angular.dev using Playwright MCP.

    This replaces hardcoded rules with live data from the official Angular update guide.

    Args:
        from_version: Starting version (e.g., "18")
        to_version: Target version (e.g., "19")

    Returns:
        UpgradeRuleSet with rules fetched from angular.dev
    """
    if not USE_DYNAMIC_FETCH:
        # Return comprehensive static rules with regex detection patterns
        return _get_static_ruleset(from_version, to_version)

    try:
        from ..playwright_mcp_integration import fetch_upgrade_guide

        # Fetch guide using MCP (framework-generic)
        guide = fetch_upgrade_guide("Angular", from_version, to_version)

        if "error" in guide:
            # Fallback on error
            return _get_fallback_ruleset(from_version, to_version, guide.get("error"))

        # Convert fetched guide to UpgradeRuleSet
        rules = []
        for rule_data in guide.get("migration_rules", []):
            severity_map = {
                "breaking": UpgradeSeverity.BREAKING,
                "recommended": UpgradeSeverity.RECOMMENDED,
                "info": UpgradeSeverity.DEPRECATED,
            }
            severity = severity_map.get(rule_data.get("severity", "info"), UpgradeSeverity.DEPRECATED)

            rule = UpgradeRule(
                id=f"ng{to_version}-{_slugify(rule_data.get('title', 'rule'))}",
                title=rule_data.get("title", "Migration rule"),
                description=rule_data.get("description", ""),
                severity=severity,
                category=UpgradeCategory.MIGRATION,
                from_version=from_version,
                to_version=to_version,
                detection_patterns=[],  # Playwright doesn't provide these
                migration_steps=rule_data.get("migration_steps", []),
                affected_stereotypes=[],
                effort_per_occurrence=15,
            )
            rules.append(rule)

        return UpgradeRuleSet(
            framework="Angular",
            from_version=from_version,
            to_version=to_version,
            required_dependencies={
                "@angular/core": f"^{to_version}.0.0",
            },
            verification_commands=["ng build", "ng test"],
            rules=rules,
        )

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Failed to fetch Angular rules dynamically: {e}")
        return _get_fallback_ruleset(from_version, to_version, str(e))


def _slugify(text: str) -> str:
    """Convert text to slug (lowercase, hyphenated)."""
    import re

    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50]


def _get_static_ruleset(from_version: str, to_version: str) -> UpgradeRuleSet:
    """Return the comprehensive static ruleset for a version pair."""
    key = f"{from_version}-{to_version}"
    static_map = {
        "18-19": ANGULAR_18_TO_19,
        "19-20": ANGULAR_19_TO_20,
    }
    if key in static_map:
        return static_map[key]
    # Unknown version pair — return generic fallback
    return _get_fallback_ruleset(from_version, to_version, f"No static rules for {key}")


def _get_fallback_ruleset(from_version: str, to_version: str, error: str = "") -> UpgradeRuleSet:
    """Return minimal fallback ruleset when dynamic fetch fails."""
    return UpgradeRuleSet(
        framework="Angular",
        from_version=from_version,
        to_version=to_version,
        verification_commands=["ng build", "ng test"],
        rules=[
            UpgradeRule(
                id=f"ng{to_version}-fallback",
                title=f"Angular {from_version} to {to_version} Upgrade",
                description=f"Dynamic fetch failed{': ' + error if error else ''}. Use ng update and refer to official docs.",
                severity=UpgradeSeverity.BREAKING,
                category=UpgradeCategory.MIGRATION,
                from_version=from_version,
                to_version=to_version,
                detection_patterns=[],
                migration_steps=[
                    f"CRITICAL: Check https://angular.dev/update-guide?v={from_version}.0-{to_version}.0&l=3 manually",
                    f"Run: ng update @angular/core@{to_version} @angular/cli@{to_version}",
                    "Follow prompts and fix breaking changes",
                    "Run: ng build --configuration production",
                    "Run: ng test",
                ],
                affected_stereotypes=[],
                effort_per_occurrence=60,
            )
        ],
    )


# =============================================================================
# Combined export
# =============================================================================

# Static rules (fallback when dynamic fetch is disabled)
ANGULAR_UPGRADE_RULES_STATIC: list = [
    ANGULAR_18_TO_19,
    ANGULAR_19_TO_20,
    ANGULAR_SIGNAL_MIGRATION,
    ANGULAR_THIRD_PARTY,
]

# Dynamic rules (fetched from angular.dev at runtime)
ANGULAR_UPGRADE_RULES: list = [
    fetch_angular_rules_dynamic("18", "19"),
    fetch_angular_rules_dynamic("19", "20"),
    ANGULAR_SIGNAL_MIGRATION,  # Keep signal migration (not version-specific)
    ANGULAR_THIRD_PARTY,  # Keep third-party compat checks
]
