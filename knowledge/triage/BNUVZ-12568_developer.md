# Developer Context: BNUVZ-12568

## Big Picture

This repository powers the web front‑end of the BNOTK product suite. End‑users (internal staff and external customers) interact with the UI built with Angular. The UI is compiled, bundled and served by a CI/CD pipeline that currently uses Webpack and the legacy SASS compiler. The task is to switch the SASS compilation to the new Angular‑Builder that comes with Angular 19. This migration is required now because Angular 19 has deprecated the old SASS import strategy (see ADR UVZ‑09‑ADR‑003). Without the migration the build will break, future Angular upgrades will be impossible, and UI styling could regress.

## Scope Boundary

IN: Update `angular.json` (or workspace config) to use `@angular-devkit/build-angular:application` for the SASS compiler, adjust SASS files according to the ADR (replace deprecated `@import` with `@use`/`@forward` where needed), run the full unit (Karma) and e2e (Playwright) test suites, and verify CI build success. OUT: Any changes to backend services, domain logic, data‑access components, or unrelated feature work. Refactoring of component code that does not touch styling is out of scope.

## Affected Components

- Frontend Build Pipeline (presentation layer)
- Angular Application Configuration (presentation layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 drops support for the legacy SASS compiler; the new Angular‑Builder must be used or the build will fail.
_Sources: tech_versions.json: Angular 18‑lts, tech_versions.json: Angular CLI 18‑lts_

**[CAUTION] Dependency Risk**
The ADR deprecates `@import` syntax. Existing SASS files that still use `@import` will cause compilation errors after migration.
_Sources: ADR link: UVZ‑09‑ADR‑003 Frontend Build Strategy SASS Import Deprecation_

**[INFO] Testing Constraint**
After changing the build system, all unit tests (Karma) and e2e tests (Playwright) must be re‑executed to catch regressions in styling or build output.
_Sources: tech_versions.json: Playwright 1.44.1, tech_versions.json: Karma 6.4.3_

**[CAUTION] Workflow Constraint**
CI pipelines that invoke `ng build` with the old builder need to be updated to the new target; otherwise the pipeline will error out.
_Sources: tech_versions.json: Gradle 8.2.1 (used for CI orchestration)_

**[INFO] Infrastructure Constraint**
The build server runs Java 17 and Gradle 8.2.1, which are compatible with Angular 19, but the Node version used by the pipeline must support the newer Sass compiler (Dart Sass).
_Sources: tech_versions.json: Java 17, tech_versions.json: Gradle 8.2.1_


## Architecture Walkthrough

WALKTHROUGH: The front‑end lives in the **frontend container** (one of the 5 top‑level containers). Within that container it belongs to the **presentation layer** (287 components). The build configuration (`angular.json`, `package.json`) is a cross‑cutting infrastructure component that sits just above the presentation components. Neighbouring pieces are:
- The **UI component library** (also in the presentation layer) that provides reusable Angular components and SASS styles.
- The **CI/CD pipeline** (infrastructure) that invokes `ng build` and runs Karma/Playwright tests.
- The **Webpack builder** (currently) which will be replaced by the **Angular‑Builder**.
Developers should start at the `angular.json` file, switch the builder for the application target to `@angular-devkit/build-angular:application`, then walk through the SASS source tree to ensure all imports comply with the new `@use`/`@forward` rules defined in the ADR. After the change, the build output flows to the same distribution folder and is consumed by the same deployment scripts, so downstream components remain unchanged.

## Anticipated Questions

**Q: Do I need to update any SASS files manually?**
A: Yes. The ADR specifies that `@import` statements are deprecated. Any SASS file still using `@import` must be rewritten to use `@use` or `@forward`. The migration may be incremental, but the build will fail if deprecated imports remain.

**Q: Will this affect third‑party component libraries that ship their own SASS?**
A: Potentially. If a library still uses `@import`, the new builder will raise an error. Verify the library’s version; most Angular Material packages have already migrated. If a library is outdated, either upgrade it or apply a temporary patch.

**Q: Do I need to change the Node or TypeScript version?**
A: Angular 19 requires at least TypeScript 5.0, but the current project is on TypeScript 4.9.5. The migration task should include checking the Angular‑CLI compatibility matrix; if the CLI version for Angular 19 is not yet in the repo, a TypeScript upgrade will be required as part of the broader Angular upgrade, not just the SASS migration.

**Q: Will the CI pipeline need changes?**
A: The pipeline currently calls `ng build` with the legacy builder. After migration, the same command works because the target is switched, but any scripts that reference the old builder name or custom Webpack configs must be reviewed.

**Q: How do we know the migration didn’t break the UI?**
A: Run the full suite of Karma unit tests and Playwright e2e tests after the change. Pay special attention to visual regression tests (if any) and components that rely on SASS variables or mixins.


## Linked Tasks

- UVZUSLNVV-5890 (Angular 19 SASS compiler migration)
- UVZ‑09‑ADR‑003 (Frontend Build Strategy SASS Import Deprecation)