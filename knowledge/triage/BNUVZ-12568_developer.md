# Developer Context: BNUVZ-12568

## Big Picture

This repository hosts the web‑frontend of a B2B portal used by internal employees and external partners to submit and track requests. The UI is built with Angular (currently v18) and styled with SASS. The upcoming Angular 19 release removes the legacy SASS compiler and requires projects to use the Angular Builder (`@angular-devkit/build-angular:application`). The task is to migrate the build configuration so that the UI can be compiled with Angular 19 without losing styling or breaking the CI pipeline. The migration is needed now because the Angular 19 upgrade is scheduled for the next release cycle; delaying it would cause the build to fail or produce visual regressions, blocking the release.

## Scope Boundary

IN: Update `angular.json` (or workspace configuration) to use `@angular-devkit/build-angular:application` for SASS, adjust any custom Webpack SASS loader settings, verify that all SASS import statements comply with the deprecation ADR, run the full test suite (Karma unit tests and Playwright e2e tests) to catch regressions. OUT: Any other Angular 19 migration steps (e.g., TypeScript upgrade, RxJS changes), backend code, non‑SASS related UI refactorings, infrastructure changes unrelated to the build process.

## Affected Components

- Angular Build Configuration (presentation)
- SASS Asset Pipeline (presentation)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 drops support for the legacy SASS compiler; the project must switch to the Angular Builder (`@angular-devkit/build-angular:application`). This forces a change in the build configuration and may require removal of custom Webpack SASS loader settings.
_Sources: tech_versions.json: Angular 18-lts, tech_versions.json: Angular CLI 18-lts, ADR: UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation_

**[CAUTION] Dependency Risk**
The version of `@angular-devkit/build-angular` must match the other Angular packages (animations, core, common, etc.) that will be upgraded to v19. A version mismatch will cause compilation errors.
_Sources: dependencies.json: @angular/core v18-lts, dependencies.json: @angular/compiler v18-lts_

**[INFO] Testing Constraint**
After the SASS migration the full test suite (Karma unit tests and Playwright e2e tests) must be executed to ensure no visual regressions or build failures were introduced.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_

**[CAUTION] Pattern Constraint**
The ADR specifies that certain SASS import syntaxes are deprecated. All SASS files need to be reviewed (or linted) to conform to the new import style before the builder can process them successfully.
_Sources: ADR: UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation_


## Architecture Walkthrough

The frontend lives in the **Presentation** container (one of the 5 system containers). Within that container the **Angular Build Configuration** component (layer: presentation) orchestrates the compilation of TypeScript, HTML templates, and SASS assets. It interacts with the **CI/CD pipeline** (infrastructure layer) to produce the final bundle that is served by the **Web Server** component (infrastructure). The SASS compiler is a sub‑component of the build configuration and currently depends on a custom Webpack loader. The migration will replace that sub‑component with the Angular Builder, which directly integrates with the Angular CLI. Neighboring components include the **Component Library** (presentation) that provides UI components styled with SASS, and the **Test Harness** (presentation) that runs Karma and Playwright tests against the built bundle.

## Anticipated Questions

**Q: Do I need to upgrade Angular to v19 before changing the SASS compiler?**
A: Yes. The new builder is only available with Angular 19 and the matching version of `@angular-devkit/build-angular`. The migration should be done as part of the overall Angular 19 upgrade, but you can update the build configuration first and then bump the other Angular packages.

**Q: Is there any custom Webpack configuration that must be removed or adapted?**
A: If the project currently adds a custom SASS loader in `webpack.config.js` (or via `angular.json`'s `customWebpackConfig`), that configuration must be removed because the Angular Builder provides its own SASS handling. Verify the repository for any `sass-loader` entries and delete or migrate them.

**Q: Will existing SASS files break because of the import deprecation?**
A: Potentially. The ADR lists the deprecated import patterns. Run the project's linting rules (or a quick grep) for the old syntax and update the imports to the new style before the build runs, otherwise the builder will emit errors.

**Q: How do I know the migration succeeded?**
A: A successful migration will result in `ng build` completing without SASS‑related errors and all unit (Karma) and e2e (Playwright) tests passing. Additionally, visual inspection of a few key pages in a local dev server is recommended to catch subtle styling regressions.

**Q: Do CI pipelines need changes?**
A: Only if they reference the old Webpack configuration or specific SASS compiler flags. After the migration, the CI should invoke the standard `ng build` command; verify that the pipeline scripts do not pass obsolete flags.


## Linked Tasks

- UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation
- UVZUSLNVV-5890 (Angular 19 core upgrade)
- Potential follow‑up: Update TypeScript to the version required by Angular 19