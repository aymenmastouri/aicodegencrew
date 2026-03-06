# Developer Context: BNUVZ-12568

## Big Picture

Our product is a web‑based portal built with Angular that is used by internal employees and external partners to perform day‑to‑day business processes. The UI lives in the *presentation* layer of the overall system (5 containers, ~1000 components). The upcoming Angular 19 release brings a new default SASS compiler that is part of the Angular Builder. This task ensures the UI can still be built and styled after the framework upgrade. It is needed now because the current SASS compiler is deprecated and will be removed in Angular 19, which would cause build failures and visual regressions. If we do not migrate, the CI pipeline will break and users may see broken styling after the framework upgrade.

## Scope Boundary

IN: Update the Angular build configuration (angular.json) to use @angular-devkit/build-angular:application, adjust any custom webpack or SASS loader settings, verify that all .scss files compile with the new Dart‑Sass compiler, run the full UI test suite (Karma + Playwright) to catch regressions. OUT: Backend Java services, domain logic, data‑access components, any non‑Angular micro‑frontends, and unrelated infrastructure containers.

## Affected Components

- Angular UI Application (presentation)
- Build Pipeline / CI (infrastructure)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 drops support for the legacy node‑sass compiler; the project must switch to the built‑in Dart‑Sass compiler provided by @angular-devkit/build-angular:application. This forces a change in the build configuration and may affect any custom SASS import paths.
_Sources: tech_versions.json: Angular 18‑lts, tech_versions.json: Angular CLI 18‑lts, ADR: UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation_

**[CAUTION] Dependency Risk**
The current dependency list does not show an explicit sass package; after migration the project must add a compatible version of the 'sass' npm package (Dart‑Sass). Compatibility with other Angular packages (animations, cdk, common, core) must be verified for version 19.
_Sources: dependencies.json: @angular/* v18‑lts_

**[INFO] Testing Constraint**
Because the SASS compilation pipeline changes, existing unit tests (Karma) and end‑to‑end tests (Playwright) must be executed to ensure no visual regressions or broken style imports appear.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_

**[CAUTION] Workflow Constraint**
The CI/CD pipeline currently invokes the Angular Builder via Webpack. Switching to the new builder may require updates to the pipeline scripts and Docker images that contain the build tools (Gradle, Node).
_Sources: tech_versions.json: Gradle 8.2.1, tech_versions.json: Webpack 5.80.0_


## Architecture Walkthrough

The Angular UI lives in the *presentation* container (one of the five system containers). Within that container it belongs to the *presentation* layer and is composed of many UI components (≈287). The build configuration (angular.json) is part of the infrastructure for this container. The migration touches the build step that produces the final bundle consumed by the browser. Neighboring components are the style assets (.scss files) and the test suites (Karma unit tests, Playwright e2e tests). The change does not cross container boundaries – it stays inside the UI container – but it influences the CI pipeline that orchestrates builds for all containers.

## Anticipated Questions

**Q: Do we need to add a new npm dependency for the Sass compiler?**
A: Yes. The new Angular Builder expects the 'sass' package (Dart‑Sass). Adding a compatible version (e.g., ^1.77.0) is required.

**Q: Will existing .scss files need to be rewritten?**
A: Most files will work unchanged, but any usage of the deprecated "@import" syntax may need to be updated to the newer "@use"/"@forward" pattern as described in the ADR.

**Q: How do we verify that the migration did not break the UI?**
A: Run the full suite of Karma unit tests and Playwright end‑to‑end tests after the migration. Pay special attention to visual regression tests if they exist.

**Q: Does the CI pipeline need changes?**
A: The pipeline must use the updated Angular CLI version (19) and ensure the Node image contains the new 'sass' package. Any custom webpack steps that were previously required for SASS can be removed.

**Q: Is there any impact on backend services?**
A: No. The migration is confined to the frontend build process and does not affect Java services, domain logic, or data‑access layers.


## Linked Tasks

- UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation
- https://jira.bnotk.de/browse/UVZUSLNVV-5890