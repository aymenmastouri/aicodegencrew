# Developer Context: BNUVZ-12568

## Big Picture

This repository contains the web‑frontend of the product – a large Angular single‑page application that delivers the user interface for internal and external users. The UI lives in the **presentation** layer of a multi‑container system (5 containers, >1000 components). The task is to migrate the SASS compilation step to the new Angular Builder that will be required by the upcoming Angular 19 upgrade. The migration is needed now because Angular 19 deprecates the old SASS import strategy; without it the CI/CD pipeline will break and future releases cannot be built. If we skip the migration, the next major release will be blocked and the team will have to roll back the Angular upgrade, delaying feature delivery and increasing technical debt.

## Scope Boundary

IN: All front‑end build artefacts – angular.json, package.json scripts, CI pipeline steps that invoke the Angular builder, and any SASS files that use the deprecated @import syntax. OUT: Back‑end services, domain logic, data‑access components, and any unrelated UI components that do not touch the build configuration or SASS compilation.

## Affected Components

- Angular Build Configuration (presentation layer)
- SASS Stylesheets (presentation layer)
- CI Build Pipeline (infrastructure layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 removes support for the legacy SASS compiler; the project must switch to @angular-devkit/build-angular:application or builds will fail.
_Sources: tech_versions.json: Angular 18‑lts, tech_versions.json: Angular CLI 18‑lts_

**[CAUTION] Dependency Risk**
The new builder pulls in a newer version of the SASS compiler which may have breaking changes with existing @import statements; verify that all SASS files compile after migration.
_Sources: ADR: UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation_

**[CAUTION] Testing Constraint**
Because the compiler change can affect generated CSS, additional UI regression tests should be executed to catch visual regressions.
_Sources: analysis input: Tests: 926_

**[INFO] Workflow Constraint**
CI pipelines currently invoke the old builder via npm scripts; those scripts need to be updated to reference the new builder target.
_Sources: tech_versions.json: Gradle 8.2.1, tech_versions.json: Webpack 5.80.0_

**[INFO] Pattern Constraint**
Old SASS files may use the deprecated @import syntax; the new compiler prefers @use/@forward. Identify and refactor where necessary.
_Sources: ADR: UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation_


## Architecture Walkthrough

The Angular application lives in the **frontend-webapp** container (presentation layer). The build configuration (angular.json) is a component of the **Angular Build System** which sits at the edge of the presentation layer and talks to the CI/CD infrastructure (infrastructure layer). Neighboring components include: • UI component library (Angular Material, CDK) – consumes the compiled CSS • Test runner configuration (Karma, Playwright) – validates the UI after build • Deployment scripts – package the built assets for the backend containers. The migration will touch the build system component and propagate to the CI pipeline, but will not modify domain or data‑access components.

## Anticipated Questions

**Q: Do I need to change the SASS file syntax (e.g., replace @import with @use)?**
A: Only if the new compiler reports errors. The migration itself does not require a blanket rewrite, but any files that use the deprecated @import syntax must be updated to @use/@forward to compile successfully.

**Q: Will the CI/CD pipeline need changes?**
A: Yes. The npm/Gradle scripts that invoke the Angular builder must be updated to use the new target @angular-devkit/build-angular:application. Verify the pipeline configuration after the change.

**Q: Are there any known incompatibilities with existing libraries (e.g., Angular Material, CDK)?**
A: The libraries are already on the Angular 18 LTS versions and are compatible with the new builder. However, run the full UI test suite after migration to catch any subtle style regressions.

**Q: How extensive should the testing be?**
A: Run the existing Karma unit tests and Playwright end‑to‑end tests. Add visual regression checks if they are part of the test suite, because CSS output may change.

**Q: Can we roll back if the migration causes issues?**
A: Yes. The change is confined to the build configuration and SASS files. Reverting the angular.json changes and any SASS syntax updates will restore the previous build process.


## Linked Tasks

- UVZ-09-ADR-003 (Frontend Build Strategy SASS Import Deprecation)
- Angular 19 Upgrade Epic (e.g., UVZUSLNVV-5900)