# Developer Context: BNUVZ-12568

## Big Picture

This repository contains the single‑page Angular front‑end that is used by internal users and external customers to interact with the core business services. The UI is built with Angular 18‑LTS, TypeScript 4.9.5 and styled with SASS. The upcoming Angular 19 upgrade requires a change in the build pipeline: the old SASS compiler (node‑sass via Webpack) is deprecated and must be replaced by the SASS compiler that ships with the Angular Builder (`@angular-devkit/build-angular:application`). The task ensures the UI can continue to be built, tested and deployed after the framework upgrade, preventing a hard stop in the release pipeline.

## Scope Boundary

IN: All build‑time artefacts related to SASS compilation – `angular.json` configuration, any custom Webpack builder settings, SASS import statements that use the deprecated syntax, CI/CD scripts that invoke the Angular build, and associated unit/e2e tests that may be affected. OUT: Runtime application code (components, services, business logic), backend services, unrelated UI components that do not touch SASS, and any non‑Angular build tools (e.g., Gradle scripts for the backend).

## Affected Components

- Angular Build Configuration (infrastructure layer)
- SASS Stylesheets (presentation layer)
- CI/CD Build Pipeline (infrastructure layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 removes the legacy SASS compiler; the project must switch to the builder‑provided compiler (`@angular-devkit/build-angular:application`). This is a hard requirement for the framework upgrade.
_Sources: tech_versions.json: Angular 18-lts, tech_versions.json: Angular CLI 18-lts, ADR: UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation_

**[CAUTION] Dependency Risk**
The new builder uses Dart Sass (v1.x) which may interpret certain SASS import patterns differently. Existing SASS files need to be verified for compatibility to avoid styling regressions.
_Sources: dependencies.json: @angular/compiler v18-lts, dependencies.json: @angular/core v18-lts_

**[INFO] Testing Constraint**
Because the compilation pipeline changes, unit tests (Karma) and end‑to‑end tests (Playwright) that rely on the build output must be re‑run to catch regressions in generated CSS.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_

**[BLOCKING] Workflow Constraint**
CI pipelines currently invoke `ng build` with the old builder configuration. Those scripts must be updated to reference the new builder target, otherwise CI will fail after the Angular upgrade.
_Sources: tech_versions.json: Gradle 8.2.1 (used for orchestrating CI), architecture_overview.json: infrastructure layer contains build pipeline components_

**[CAUTION] Pattern Constraint**
The ADR (UVZ‑09‑ADR‑003) deprecates the old `@import` syntax in SASS. Any remaining deprecated imports must be replaced with the new `@use`/`@forward` syntax before or during the migration.
_Sources: ADR: https://wiki.bnotk.de/spaces/UVZUSLNAS/pages/386958007/UVZ-09-ADR-003+-+Frontend+Build+Strategy+SASS+Import+Deprecation_


## Architecture Walkthrough

The front‑end lives in the **frontend container** (one of the five system containers). Within that container it belongs to the **presentation layer** (287 components) and the **infrastructure layer** for build‑time concerns (e.g., Angular CLI, Webpack). The migration touches the **Angular Build Configuration** component (infrastructure) which is referenced by the **CI/CD pipeline** component (also infrastructure). The **SASS Stylesheets** component (presentation) consumes the output of the build configuration. Data flows: source SASS → Angular Builder (new compiler) → compiled CSS → UI components. The developer will edit `angular.json` (builder target), possibly adjust custom Webpack config, and verify that the SASS files still compile and render correctly. No runtime services or domain logic are involved.

## Anticipated Questions

**Q: Do I need to upgrade Angular CLI and other Angular packages to version 19 before changing the builder?**
A: Yes. The new builder is only available in `@angular-devkit/build-angular` version 19, which is bundled with Angular CLI 19. The migration should be performed as part of the overall Angular 19 upgrade.

**Q: Will existing SASS files break because of the new compiler?**
A: Potentially. The new Dart Sass enforces stricter import rules and deprecates the old `@import` syntax. Verify all SASS files against the ADR and run the full test suite after migration to catch any styling regressions.

**Q: Are there any CI/CD changes required?**
A: Yes. CI scripts that invoke `ng build` must be updated to use the new builder target (`@angular-devkit/build-angular:application`). Ensure the pipeline pulls the updated Angular CLI version.

**Q: Do unit tests (Karma) or e2e tests (Playwright) need modifications?**
A: No code changes are expected, but the test suites must be re‑executed after the migration to confirm that the compiled CSS is still correct and that no test failures appear.

**Q: Is there a fallback if the migration causes issues?**
A: Temporarily you could pin the project to Angular 18 until the issues are resolved, but this defeats the purpose of the Angular 19 upgrade and will block future releases.


## Linked Tasks

- UVZ-09-ADR-003 (Frontend Build Strategy SASS Import Deprecation)
- Angular 19 Upgrade Epic (e.g., UVZ-5891)
- CI Pipeline Update Task (e.g., UVZ-5892)