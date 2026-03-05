# Developer Context: BNUVZ-12568

## Big Picture

Our product is a web‑based client application that serves external users (e.g., customers of the BNOTK platform). It is built with Angular (currently v18 LTS) and lives in the *frontend* container, which belongs to the **presentation** layer of the overall system (5 containers, ~1000 components). The UI components import SASS style sheets for theming and layout. The upcoming Angular 19 release removes support for the old SASS import mechanism, requiring the new Angular Builder (`@angular-devkit/build-angular:application`) that bundles an updated SASS compiler. This task prepares the UI build pipeline for the framework upgrade, preventing a broken build and UI regressions that would affect every user.

## Scope Boundary

IN: Update `angular.json` (or workspace configuration) to use `@angular-devkit/build-angular:application` as the builder for the application target, adjust any SASS import statements that rely on the deprecated `@import` syntax, and run the full frontend test suite (Karma unit tests and Playwright end‑to‑end tests) to verify that styles render correctly. OUT: Any other Angular 19 migration work (e.g., RxJS upgrades, Ivy changes), backend code, Gradle build changes, or non‑frontend infrastructure updates.

## Affected Components

- Angular UI components (presentation layer)
- Build configuration (infrastructure layer – angular.json / workspace)
- Style assets (SASS files used across the presentation layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 deprecates the legacy SASS compiler; the new builder is mandatory for a successful build after the framework upgrade.
_Sources: tech_versions.json: Angular 18-lts, ADR: UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation_

**[CAUTION] Dependency Risk**
The new builder may have tighter coupling with the Angular CLI and Webpack versions currently in use (Angular CLI 18‑lts, Webpack 5.80.0). Compatibility must be verified to avoid build‑time failures.
_Sources: tech_versions.json: Angular CLI 18-lts, tech_versions.json: Webpack 5.80.0_

**[CAUTION] Testing Constraint**
Because style compilation changes can silently affect UI rendering, the entire frontend test suite (Karma unit tests and Playwright e2e tests) must be executed after migration to catch regressions.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_

**[CAUTION] Integration Boundary**
Many presentation‑layer components import SASS files using the deprecated `@import` syntax. Those imports need to be updated to the new `@use`/`@forward` pattern, otherwise the new compiler will throw errors.
_Sources: analysis input: Architecture Overview – presentation layer contains 287 components that rely on SASS_

**[INFO] Workflow Constraint**
CI/CD pipelines that cache the Angular build artifacts must be updated to install the new builder package and clear any stale caches that reference the old compiler.
_Sources: tech_versions.json: Gradle 8.2.1 (used for overall build orchestration), tech_versions.json: Java 17 (runtime for CI agents)_


## Architecture Walkthrough

WALKTHROUGH: The frontend lives in its own **container** (e.g., `frontend-webapp`). Inside this container the **presentation layer** holds all Angular components (≈287). The SASS compiler is part of the **infrastructure layer** – specifically the Angular build configuration (`angular.json`) that the Angular CLI (currently 18‑lts) invokes. The builder (`@angular-devkit/build-angular:application`) sits between the CLI and the Webpack bundler, orchestrating how SASS files are compiled into CSS. Neighboring pieces are:
- **Presentation components** that import SASS files.
- **Testing framework** (Karma + Playwright) that validates the rendered UI.
- **CI pipeline** that runs `ng build` during the release process.
Changing the builder therefore touches the build config (infrastructure), all style imports (presentation), and the CI workflow (operations). No backend containers or domain logic are directly affected.

## Anticipated Questions

**Q: Do I need to modify the existing SASS files themselves?**
A: Only if they use the deprecated `@import` syntax. The migration guide (ADR) recommends converting those to the new `@use`/`@forward` syntax. Files that already use the new syntax can stay unchanged.

**Q: Will this affect the current CI/CD pipeline?**
A: Yes. The pipeline installs the Angular CLI and runs the build. After switching to the new builder you must ensure the CI environment pulls the updated `@angular-devkit/build-angular` package and clears any cached build artifacts that reference the old compiler.

**Q: What tests should I run after the migration?**
A: Run the full suite of frontend unit tests (Karma) and end‑to‑end tests (Playwright). Pay special attention to visual regression tests or any tests that assert CSS class presence, as style compilation changes can affect those.

**Q: Is there any impact on the backend or other containers?**
A: No. The change is confined to the frontend container's build process and style assets. Backend services, domain logic, and data‑access layers remain untouched.

**Q: What version of the new builder should I target?**
A: Use the version that ships with Angular 19 (the one referenced in the Angular 19 release notes). It will be compatible with the Angular CLI version that will be upgraded alongside this migration.


## Linked Tasks

- UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation
- UVZUSLNVV-5890 (Angular 19 framework upgrade)
- Potential follow‑up task: Update Angular CLI to 19.x