# Developer Context: BNUVZ-12568

## Big Picture

This project is a large, multi‑container web platform that delivers a UI built with Angular. End‑users are internal employees and external customers who interact with the system through a browser. The task is to migrate the SASS compilation step to the new Angular Builder that ships with Angular 19. The migration is part of the broader Angular 19 upgrade and is required now because Angular 19 will no longer support the legacy SASS import strategy. Without the migration the CI/CD pipeline will break, preventing any further UI development or deployment.

## Scope Boundary

IN: Update the Angular build configuration (angular.json) to use @angular-devkit/build-angular:application, adjust any custom SASS import statements if they rely on the deprecated syntax, run the full UI test suite, and verify CI build success. OUT: No changes to backend services, domain logic, or unrelated UI components; no changes to business‑logic code, only build‑pipeline and styling import concerns.

## Affected Components

- Frontend build configuration (presentation layer)
- Angular application module (presentation layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 deprecates the old SASS import style; the new SASS compiler provided by @angular-devkit/build-angular:application must be used or the build will fail.
_Sources: tech_versions.json: Angular 18-lts, ADR: https://wiki.bnotk.de/spaces/UVZUSLNAS/pages/386958007/UVZ-09-ADR-003+-+Frontend+Build+Strategy+SASS+Import+Deprecation_

**[CAUTION] Dependency Risk**
The version of @angular-devkit/build-angular that ships with Angular 19 may have compatibility constraints with existing SASS versions or third‑party Webpack plugins; these must be verified before committing the change.
_Sources: dependencies.json: @angular/... v18-lts, tech_versions.json: Webpack 5.80.0_

**[INFO] Testing Constraint**
Because the SASS compilation pipeline changes, visual regressions are possible. The full UI test suite (Karma + Playwright) should be executed after migration to catch any styling breakage.
_Sources: Issue description: "additional testing may be necessary to minimize the risk of potential regressions"_

**[INFO] Workflow Constraint**
The migration must be performed as part of the Angular 19 upgrade branch and integrated into the CI/CD pipeline; any pipeline steps that invoke the old builder need to be updated.
_Sources: tech_versions.json: Gradle 8.2.1, tech_versions.json: Angular CLI 18-lts_


## Architecture Walkthrough

The UI lives in the **frontend-webapp** container (presentation layer). The Angular application component is the entry point for all UI code and is built by the CI/CD pipeline (infrastructure layer). The SASS compiler is part of the build tooling that sits between the source code (presentation) and the generated bundles that are served to browsers. Neighbouring components include: • Backend API services (application layer) that provide data to the UI • Shared design system (presentation layer) that supplies SASS variables and mixins • CI/CD pipeline (infrastructure) that runs the Angular build. The migration touches only the build configuration within the frontend container; it does not affect runtime components or backend services.

## Anticipated Questions

**Q: Do any SASS files need to be rewritten because of the new compiler?**
A: In most cases the existing SASS syntax works unchanged, but import statements that used the deprecated `@import` syntax may need to be switched to the newer `@use`/`@forward` pattern. Verify the project’s SASS files for such usages.

**Q: Will the CI build break after we change the builder?**
A: Yes, the CI pipeline currently invokes the old builder. After updating angular.json you must also update any scripts or Docker images that reference the old builder so that the pipeline can complete successfully.

**Q: Are there known incompatibilities with other Angular libraries (e.g., Angular Material, CDK)?**
A: All Angular libraries must be upgraded to their Angular 19 compatible versions. Check that @angular/material, @angular/cdk, etc., have matching major versions before merging the change.

**Q: Do we need to run the full test suite after the migration?**
A: Yes. The issue explicitly calls for additional testing to catch regressions. Run the Karma unit tests and Playwright end‑to‑end tests to ensure no visual or functional breakage.

**Q: Can we postpone this migration until after the Angular 19 release?**
A: No. Angular 19 will reject the legacy SASS import mechanism, so the build will fail as soon as the framework is upgraded. The migration must be completed before the Angular 19 version is merged into the main branch.


## Linked Tasks

- UVZ-09-ADR-003 (Frontend Build Strategy SASS Import Deprecation)
- UVZUSLNVV-5890 (Migration des SASS Compiler)