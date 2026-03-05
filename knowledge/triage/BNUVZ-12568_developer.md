# Developer Context: BNUVZ-12568

## Big Picture

The project is a large, multi‑container web application (5 containers, >1000 components) whose user‑facing part is an Angular SPA living in the presentation container. End users are internal employees and external customers who interact with the UI for core business processes. This ticket addresses the need to modernise the frontend build pipeline: the current SASS compiler is deprecated and will be removed in Angular 19, so the Angular build must switch to the new @angular-devkit/build-angular:application builder. The migration is required now because the roadmap includes an Angular 19 upgrade; postponing it would make the next release impossible without a rushed, high‑risk fix.

## Scope Boundary

IN: Update the Angular build configuration (angular.json) to use @angular-devkit/build-angular:application, adjust any SASS import syntax that the new compiler deprecates, run the full unit (Karma) and end‑to‑end (Playwright) test suites, and verify CI/CD pipeline steps that invoke the Angular build. OUT: Any changes to backend services, domain logic, data‑access components, or unrelated UI components that do not touch the build configuration or SASS files.

## Affected Components

- Angular Build Configuration (presentation layer)
- SASS Compilation Pipeline (presentation layer)
- CI Build Job (infrastructure/container handling builds)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 will drop the legacy SASS compiler; the project must adopt the new builder to stay compatible with the upcoming framework version.
_Sources: tech_versions.json: Angular 18-lts, ADR: UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation_

**[CAUTION] Dependency Risk**
The new @angular-devkit/build-angular:application brings its own SASS version. All @angular/* packages must be upgraded in lockstep to avoid version mismatches.
_Sources: dependencies.json: @angular/core v18-lts, dependencies.json: @angular/compiler v18-lts_

**[CAUTION] Testing Constraint**
After changing the builder, existing Karma unit tests and Playwright e2e tests must be executed to catch regressions caused by SASS compilation differences.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_

**[INFO] Workflow Constraint**
CI pipelines that invoke "ng build" will need to reference the new builder target; scripts or Docker images that pin the old builder may fail.
_Sources: tech_versions.json: Gradle 8.2.1 (used for CI orchestration)_


## Architecture Walkthrough

WALKTHROUGH: The change lives entirely in the **presentation container** (the Angular SPA). Within that container, it touches the **presentation layer** (build configuration, SASS assets). The primary component is the **Angular Build Configuration** (angular.json) which is consumed by the **CI Build Job** (infrastructure container) during the pipeline. Downstream, the **Karma unit test runner** and **Playwright e2e runner** consume the compiled assets, so they are neighboring components that must be re‑run after migration. No other containers (e.g., domain, data‑access, infrastructure services) are impacted.

## Anticipated Questions

**Q: Do we need to upgrade the whole Angular framework to version 19 now, or only the SASS builder?**
A: Only the builder needs to be switched to @angular-devkit/build-angular:application for the migration. The full Angular 19 upgrade can be performed later, but the builder change must happen now to avoid future incompatibility.

**Q: Will any existing .scss files need to be rewritten?**
A: The new compiler deprecates certain import syntaxes (e.g., tilde‑based imports). Review the ADR for the exact deprecations; most files will work unchanged, but any usage of the old import style must be updated.

**Q: How will this affect our CI/CD pipeline?**
A: The pipeline step that runs "ng build" must reference the new builder target. Verify that the Docker image or Node version used in CI supports the newer @angular-devkit version.

**Q: Are there any known breaking changes that could cause test failures?**
A: The SASS compiler may produce slightly different CSS output, which can affect visual regression tests. Run the full Karma and Playwright suites after migration to catch any discrepancies.

**Q: Is there a fallback if the migration introduces issues?**
A: You can temporarily revert the angular.json change and continue using the legacy builder on Angular 18, but this will postpone the required upgrade and must be addressed before the Angular 19 release.


## Linked Tasks

- UVZUSLNVV-5890 (Angular 19 upgrade planning)
- UVZ-09-ADR-003 (Frontend Build Strategy SASS Import Deprecation)