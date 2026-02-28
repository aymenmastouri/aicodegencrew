# Developer Context: BNUVZ-12568

## Big Picture

Our product is a large, multi‑container web application that serves internal users (e.g., staff, partners) via a rich Angular front‑end. The front‑end lives in the **presentation** layer (≈200 UI components) and is built by the **infrastructure** layer using Angular CLI, Webpack and a SASS stylesheet pipeline. The upcoming Angular 19 release deprecates the old SASS import strategy, so the build must switch to the new SASS compiler provided by the Angular Builder. This task guarantees that the UI can continue to be compiled, styled and deployed without interruption. The migration is required now because the Angular 19 upgrade is scheduled for the next release cycle; delaying it would cause the CI pipeline to fail and block any further front‑end releases.

## Scope Boundary

IN: Update `angular.json` (or workspace configuration) to use `@angular-devkit/build-angular:application` as the builder for all Angular applications, adjust any SASS `@import` statements that the new compiler flags as deprecated, run the full unit‑test suite (Karma) and end‑to‑end tests (Cypress/Playwright) to verify no visual regressions. OUT: Changes to backend Java services, migration of unrelated third‑party libraries, redesign of UI components, or changes to the CI infrastructure that are unrelated to the Angular build process.

## Affected Components

- Angular build configuration (infrastructure layer)
- SASS stylesheet files (presentation layer)
- CI build pipeline steps that invoke Angular CLI (infrastructure layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 no longer supports the legacy SASS compiler; the project must switch to the builder‑provided compiler or builds will fail.
_Sources: tech_versions.json: Angular 18.2.13 (current), ADR: UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation_

**[CAUTION] Dependency Risk**
The new SASS compiler may have stricter import rules; existing `@import` statements could cause compilation errors or subtle style changes, so they need verification.
_Sources: tech_versions.json: Webpack 5.80.0 (build tool), tech_versions.json: TypeScript 4.9.5 (language)_

**[INFO] Testing Constraint**
Because the compiler change can affect generated CSS, the full suite of unit (Karma) and e2e (Cypress, Playwright) tests must be executed to catch regressions.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Cypress 14.0.3, tech_versions.json: Playwright 1.43.1_

**[INFO] Workflow Constraint**
CI pipelines that cache the Angular build output may need cache invalidation after the builder switch to avoid stale artifacts.
_Sources: tech_versions.json: Gradle 8.2.1 (overall build orchestrator)_


## Architecture Walkthrough

The front‑end lives in the **frontend container** (one of the five system containers). Within that container the **presentation layer** holds all UI components and SASS files. The **infrastructure layer** contains the Angular CLI build configuration (`angular.json`) and the CI scripts that invoke `ng build`. The migration touches the infrastructure layer (builder definition) and the presentation layer (SASS imports). Neighboring components are the unit‑test runner (Karma) and e2e test runners (Cypress/Playwright) that consume the compiled CSS. No other containers (e.g., backend Java services) are directly impacted.

## Anticipated Questions

**Q: Do I need to modify any SASS files, or is changing the builder enough?**
A: Changing the builder is mandatory, but the new compiler enforces stricter import rules. After the builder switch, run the build locally; any compilation errors will point to SASS files that need their `@import` statements updated.

**Q: Will this affect the CI pipeline or require changes to Gradle scripts?**
A: Only the part of the pipeline that runs `ng build` may need cache invalidation. No changes to Gradle itself are required unless the pipeline explicitly caches Angular build artifacts.

**Q: What tests should I run to ensure nothing regressed?**
A: Execute the full unit‑test suite (Karma) and all end‑to‑end tests (Cypress and Playwright). Pay special attention to visual regression tests, if any, because CSS output may differ.

**Q: Is there a fallback if the new compiler breaks the build?**
A: You can revert the `angular.json` builder entry to the previous value and restore the repository state, but the goal is to keep the migration in the same branch and verify it before merging.

**Q: Are there any other libraries that need to be upgraded alongside Angular 19?**
A: The migration focuses on the SASS compiler. Other libraries (RxJS, Webpack, etc.) remain at their current versions for now, but they should be re‑tested after the Angular upgrade.


## Linked Tasks

- UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation
- SUPPORT-5890 (this ticket)