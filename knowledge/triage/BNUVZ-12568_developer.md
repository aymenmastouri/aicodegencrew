# Developer Context: BNUVZ-12568

## Big Picture

This project is the web‑frontend of an internal portal used by the company’s employees. It lives in the *presentation* layer of the overall system and is built with Angular. The task is to migrate the SASS compilation step to the new Angular Builder that comes with Angular 19. The migration is needed now because the upcoming Angular 19 release deprecates the old SASS compiler; if we do not migrate, the CI build will break and the next production release cannot be shipped. The change does not affect runtime behaviour – it only touches the build pipeline and the style assets – but a broken build would halt delivery and could introduce visual regressions if not tested.

## Scope Boundary

IN: Angular project’s build configuration (angular.json, package.json), all .scss/.sass files, CI/CD build step that invokes @angular-devkit/build-angular, related unit (Karma) and e2e (Playwright) test suites. OUT: Backend services, database schema, non‑Angular micro‑frontends, runtime business logic, security exception handling, and any unrelated containers.

## Affected Components

- FrontendAngularApp (presentation)
- AngularBuildConfig (infrastructure/presentation)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 requires the new builder @angular-devkit/build-angular:application which ships a different SASS compiler. The current codebase is on Angular 18‑lts with the legacy builder, so the build will fail unless the configuration is updated.
_Sources: tech_versions.json: Angular 18‑lts, tech_versions.json: Angular CLI 18‑lts, tech_versions.json: Webpack 5.80.0_

**[CAUTION] Dependency Risk**
Third‑party libraries or custom SCSS that still use the deprecated @import syntax may not compile with the new Dart Sass compiler. These files need to be identified and migrated to the @use/@forward syntax to avoid compilation errors.
_Sources: ADR: UVZ‑09‑ADR‑003 Frontend Build Strategy SASS Import Deprecation_

**[INFO] Testing Constraint**
After the migration the existing unit tests (Karma) and end‑to‑end tests (Playwright) must be run to catch any visual regressions caused by style changes or build‑pipeline differences.
_Sources: analysis_inputs: Karma 6.4.3, analysis_inputs: Playwright 1.44.1_

**[CAUTION] Technology Constraint**
Angular 19 typically requires TypeScript 5.x. The project currently uses TypeScript 4.9.5, so a TS upgrade may be required as part of the Angular upgrade.
_Sources: tech_versions.json: TypeScript 4.9.5_


## Architecture Walkthrough

The frontend lives in the **presentation** container (one of the five top‑level containers). Within that container the Angular application sits in the **presentation layer** and is built by the **infrastructure layer** component that wraps the Angular CLI. The SASS compiler is invoked by the build step defined in *angular.json* via the builder @angular-devkit/build-angular:application. Neighboring components are the UI component library (Angular Material, CDK), the style asset folder (src/styles), and the CI/CD pipeline that triggers the build. Changing the builder will affect only this build pipeline; downstream components (runtime UI components) remain unchanged but must be re‑compiled with the new compiler.

## Anticipated Questions

**Q: Do we need to upgrade TypeScript as part of this migration?**
A: Angular 19 usually requires TypeScript 5.x. The project currently uses 4.9.5, so you should verify the required TS version in the Angular 19 release notes and upgrade if necessary before updating the builder.

**Q: Will existing SCSS files need to be rewritten?**
A: If any SCSS files still use the deprecated `@import` syntax, they must be converted to the newer `@use`/`@forward` syntax because the new Dart Sass compiler does not support the old syntax. Run a search for `@import` in the style folder to identify candidates.

**Q: How do we ensure we don’t introduce visual regressions?**
A: After the migration run the full suite of unit tests (Karma) and end‑to‑end tests (Playwright). Additionally, consider a visual regression testing tool if one is already part of the CI pipeline.

**Q: Is the CI/CD pipeline affected?**
A: Yes. The pipeline step that calls `ng build` will now use the new builder. Update the `angular.json` configuration in the repository and ensure the CI script references the correct builder name.

**Q: Will this change affect runtime performance or functionality?**
A: No. The change is limited to the build process. As long as the styles compile successfully, the runtime behaviour of the application remains unchanged.


## Linked Tasks

- UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation