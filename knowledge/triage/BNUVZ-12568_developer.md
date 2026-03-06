# Developer Context: BNUVZ-12568

## Big Picture

Our product is a web‑based portal used by internal employees and external partners to submit and track requests. It is built as a single‑page Angular application that runs in the browser and talks to a Java‑17 backend via REST APIs. The UI is styled with SASS and compiled during the CI/CD build. The upcoming Angular 19 upgrade is a scheduled platform refresh that brings performance improvements and long‑term support. This ticket prepares the build pipeline for that upgrade by moving the SASS compilation from the legacy Webpack‑based loader to the new Angular‑Builder compiler. Doing this now ensures the next release can be built and deployed without interruption and gives us a chance to catch any styling regressions early.

## Scope Boundary

IN: Update angular.json (or workspace configuration) to use @angular-devkit/build-angular:application for SASS, adjust any SASS import statements according to ADR UVZ‑09‑ADR‑003, run the full frontend test suite, and verify CI build scripts. OUT: Changing the Angular version itself, modifying application code unrelated to styling, updating backend services, or refactoring unrelated UI components.

## Affected Components

- frontend-build (presentation)
- sass-compiler-config (presentation)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 drops support for the legacy SASS loader; the project must use the Angular‑Builder compiler to stay compatible with the framework version.
_Sources: tech_versions.json: Angular 18‑lts, ADR: UVZ-09-ADR-003 SASS Import Deprecation_

**[CAUTION] Dependency Risk**
The new compiler interacts with Webpack 5 and the existing Angular CLI 18 configuration; mismatched versions could cause build failures or incorrect CSS output.
_Sources: tech_versions.json: Webpack 5.80.0, tech_versions.json: Angular CLI 18‑lts_

**[CAUTION] Testing Constraint**
Because the SASS compilation pipeline changes, the full UI test suite (Karma + Playwright) must be executed to detect regressions in styling or component rendering.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_

**[INFO] Pattern Constraint**
The ADR mandates deprecation of the old "@import" syntax in SASS; existing style sheets may need to be rewritten to use the new module system.
_Sources: ADR: UVZ-09-ADR-003 SASS Import Deprecation_

**[CAUTION] Workflow Constraint**
The CI pipeline currently invokes "ng build" via Gradle scripts; the build step must be updated to pass the new builder configuration without breaking the Gradle‑Angular integration.
_Sources: tech_versions.json: Gradle 8.2.1, tech_versions.json: Angular CLI 18‑lts_


## Architecture Walkthrough

The SASS compilation lives in the **frontend** container, specifically in the **presentation** layer. It is part of the build‑time tooling and is invoked by the Angular CLI (which sits in the same container). The component responsible for the configuration is the "frontend‑build" module (presentation layer). Neighbouring components are:
- "angular‑workspace" (presentation) – holds angular.json where the builder is defined.
- "webpack‑config" (presentation) – currently used for asset bundling; will be consulted by the new builder.
- "ci‑pipeline" (infrastructure) – Gradle script that triggers "npm install" and "ng build".
- "ui‑component library" (presentation) – consumes the compiled CSS at runtime.
The developer will be editing the build configuration and possibly some SASS files, but will not touch runtime code or backend containers.

## Anticipated Questions

**Q: Do we need to upgrade Angular to version 19 before switching the SASS compiler?**
A: No. The new Angular‑Builder compiler can be configured while still on Angular 18, but the migration is required before the Angular 19 upgrade because the old compiler will be removed in Angular 19.

**Q: Will existing "@import" statements in SASS break after the migration?**
A: Yes, the ADR states that the old import syntax is deprecated. Any "@import" usages should be converted to the module‑based "@use" syntax before or during the migration to avoid compilation errors.

**Q: Do we have to modify the CI/CD Gradle scripts?**
A: Only the part that invokes the Angular build may need a flag or updated builder name. The overall Gradle workflow stays the same, but the change must be verified so the pipeline does not fail.

**Q: What testing is expected after the change?**
A: Run the full frontend test suite (Karma unit tests and Playwright end‑to‑end tests) and manually verify that styled components render correctly. Pay special attention to pages that rely heavily on SASS variables or mixins.

**Q: Is there any impact on the backend or other containers?**
A: No. The change is confined to the frontend build process and does not affect backend services, data access, or domain logic.


## Linked Tasks

- UVZ-09-ADR-003 (Frontend Build Strategy SASS Import Deprecation)
- SUPPORT-5885 (Angular 19 framework upgrade preparation)