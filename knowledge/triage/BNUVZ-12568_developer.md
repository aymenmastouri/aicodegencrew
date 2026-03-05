# Developer Context: BNUVZ-12568

## Big Picture

This repository contains the single‑page Angular front‑end that is used by internal users and external customers to interact with the core business services. The UI is built with Angular components (presentation layer) that are styled with SASS. The build pipeline (infrastructure layer) is orchestrated by Angular CLI, Webpack and Karma. The task is to migrate the SASS compilation step to the new Angular Builder that will be required for the upcoming Angular 19 upgrade. Doing the migration now ensures the application can be upgraded without breaking the build, keeps the styling pipeline functional, and avoids future technical debt.

## Scope Boundary

IN: Update `angular.json` to use `@angular-devkit/build-angular:application` for SASS, adjust any custom Webpack or builder configuration that references the old sass‑loader, run the SASS import deprecation ADR checks, and execute the full UI test suite to verify no regressions. OUT: The broader Angular 19 framework upgrade (core, router, RxJS), backend services, data‑access layer, and any non‑UI components are out of scope for this ticket.

## Affected Components

- Build Configuration (infrastructure layer)
- Presentation components that import SASS (presentation layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 drops support for the legacy SASS compiler; the new builder (`@angular-devkit/build-angular:application`) must be used or the build will fail. This is a hard blocker for the upgrade.
_Sources: tech_versions.json: Angular 18-lts, ADR: UVZ-09-ADR-003 – Frontend Build Strategy SASS Import Deprecation_

**[CAUTION] Dependency Risk**
The new builder brings its own version of `sass` and may conflict with the existing Webpack 5 configuration and any custom `sass-loader` settings. Compatibility must be verified before merging.
_Sources: tech_versions.json: Webpack 5.80.0, dependencies.json: @angular/compiler v18-lts_

**[INFO] Testing Constraint**
Because the SASS compilation path changes, all UI unit tests (Karma) and end‑to‑end tests (Playwright) need to be run to catch regressions in styling or build failures.
_Sources: analysis input: Testing constraint – additional testing may be necessary_


## Architecture Walkthrough

YOU ARE HERE: The front‑end lives in the **frontend container**. Within that container the **infrastructure layer** holds the build configuration (Angular CLI, Webpack, builder). The **presentation layer** contains the Angular components that import SASS files. The SASS compiler sits between the presentation layer (style files) and the infrastructure layer (build pipeline). Changing the builder will affect the `angular.json` file, any custom Webpack config, and potentially the CI/CD pipeline that invokes the Angular build. Downstream, the compiled CSS is bundled and served to the browser; upstream, no other containers are impacted.

## Anticipated Questions

**Q: Do I need to upgrade Angular core to 19 as part of this migration?**
A: No. The migration can be performed on the current Angular 18 codebase by switching the builder. However, the change is a prerequisite for the later Angular 19 upgrade.

**Q: Will existing SASS files need to be rewritten?**
A: Only if they use the deprecated `@import` syntax that the ADR flags. The migration task should include running the ADR checks and updating any flagged imports.

**Q: Is there any impact on the CI pipeline?**
A: The CI pipeline currently runs `ng build` with the old builder. After migration it must invoke the same command but the builder will be `@angular-devkit/build-angular:application`. Verify that the pipeline’s Docker image contains the required version of the Angular CLI.

**Q: What tests should I run after the change?**
A: Run the full unit test suite (Karma) and the end‑to‑end suite (Playwright). Pay special attention to visual regression tests if they exist, because CSS output may differ.

**Q: Are there any known incompatibilities with other libraries (e.g., RxJS, CDK)?**
A: The SASS compiler change is isolated to the build step and does not affect runtime libraries such as RxJS or Angular CDK. The main compatibility concern is with the Webpack configuration and any custom `sass-loader` usage.


## Linked Tasks

- UVZUSLNVV-5890 (Angular 19 core upgrade – future ticket)
- UVZ-09-ADR-003 (Frontend Build Strategy SASS Import Deprecation) – reference for import changes