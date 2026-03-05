# Developer Context: BNUVZ-12568

## Big Picture

The project is a large enterprise‑grade Angular single‑page application that serves internal and external users via a web UI. It lives in the *frontend* container and most of its code resides in the presentation layer (UI components, style sheets, routing). The task is to migrate the SASS compilation step to the new Angular Builder that will be required for the upcoming Angular 19 upgrade. This migration prevents a hard break in the build pipeline, ensures that styling continues to compile, and keeps the roadmap for future Angular upgrades on track. If the migration is not performed, the next major Angular release will break the build and could cause UI regressions for users.

## Scope Boundary

IN: Update angular.json (or workspace configuration) to use @angular-devkit/build-angular:application as the builder for SASS, adjust any SASS import statements that are deprecated, run the full unit (Karma) and e2e (Playwright) test suites, and verify CI build success. OUT: Upgrading all Angular core packages to version 19, refactoring application code unrelated to styling, changing the underlying bundler (e.g., moving from Webpack to Vite), or modifying backend services.

## Affected Components

- Angular build configuration (presentation layer)
- SASS style sheets used by UI components (presentation layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 deprecates the legacy SASS compiler; the new builder @angular-devkit/build-angular:application must be used or the build will fail after the framework upgrade.
_Sources: ADR: UVZ-09-ADR-003+-+Frontend+Build+Strategy+SASS+Import+Deprecation, tech_versions.json: Angular 18‑lts_

**[CAUTION] Dependency Risk**
Existing SASS files may contain @import statements that are no longer supported by the new compiler; they will need to be rewritten to @use/@forward or adjusted, otherwise compilation errors will appear.
_Sources: ADR: UVZ-09-ADR-003+-+Frontend+Build+Strategy+SASS+Import+Deprecation_

**[INFO] Testing Constraint**
Because the compiler change can affect generated CSS, the full test suite (Karma unit tests and Playwright e2e tests) must be executed to catch visual or functional regressions.
_Sources: analysis_inputs: Playwright 1.44.1, analysis_inputs: Karma 6.4.3_


## Architecture Walkthrough

YOU ARE HERE: **frontend container** → **presentation layer** → **Angular application**. The Angular build configuration (angular.json) lives in the root of the frontend container and is consumed by the Angular CLI (currently version 18‑lts). The SASS compiler is a build‑time dependency; it does not affect runtime components but feeds CSS into UI components (buttons, forms, etc.). Neighboring components include the UI component library (Angular Material via @angular/cdk) and the style‑sheet assets that are imported by each component. Changing the builder will only touch the build pipeline; no backend or domain logic is impacted.

## Anticipated Questions

**Q: Do we need to upgrade all Angular packages to version 19 now, or only the builder?**
A: Only the builder configuration and the SASS compiler need to be changed for this task. Full Angular 19 package upgrades are out of scope and can be done in a later phase.

**Q: Will existing SASS files compile without changes?**
A: Most will, but any file that uses the deprecated `@import` syntax will need to be updated to the newer `@use`/`@forward` syntax, as required by the new compiler.

**Q: How will this affect the CI pipeline that currently uses Gradle 8.2.1?**
A: The CI pipeline invokes the Angular CLI via npm scripts; only the builder flag in angular.json changes. No Gradle configuration changes are required.

**Q: Are there known incompatibilities between the new builder and Webpack 5.80.0?**
A: The new Angular Builder still uses Webpack under the hood. The current Webpack version is compatible, but after migration you should run the build locally to confirm there are no warnings.

**Q: Do we need to adjust unit or e2e test configurations?**
A: No test configuration changes are required, but the entire test suite must be run after migration to ensure no styling regressions have been introduced.


## Linked Tasks

- UVZUSLNVV-5890 (Migration des SASS Compiler)
- UVZ-09-ADR-003 (Frontend Build Strategy SASS Import Deprecation)
- Potential future task: Angular 19 core framework upgrade