# Developer Context: BNUVZ-12568

## Big Picture

The project is a large Angular single‑page application that delivers the user interface for internal and external users (e.g., a customer portal). It lives in the **presentation** layer of a five‑container architecture and is built with Angular 18‑lts, Webpack, Karma and Playwright. The upcoming Angular 19 release requires a change in the build pipeline: the legacy SASS compiler is removed and the new Angular‑Builder SASS compiler must be used. This task guarantees that the UI can still be compiled and rendered after the framework upgrade, and that no styling regressions reach production.

## Scope Boundary

IN: Update the Angular build configuration (angular.json) to use @angular-devkit/build-angular:application as the SASS compiler, adjust any SASS import statements that rely on the deprecated syntax, run the full suite of unit, integration and e2e tests, and verify CI build success. OUT: Any other Angular 19 migration steps (e.g., RxJS updates, component API changes), backend services, database schema changes, or unrelated feature work.

## Affected Components

- Angular Build Configuration (presentation)
- SASS Stylesheets / SCSS files (presentation)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 drops support for the old SASS compiler; the project must switch to the Angular‑Builder implementation to keep the build pipeline functional.
_Sources: tech_versions.json: Angular 18‑lts, ADR: UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation_

**[CAUTION] Dependency Risk**
The new SASS compiler may interpret @use / @import statements differently; existing third‑party SCSS (e.g., Angular Material, CDK) must be compatible with the new compiler version.
_Sources: dependencies.json: @angular/material v18‑lts, dependencies.json: @angular/cdk v18‑lts_

**[CAUTION] Testing Constraint**
Because the compiler change can affect generated CSS, the full test suite (Karma unit tests, Playwright e2e tests) must be executed to catch visual regressions.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_

**[INFO] Integration Boundary**
CI pipelines that invoke the Angular CLI need to be updated to the new builder target; otherwise builds will fail in the automation environment.
_Sources: tech_versions.json: Gradle 8.2.1, tech_versions.json: Angular CLI 18‑lts_


## Architecture Walkthrough

The Angular SPA lives in the **frontend container** (one of the five system containers). Within that container it belongs to the **presentation layer** (≈287 components). The SASS compiler is part of the **build sub‑layer** that interacts with the CI/CD pipeline. Neighbouring components include the Webpack bundler, Karma unit‑test runner, and Playwright e2e runner. Changing the compiler only touches the build configuration and the SCSS assets; runtime components (components, services, routes) remain unchanged. Think of the map as: Frontend Container → Presentation Layer → Build Configuration (angular.json) ↔ SASS Compiler ↔ SCSS Assets ↔ Webpack → Bundled CSS → Browser.

## Anticipated Questions

**Q: Do any SCSS files need to be rewritten because of the new compiler?**
A: The new Angular‑Builder compiler follows the modern Sass module system. Existing @import statements that rely on the deprecated import resolution may need to be changed to @use/@forward. Verify the ADR for the exact deprecation list and run the test suite to spot failures.

**Q: Will the CI/CD pipeline break after the change?**
A: CI jobs that call `ng build` reference the new builder target (`@angular-devkit/build-angular:application`). Pipeline scripts therefore need to point to that target, and a full build in the CI environment should be performed to confirm successful execution.

**Q: Are third‑party libraries (e.g., Angular Material) compatible with the new compiler?**
A: Material and CDK are at version 18‑lts, which already support the new Sass module system. However, confirm that no custom theming SCSS imports conflict with the new resolution rules.

**Q: Do we need to adjust Karma or Playwright configurations?**
A: No direct changes are required, but because the compiled CSS may differ, re‑run both unit and e2e tests to ensure visual and functional correctness.

**Q: Is there a fallback if the migration causes regressions?**
A: The migration can be reverted by restoring the previous angular.json configuration and SASS compiler settings from version control; having the change in a feature branch facilitates a straightforward rollback.


## Linked Tasks

- UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation
- Angular 19 Upgrade Epic (e.g., UVZUSLNVV-5900)
- UI Regression Test Suite Update (if any)