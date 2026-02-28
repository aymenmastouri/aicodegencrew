# Developer Context: BNUVZ-12568

## Big Picture

Our product is a large, Angular‑based web application that serves internal users (e.g., employees) and possibly external customers. It lives in the *presentation* layer of a five‑container architecture and is built and delivered by a dedicated front‑end build container. The upcoming Angular 19 upgrade is part of the platform’s roadmap to stay on supported framework versions. This ticket addresses the required change of the SASS compilation step: Angular 19 deprecates the old SASS import mechanism, so the build must switch to the new Angular Builder. Performing the migration now prevents a broken build pipeline and ensures that future feature work can continue without interruption.

## Scope Boundary

IN: Update the Angular build configuration (angular.json) to use @angular-devkit/build-angular:application for SASS, adjust any custom SASS import statements, align the CI/CD build scripts with the new builder, and run the full front‑end test suite to catch regressions. OUT: No changes to backend Java services, domain logic, or unrelated third‑party libraries that are not part of the front‑end build process.

## Affected Components

- frontend‑build (infrastructure layer)
- presentation layer components that import SCSS
- CI/CD pipeline scripts (workflow layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 no longer supports the legacy SASS compiler; the new @angular-devkit/build-angular:application builder must be used or the project will fail to compile.
_Sources: tech_versions.json: Angular 18‑lts (current version), tech_versions.json: Angular CLI 18‑lts (current version)_

**[CAUTION] Dependency Risk**
The existing Webpack 5.80.0 configuration may conflict with the Angular Builder’s internal handling of SASS; any custom webpack rules for SCSS need verification.
_Sources: tech_versions.json: Webpack 5.80.0_

**[CAUTION] Testing Constraint**
Because the SASS compilation path changes, visual regression tests and unit tests that import SCSS must be re‑run to ensure no styling regressions are introduced.
_Sources: analyzed_architecture.json: Tests count 926_

**[BLOCKING] Workflow Constraint**
CI pipelines that invoke ng build with the old builder need to be updated; otherwise builds will fail in the automation environment.
_Sources: tech_versions.json: Gradle 8.2.1 (used for overall build orchestration)_

**[INFO] Infrastructure Constraint**
The build container must have a Node version compatible with Angular 19 and the new builder; verify that the container image is updated accordingly.
_Sources: tech_versions.json: TypeScript 4.9.5 (used by Angular CLI)_


## Architecture Walkthrough

The front‑end lives in the *presentation* layer (≈287 components) inside the **frontend‑build** container (infrastructure layer). The SASS compiler is part of the build pipeline that takes SCSS assets from presentation components and produces CSS bundles. It interacts with:
- Angular CLI (currently version 18‑lts) → will be upgraded to 19.
- Webpack configuration (currently used for custom asset handling).
- CI/CD scripts that invoke the builder.
Neighbouring components include the component library (presentation) that imports SCSS, the style assets repository, and the build orchestrator (Gradle). Updating the builder changes the *integration point* between the presentation layer and the infrastructure build container, but does not affect runtime services in the domain or data‑access layers.

## Anticipated Questions

**Q: Do I need to change any TypeScript or Angular code besides the build config?**
A: No functional TypeScript changes are required for the migration itself. Only the angular.json builder entry and any custom webpack SASS rules may need adjustment.

**Q: Will existing unit and e2e tests still run after the migration?**
A: They should run, but because the CSS output may differ, visual regression tests and any tests that import SCSS should be re‑executed to confirm no regressions.

**Q: Is there a risk that the new builder breaks our custom SASS import paths?**
A: Yes. The new builder enforces a different import resolution strategy. Verify that all @import statements resolve correctly after the change.

**Q: Do we need to upgrade other build tools (Webpack, Karma) as part of this?**
A: Only if custom webpack configuration conflicts with the Angular Builder. The existing versions (Webpack 5.80.0, Karma 6.4.3) are compatible with Angular 19, but review any custom loader settings.

**Q: What happens if we postpone this migration?**
A: The application will fail to build once Angular 19 is adopted, blocking any further releases and potentially causing downtime for users.


## Linked Tasks

- UVZUSLNVV-5890 (Angular 19 upgrade – overall framework bump)
- UVZ-09-ADR-003 (Frontend Build Strategy SASS Import Deprecation) – reference architecture decision