# Developer Context: BNUVZ-12568

## Big Picture

The frontend engineering team maintains a large, multi‑container web application built with Angular 18‑LTS that serves internal and external users via a rich UI. Angular 19 will deprecate the legacy SASS compiler, so the build container must be switched to the new Angular Builder SASS compiler now to keep the build pipeline functional. If we postpone the migration, the build will fail after the framework upgrade, causing a release block and potential downtime for all users.

## Scope Boundary

IN: All build‑related configuration files (angular.json, tsconfig.json) that reference the SASS compiler, the SASS import statements that may be affected by the deprecation described in ADR UVZ‑09‑ADR‑003, CI pipeline steps that invoke the Angular build, and any unit/e2e tests that verify style rendering. OUT: Application runtime code (components, services, business logic), backend services, database schema, and any unrelated UI features that do not touch the build pipeline.

## Affected Components

- Angular Build Configuration (infrastructure)
- SASS Compilation Pipeline (infrastructure)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 removes the legacy SASS compiler; the project must adopt @angular-devkit/build-angular:application or the build will fail after the framework upgrade.
_Sources: tech_versions.json: Angular 18‑lts, ADR: https://wiki.bnotk.de/spaces/UVZUSLNAS/pages/386958007/UVZ-09-ADR-003+-+Frontend+Build+Strategy+SASS+Import+Deprecation_

**[CAUTION] Dependency Risk**
The new SASS compiler changes how @import statements are resolved; existing SASS files that rely on the deprecated import style may break and need refactoring.
_Sources: ADR: https://wiki.bnotk.de/spaces/UVZUSLNAS/pages/386958007/UVZ-09-ADR-003+-+Frontend+Build+Strategy+SASS+Import+Deprecation_

**[INFO] Testing Constraint**
Because the compiler change can affect generated CSS, all visual regression tests (Karma, Playwright) must be re‑run to ensure no styling regressions are introduced.
_Sources: analysis_input: Karma 6.4.3, analysis_input: Playwright 1.44.1_

**[CAUTION] Workflow Constraint**
The CI pipeline currently invokes "ng build" via Gradle 8.2.1; the Gradle task may need to be updated to pass the new builder options.
_Sources: tech_versions.json: Gradle 8.2.1, tech_versions.json: Angular CLI 18‑lts_


## Architecture Walkthrough

The SASS compiler lives in the **frontend build container** (one of the 5 top‑level containers). Within that container the relevant layer is **infrastructure** (build & deployment). The primary component is the **Angular Builder configuration** (angular.json) which is consumed by the **Angular CLI** (presentation‑layer tooling) and feeds the **Webpack** bundler. Neighbouring components include the **Karma** unit‑test runner, **Playwright** e2e runner, and the **CI/CD pipeline** (Gradle tasks). Updating the builder will affect the flow: source SASS → Angular Builder → Webpack → bundled CSS → UI components. No runtime business logic components are touched.

## Anticipated Questions

**Q: Do I need to modify angular.json manually, or is there a schematic to migrate the builder?**
A: The migration requires changing the "builder" entry for the application target to "@angular-devkit/build-angular:application" and ensuring any SASS‑specific options are moved to the new schema. No schematic is provided yet, so manual edit is expected.

**Q: Will existing SASS files compile without changes?**
A: Only if they use the new import syntax. Files that still use the deprecated "@import" style may fail; the ADR outlines the required changes, so those files should be reviewed and updated accordingly.

**Q: How does this affect the CI pipeline that runs Gradle builds?**
A: Gradle invokes "ng build"; after the builder change the command line arguments may differ. Verify the Gradle task configuration and adjust any custom flags that were specific to the old compiler.

**Q: Do we need to update any test configurations?**
A: No test code changes are required, but all visual regression suites (Karma unit tests, Playwright e2e tests) should be re‑executed after the migration to catch styling regressions.

**Q: Is there any impact on other libraries like Webpack or RxJS?**
A: The SASS compiler runs before Webpack bundles the assets, so Webpack itself is unaffected. RxJS and other runtime libraries are unrelated to the build‑time SASS compilation.


## Linked Tasks

- UVZ-09-ADR-003 (Frontend Build Strategy SASS Import Deprecation)
- Angular 19 upgrade epic (if any) – reference ticket UVZUSLNVV-5890