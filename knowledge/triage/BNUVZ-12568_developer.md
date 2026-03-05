# Developer Context: BNUVZ-12568

## Big Picture

Our system is a large, multi‑container web platform that delivers a rich UI to internal and external users via an Angular front‑end. The presentation layer (≈287 components) contains all UI widgets, pages and style assets. The product is currently on Angular 18 LTS and will be upgraded to Angular 19 as part of the scheduled major release. This ticket addresses the build‑time part of that upgrade: the SASS compiler that Angular 18 used is deprecated and will no longer work with Angular 19. The migration to the new @angular-devkit/build-angular:application builder ensures the UI continues to compile, styles are processed correctly, and the CI pipeline stays green. It must be done now because the Angular 19 upgrade is imminent; delaying would cause a hard break in the CI build and potentially ship a UI that cannot render correctly.

## Scope Boundary

IN: The Angular build configuration (angular.json) using @angular-devkit/build-angular:application, any SASS import statements that need to follow the pattern defined in ADR UVZ‑09‑ADR‑003, and verification through the full front‑end test suite (Karma, Playwright) to ensure UI rendering without regression. OUT: Business logic changes, backend services, domain or data‑access layers, and any non‑style related refactorings. The migration does not affect the Java 17 backend, security exception handling, or infrastructure containers.

## Affected Components

- Angular build configuration (application layer)
- SASS style files used by UI components (presentation layer)
- CI build pipeline for front‑end (infrastructure layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 removes the legacy SASS compiler; the project must switch to the new builder to stay compatible with the framework version.
_Sources: tech_versions.json: Angular 18‑lts (current), tech_versions.json: Angular CLI 18‑lts (current), ADR: UVZ‑09‑ADR‑003 (SASS import deprecation)_

**[CAUTION] Dependency Risk**
The current build chain uses Webpack 5.80.0; the new builder may replace Webpack with an internal bundler, so any custom Webpack plugins or loader configurations must be reviewed for compatibility.
_Sources: tech_versions.json: Webpack 5.80.0, tech_versions.json: TypeScript 4.9.5_

**[INFO] Testing Constraint**
Because the SASS compilation path changes, style‑related unit tests (Karma) and end‑to‑end tests (Playwright) may surface regressions; a full test run is required after migration.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_

**[CAUTION] Workflow Constraint**
CI pipelines currently invoke the old Angular builder; pipeline scripts must be updated to call the new builder and any caching steps that depend on Webpack output need adjustment.
_Sources: tech_versions.json: Gradle 8.2.1 (used for backend builds, not directly affected but indicates overall CI tooling)_


## Architecture Walkthrough

YOU ARE HERE: Front‑end container → Application layer (Angular build system) → Presentation layer (UI components with SASS). The Angular build configuration (angular.json) lives in the application layer and is consumed by the CI pipeline (infrastructure layer). UI components import SASS files; those files are compiled by the SASS compiler. After migration, the compiler is provided by @angular-devkit/build-angular:application instead of the legacy Webpack loader. Neighboring pieces: the Karma test runner (presentation layer) and Playwright e2e tests (infrastructure layer) will consume the compiled CSS. No backend containers are touched.

## Anticipated Questions

**Q: Do I need to modify any existing SASS files?**
A: Only if they use the deprecated import syntax highlighted in ADR UVZ‑09‑ADR‑003. Most files can stay unchanged; just ensure imports follow the new pattern.

**Q: Will the TypeScript version (4.9.5) cause any issues with the new builder?**
A: The new builder is compatible with TypeScript 4.9.x, which is already used in the project, so no version conflict is expected.

**Q: What about the CI pipeline – do I have to change the Gradle build?**
A: Gradle itself is unchanged, but the front‑end build step in the pipeline must be pointed at the new builder. No backend Gradle scripts need modification.

**Q: How extensive should the testing be after migration?**
A: Run the full suite: all Karma unit tests for components, plus the Playwright end‑to‑end tests. Pay special attention to visual regressions in components that heavily rely on SASS.

**Q: Is there a fallback if the migration breaks the build?**
A: You can revert the angular.json changes and keep using the old builder until the issue is resolved, but the project will not be able to upgrade to Angular 19 until the migration succeeds.
