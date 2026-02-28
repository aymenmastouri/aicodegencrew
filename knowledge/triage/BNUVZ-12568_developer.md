# Developer Context: BNUVZ-12568

## Big Picture

This repository powers a large enterprise web application that is delivered to internal users via a browser. The UI is a single‑page Angular app (presentation layer) that talks to backend services (Java, Gradle). The task is to migrate the SASS compilation step from the deprecated compiler to the new Angular Builder that Angular 19 requires. The migration is part of the overall Angular 19 upgrade, which is scheduled now to keep the product on a supported stack, obtain security patches and avoid a future build‑breakage scenario. If we postpone the migration, the next major Angular upgrade will fail, the CI pipeline will break and the product will become vulnerable.

## Scope Boundary

IN: All frontend build artefacts – angular.json, any custom webpack or builder configuration, SASS import statements, CI/CD scripts that invoke the Angular build, and the associated unit/e2e test suites that may be affected by the change. OUT: Backend Java services, domain logic, data‑access layer, unrelated UI components that do not touch SASS, and any infrastructure that is not part of the frontend build pipeline.

## Affected Components

- Angular Application (presentation layer)
- Frontend Build Configuration (infrastructure layer)
- CI/CD Build Pipeline (infrastructure layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 removes support for the legacy SASS compiler; the project must switch to the new builder (@angular-devkit/build-angular:application) or the build will fail after the framework upgrade.
_Sources: issue_context: Migration des SASS Compiler, ADR: UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation_

**[CAUTION] Testing Constraint**
The migration can introduce subtle style regressions; comprehensive unit, integration and e2e tests (Karma, Cypress, Playwright) must be re‑run to ensure visual output is unchanged.
_Sources: issue_context: "additional testing may be necessary to minimize the risk of potential regressions"_

**[INFO] Dependency Risk**
Upgrading Angular core packages from 18.2.x to 19.x may expose version incompatibilities with RxJS, @angular/animations, and other Angular libraries; these need verification but do not block the SASS migration itself.
_Sources: analysis_input: Dependencies (runtime) – @angular/* 18.2.13_

**[CAUTION] Technology Constraint**
The project currently uses Webpack 5.80.0 and Angular CLI 18.2.19; the new builder may change the underlying bundler behaviour, so any custom Webpack loader configuration for SASS must be reviewed.
_Sources: analysis_input: Technology Stack – Webpack 5.80.0, Angular CLI 18.2.19_


## Architecture Walkthrough

The Angular SPA lives in the **frontend-webapp** container (presentation layer). Its build artefacts are managed by the **frontend build** component, which resides in the infrastructure layer but is tightly coupled to the presentation layer. The component reads the **angular.json** configuration, invokes the Angular Builder via the Angular CLI, and produces the bundled JavaScript/CSS that is served to browsers. Neighboring components include: • UI component library (shared presentation components) • Backend API gateway (application layer) that the SPA calls at runtime • CI/CD pipeline (infrastructure) that runs the Angular build and executes Karma, Cypress and Playwright tests. The migration will touch only the build component and its configuration; runtime components remain unchanged.

## Anticipated Questions

**Q: Do we need to modify any custom SASS import paths (e.g., the '~' syntax) after the migration?**
A: Yes. The ADR linked in the ticket describes the deprecation of the old import syntax. All SASS files should be updated to use the standard import paths as required by the new Angular Builder.

**Q: Will the migration affect existing unit and e2e tests?**
A: Potentially. Because the compiled CSS may differ, visual regression tests (Cypress, Playwright) should be re‑run. Unit tests that import SASS files via Angular's TestBed may also need to be refreshed.

**Q: Do we have to upgrade Angular CLI and other Angular packages at the same time?**
A: Yes. The new builder is part of Angular 19 and the corresponding CLI version. The upgrade should be performed in a single step to avoid version mismatches.

**Q: Is any change required in the CI/CD pipeline scripts?**
A: Only if the pipeline references the old builder name or custom webpack configuration for SASS. Those references must be updated to the new builder name.

**Q: What is the fallback if the migration introduces breaking style changes?**
A: The fallback is to keep the project on Angular 18 until the issues are resolved, but this would block the planned Angular 19 upgrade and leave the application on an unsupported framework version.


## Linked Tasks

- UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation
- UVZUSLNVV-5890 (this ticket)
- Potential follow‑up task: Angular 19 core upgrade