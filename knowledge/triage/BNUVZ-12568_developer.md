# Developer Context: BNUVZ-12568

## Big Picture

The project is a large internal web application built with Angular (currently v18‑LTS) that serves business users of Bnotk. All UI components (≈287) live in the presentation layer and rely on SASS for styling. The company plans to upgrade the whole front‑end stack to Angular 19. Angular 19 deprecates the old SASS import mechanism, so the build will break unless the SASS compiler is switched to the new Angular Builder (`@angular-devkit/build-angular:application`). This task prepares the application for the upcoming major framework upgrade and prevents a complete front‑end build failure after the upgrade. If the migration is not done, the CI pipeline will stop, deployments will be blocked, and users will lose access to the UI.

## Scope Boundary

IN: All front‑end build artefacts – `angular.json`, any custom webpack configuration, SASS files, style‑related npm scripts, and the CI/CD steps that invoke the Angular build. Unit and e2e test suites (Karma, Playwright) that compile styles. 
OUT: Backend Java services, database schemas, non‑UI domain logic, and any infrastructure that is not part of the front‑end build pipeline.

## Affected Components

- Angular Build Configuration (presentation layer)
- SASS Style Sheets used by UI components (presentation layer)
- CI/CD Front‑end Build Pipeline (infrastructure layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 removes the legacy SASS compiler; the project must switch to the new builder (`@angular-devkit/build-angular:application`). This is a hard requirement for the upcoming framework upgrade.
_Sources: issue_context: Migration des SASS Compiler, ADR: UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation_

**[CAUTION] Dependency Risk**
All `@angular/*` packages are currently pinned to v18‑LTS. Upgrading the SASS compiler implies upgrading the entire Angular package set to v19, which may introduce version mismatches with other libraries (e.g., RxJS, Angular CDK). Compatibility must be verified.
_Sources: tech_versions.json: Angular 18‑lts, dependencies.json: @angular/* v18‑lts_

**[INFO] Testing Constraint**
The new compiler changes the way styles are processed; unit tests (Karma) and e2e tests (Playwright) that rely on compiled CSS may start failing. Additional regression testing is required to catch visual or functional regressions.
_Sources: issue_context: "additional testing may be necessary", tech_versions.json: Playwright 1.44.1, Karma 6.4.3_

**[CAUTION] Workflow Constraint**
The CI pipeline currently invokes `ng build` with the legacy builder. The pipeline scripts must be updated to reference the new builder target, and any caching or artifact steps that assume the old output layout need review.
_Sources: issue_context: Migration to @angular-devkit/build-angular:application_


## Architecture Walkthrough

The front‑end lives in its own container (the "frontend" container) and occupies the **presentation** layer of the overall system. The primary component involved is the Angular application module, which is wired to the build system via `angular.json`. This component interacts with:
- **Style libraries** (shared SASS files) that are imported by UI components.
- **CI/CD pipeline** (infrastructure layer) that runs `ng build` during each release.
- **Test runners** (Karma for unit tests, Playwright for e2e) that compile the styles as part of the test build.
The migration will touch the build configuration (angular.json), any custom webpack config that currently handles SASS, and the CI scripts that invoke the build. All UI components that import SASS remain unchanged; only the compilation step changes. Think of the map as: **Frontend Container → Presentation Layer → Angular App (build config) → Neighbors: Style assets, CI pipeline, Test runners**.

## Anticipated Questions

**Q: Do we need to modify existing SASS files (e.g., import statements) after switching to the new compiler?**
A: In most cases the new Angular Builder supports the same import syntax, but the deprecation notice in the ADR mentions that certain legacy import patterns are no longer allowed. Review the SASS files for deprecated `@import` usage and replace with the modern `@use`/`@forward` syntax where needed.

**Q: Will the Angular CLI version also need to be upgraded to 19, and does that affect other parts of the build?**
A: Yes. The SASS compiler migration is part of the Angular 19 upgrade, so the Angular CLI must be upgraded to the 19.x series. This upgrade may bring other breaking changes (e.g., changes to the default builder, removal of Webpack configuration). Those changes should be evaluated alongside the SASS migration.

**Q: How does this change impact our CI/CD pipeline?**
A: The pipeline currently calls `ng build` with the legacy builder target. After migration the target must be changed to `@angular-devkit/build-angular:application`. Any caching of build artefacts or assumptions about output directories may need adjustment.

**Q: What testing effort is expected?**
A: Run the full suite of Karma unit tests and Playwright e2e tests after the migration. Pay special attention to visual regression tests or snapshot tests that compare rendered CSS. If failures appear, they are likely due to differences in how the new compiler processes SASS.

**Q: Are there any other Angular 19 breaking changes we should be aware of before starting?**
A: Beyond the SASS compiler, Angular 19 introduces changes to the Ivy compiler, stricter type checking, and possible removal of deprecated APIs. While the ticket focuses on SASS, it is advisable to review the Angular 19 release notes for other breaking changes that may affect the application.


## Linked Tasks

- UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation