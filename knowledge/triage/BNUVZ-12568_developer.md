# Developer Context: BNUVZ-12568

## Big Picture

This repository hosts the web front‑end of the product – a single‑page application used by internal employees and external customers to interact with the core business services. The UI is built with Angular, styled with SASS, and delivered through a CI/CD pipeline that packages the static assets for the backend containers. The current task is to migrate the SASS compilation from the deprecated Angular Builder to the new @angular-devkit/build-angular:application builder that will be required for the upcoming Angular 19 upgrade. The migration is needed now because the Angular 19 release schedule is fixed, and the old compiler will be removed, causing immediate build breakage if left unchanged. Not performing the migration would block the Angular 19 upgrade, halt deployments, and increase the risk of regressions in the UI styling.

## Scope Boundary

IN: All front‑end build artefacts that involve SASS compilation – angular.json configuration, any custom webpack or builder scripts, CI pipeline steps that invoke the Angular build, and the associated unit/e2e tests that verify compiled CSS. OUT: Back‑end Java services, domain logic, data‑access layer, and any unrelated UI components that do not touch the build configuration. The migration does not touch runtime code, only build‑time tooling.

## Affected Components

- Angular Build Configuration (presentation layer)
- SASS Compilation Setup (infrastructure layer)
- CI Build Pipeline – Frontend Job (infrastructure layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 removes the legacy SASS compiler; the new @angular-devkit/build-angular:application builder must be used for any SASS imports. This forces a change in the build configuration before the Angular version bump.
_Sources: tech_versions.json: Angular 18-lts, ADR: UVZ-09-ADR-003 (Frontend Build Strategy SASS Import Deprecation)_

**[CAUTION] Dependency Risk**
Current runtime dependencies list only @angular/* packages at v18‑lts. Upgrading the builder may introduce transitive dependencies that require newer @angular packages, so version compatibility must be verified.
_Sources: dependencies.json: @angular/core v18-lts, dependencies.json: @angular/compiler v18-lts_

**[INFO] Testing Constraint**
The ticket explicitly notes that additional testing may be required to catch regressions caused by the new compiler. All existing Karma unit tests and Playwright e2e tests must be run after migration.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_

**[INFO] Workflow Constraint**
The CI pipeline currently invokes "ng build" via Gradle 8.2.1 scripts. The pipeline will need to be updated to use the new builder flag, but the surrounding Gradle orchestration remains unchanged.
_Sources: tech_versions.json: Gradle 8.2.1, tech_versions.json: Angular CLI 18-lts_


## Architecture Walkthrough

The front‑end lives in its own container (e.g., **frontend-web**). Within that container the code is organized by layers: presentation (Angular components, templates, SASS files), application (services, state management), and infrastructure (build scripts, CI jobs). The SASS compiler is part of the **infrastructure layer** – it is invoked by the Angular build configuration (angular.json) which lives in the presentation layer but is executed by the infrastructure tooling. Neighboring components are:
- **Angular Build Configuration** (presentation) – defines which builder to use.
- **CI Build Job** (infrastructure) – runs "ng build" during the pipeline.
- **Unit/E2E Test Suites** (application/presentation) – consume the compiled CSS.
The migration will therefore touch the build configuration file and the CI job, but the rest of the component graph (UI components, services, domain logic) stays untouched.

## Anticipated Questions

**Q: Do I need to update any Angular package versions besides the builder?**
A: Only the builder flag changes, but because the new builder may depend on newer @angular/core/@angular/compiler packages, verify that the existing v18‑lts packages are still compatible. If the builder pulls in v19 packages, you will need to upgrade the Angular packages together with the builder.

**Q: Will the existing SASS files need to be rewritten?**
A: No functional rewrite is required; the new builder supports the same SASS syntax. However, import paths that relied on the deprecated "@import" behaviour should be checked, as the ADR mentions deprecation of certain import styles.

**Q: How extensive is the testing effort?**
A: Run the full suite of Karma unit tests and Playwright e2e tests after the migration. Pay special attention to visual regression tests (if any) because CSS output may differ slightly with the new compiler.

**Q: Is there a fallback if the migration breaks the build?**
A: You can temporarily revert the angular.json change and keep the project on Angular 18 until the issue is resolved. The CI pipeline can be configured to use a feature branch for the migration to avoid blocking the main build.

**Q: Does this affect the backend Java services?**
A: No. The migration is confined to the front‑end build pipeline and does not touch any Java code, domain logic, or data‑access components.


## Linked Tasks

- UVZ-09-ADR-003 – Frontend Build Strategy SASS Import Deprecation
- UVZUSLNVV-5890 – Migration des SASS Compiler