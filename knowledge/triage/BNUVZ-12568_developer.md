# Developer Context: BNUVZ-12568

## Big Picture

This project is a large Angular single‑page application that serves internal users (e.g., employees of the client organization). The front‑end lives in the *frontend* container, mainly in the presentation layer, and is built with Angular 18, TypeScript 4.9.5, Webpack 5, Karma unit tests and Playwright e2e tests. The task is to prepare the codebase for the upcoming Angular 19 release by switching the build system to the new Angular Builder that ships a modern SASS compiler. Doing this now prevents a future break‑age of the CI build and eliminates the need to rewrite SASS imports later, reducing regression risk.

## Scope Boundary

IN: Update angular.json (or workspace configuration) to use @angular-devkit/build-angular:application, adjust any custom SASS loader configuration, run the full test suite (Karma + Playwright) to verify UI rendering, and address any SASS import deprecations as described in the ADR. OUT: Changes to backend services, unrelated feature code, migration of other libraries (e.g., RxJS, Angular CDK), or a full TypeScript version upgrade.

## Affected Components

- Angular build configuration (infrastructure / presentation)
- SASS stylesheet assets (presentation)
- CI build pipeline scripts (infrastructure)

## Context Boundaries

**[CAUTION] Technology Constraint**
Angular 19 replaces the legacy node‑sass compiler with the built‑in Dart Sass compiler. All SASS files must follow the new import rules (no tilde‑style imports, no deprecated syntax) as mandated by the ADR. Failure to adapt will cause compilation errors after the migration.
_Sources: ADR: UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation, tech_versions.json: Angular 18-lts_

**[INFO] Dependency Risk**
The new builder bundles its own SASS compiler, which may conflict with the existing custom Webpack 5 configuration that currently handles SASS loading. The migration must verify that no custom webpack rules are left orphaned, otherwise the build could silently skip styles or produce broken CSS.
_Sources: tech_versions.json: Webpack 5.80.0, tech_versions.json: Angular CLI 18-lts_

**[INFO] Testing Constraint**
Because the SASS compilation path changes, visual regressions are possible. All unit tests (Karma) and end‑to‑end tests (Playwright) must be executed after the migration to catch styling breakages.
_Sources: Issue description: "additional testing may be necessary to minimize the risk of potential regressions", tech_versions.json: Playwright 1.44.1, tech_versions.json: Karma 6.4.3_


## Architecture Walkthrough

WALKTHROUGH: The front‑end lives in the **frontend** container (one of the 5 system containers). Within that container the code is organized into the **presentation layer** (≈287 components). The SASS files are assets attached to many UI components. Build configuration (angular.json, webpack config) resides in the **infrastructure** slice of the presentation container. The migration touches the build pipeline (infrastructure) but the ripple effect is on every component that imports SASS, i.e., the majority of UI components. Neighboring pieces are: (1) Angular component classes (presentation), (2) the CI/CD pipeline that runs `ng build` (infrastructure), (3) test suites that load compiled CSS (testing). The developer should start at the angular.json entry for the builder, then trace any custom webpack rules that reference SASS loaders, and finally run the full test matrix.

## Anticipated Questions

**Q: Do we need to modify any custom webpack configuration for SASS?**
A: Yes. The new @angular-devkit/build-angular:application builder includes its own SASS handling. Any custom webpack rule that loads SASS must be reviewed and either removed or adapted to the new builder's configuration.

**Q: Will the existing unit and e2e tests still run after the migration?**
A: They should run, but because the CSS output may change, you must execute the full Karma and Playwright suites to verify that no visual regressions or test failures appear.

**Q: Is a TypeScript version bump required for Angular 19?**
A: Angular 19 typically requires TypeScript 5.x, but the current task only addresses the SASS compiler migration. The TypeScript upgrade can be scheduled separately; however, be aware that the build may warn about incompatibility if the TypeScript version is not updated later.

**Q: What specific SASS import changes are needed?**
A: Refer to the ADR (UVZ-09-ADR-003). It outlines that tilde‑based imports (`@import '~@my-lib/style'`) and the old `::ng-deep` syntax are deprecated. Update imports to use relative paths or the new `@use`/`@forward` syntax as described.

**Q: What is the fallback if the migration breaks the build?**
A: You can revert the angular.json change and re‑enable the previous builder. However, this is only a temporary measure; the next Angular version will not support the old compiler, so the migration must eventually succeed.


## Linked Tasks

- UVZUSLNVV-5890 (Angular 19 upgrade – overall version bump)
- UVZ-09-ADR-003 (Frontend Build Strategy SASS Import Deprecation)