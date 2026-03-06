# Developer Context: BNUVZ-12568

## Big Picture

We run a large Angular front‑end (the "frontend‑webapp" container) that delivers the UI for internal and external users. The UI is styled with SASS and built via the Angular CLI. The upcoming Angular 19 upgrade deprecates the previous SASS compilation path, so the build must be switched to the new Angular Builder (`@angular-devkit/build-angular:application`). This task ensures the UI can continue to be built and delivered after the framework upgrade. It is needed now because the Angular 19 release is scheduled for the next sprint; delaying the migration would cause the CI pipeline to break and could postpone the overall product release. Without the migration the application would either fail to compile or render with broken styles, harming the user experience.

## Scope Boundary

IN: All Angular build configuration files (e.g., `angular.json`), SASS import statements, custom Webpack or builder plugins related to style processing, and the CI/CD pipeline steps that invoke the Angular build. OUT: Backend Java services, unrelated Angular modules that do not touch SASS, database schemas, and any non‑frontend infrastructure.

## Affected Components

- Angular Build Configuration (infrastructure layer)
- SASS Compilation Pipeline (infrastructure layer)
- CI/CD Build Step for Frontend (application layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 no longer supports the legacy SASS import syntax; the project must switch to the new builder (`@angular-devkit/build-angular:application`). This is a blocking change because the old builder will cause the build to fail after the framework upgrade.
_Sources: tech_versions.json: Angular 18-lts, ADR: https://wiki.bnotk.de/spaces/UVZUSLNAS/pages/386958007/UVZ-09-ADR-003+-+Frontend+Build+Strategy+SASS+Import+Deprecation_

**[CAUTION] Dependency Risk**
The new builder pulls in a newer version of the SASS compiler which must be compatible with the existing TypeScript (4.9.5) and other Angular packages (animations, core, etc.). Verify that no peer‑dependency conflicts arise after the switch.
_Sources: dependencies.json: @angular/core v18-lts, tech_versions.json: TypeScript 4.9.5_

**[INFO] Testing Constraint**
Because the SASS compilation path changes, visual regression tests and unit tests that rely on compiled CSS may start failing. Additional testing is required to ensure no regressions in UI appearance.
_Sources: issue_context: "additional testing may be necessary to minimize the risk of potential regressions"_


## Architecture Walkthrough

The front‑end lives in the **frontend‑webapp** container (one of the 5 containers). It belongs mainly to the **presentation** layer (UI components) but the SASS compilation is part of the **infrastructure** layer that supports the build process. The build configuration (`angular.json`) is the entry point; it calls the Angular Builder, which in turn invokes the SASS compiler. Neighbouring components are the UI component library (presentation layer) that consumes the generated CSS, and the CI/CD pipeline (application layer) that triggers the build. Changing the builder affects only this container and its build pipeline – no other containers (e.g., backend services) are impacted.

## Anticipated Questions

**Q: Do I need to modify every `angular.json` project entry or only the main application?**
A: Only the projects that currently use the legacy SASS builder need to be updated. Typically this is the main application project; library projects that do not compile SASS can be left unchanged.

**Q: Will existing SASS files need to be rewritten?**
A: No. The new builder supports the same SASS syntax; only the import mechanism changes internally. However, verify that any custom import paths still resolve after the migration.

**Q: How does this affect the CI/CD pipeline?**
A: The pipeline step that runs `ng build` will automatically use the new builder once `angular.json` is updated. Ensure the CI environment has the same Angular CLI version (19) installed.

**Q: Are there known incompatibilities with third‑party SASS libraries?**
A: At the moment no specific incompatibilities are documented, but run the full test suite (including visual regression tests) after migration to catch any edge cases.

**Q: What testing is required after the migration?**
A: Run the full unit test suite (Karma) and the end‑to‑end tests (Playwright). Additionally, perform visual regression checks on key UI screens to confirm styling is unchanged.


## Linked Tasks

- UVZ-09-ADR-003 (Frontend Build Strategy SASS Import Deprecation)
- UVZUSLNVV-5890 (Angular 19 upgrade ticket)
- Potential follow‑up task: Update CI pipeline to use Angular CLI 19