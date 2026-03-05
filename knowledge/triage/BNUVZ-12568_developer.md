# Developer Context: BNUVZ-12568

## Big Picture

This repository contains the frontend of a Bnotk internal portal built with Angular. End‑users are employees who interact with the portal for daily business processes. The task is to migrate the SASS compilation from the legacy Webpack‑based compiler to the new Angular Builder that will be mandatory in Angular 19. The migration is part of a larger Angular 19 upgrade and is required now because Angular 19 will drop support for the old compiler, causing the build to break. Without the migration the team cannot ship the next version, delaying feature delivery and security updates.

## Scope Boundary

IN: All Angular source files, SASS/SCSS style sheets, angular.json build configuration, any custom Webpack configuration that references the old SASS loader, CI build scripts that invoke the Angular build. OUT: Backend Java services, database schema, non‑Angular assets, unrelated npm packages, infrastructure outside the frontend container.

## Affected Components

- Frontend Angular Application (presentation layer)
- Build Configuration (application layer)
- SASS/SCSS style assets (presentation layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 deprecates the legacy SASS compiler; the project must switch to @angular-devkit/build-angular:application which uses Dart‑Sass. This is a hard requirement for the upgrade to succeed.
_Sources: ADR: UVZ-09-ADR-003+-+Frontend+Build+Strategy+SASS+Import+Deprecation, issue description: "migration to the new SASS compiler (Angular Builder) @angular-devkit/build-angular:application"_

**[CAUTION] Dependency Risk**
All @angular/* packages are currently pinned to the v18‑lts line. Moving to Angular 19 will require upgrading these packages and ensuring they are compatible with the new builder and the version of the sass npm package.
_Sources: tech_versions.json: Angular 18‑lts, dependencies.json: @angular/core v18‑lts, @angular/common v18‑lts, etc._

**[CAUTION] Testing Constraint**
The migration may change the generated CSS output, potentially breaking visual regressions. Additional testing (unit, integration, and e2e) is required to verify that UI appearance and component behavior remain unchanged.
_Sources: issue description: "additional testing may be necessary to minimize the risk of potential regressions"_

**[INFO] Infrastructure Constraint**
The CI pipeline currently builds the frontend with Gradle 8.2.1 invoking npm scripts. The pipeline must be able to run the new Angular Builder, which may have different node version or environment requirements.
_Sources: tech_versions.json: Gradle 8.2.1, tech_versions.json: Node ecosystem (npm) used for Angular CLI_


## Architecture Walkthrough

The frontend lives in its own container (the "frontend" container) and occupies the presentation layer (≈287 components) plus the application layer for build configuration. The Angular app communicates with backend services via HTTP APIs (infrastructure layer). The SASS migration touches the build configuration (angular.json) and the style assets that are consumed by presentation components. Neighboring pieces are: 1) the CI/CD pipeline (Gradle) that triggers the Angular build, 2) unit test runner Karma and e2e runner Playwright that rely on the compiled CSS, and 3) the backend APIs that are unaffected but may surface UI regressions if styles break. Think of the map as: **Frontend Container → Application Layer (angular.json, builder config) → Presentation Layer (components + SCSS files) → Neighbors: CI pipeline, test suites, backend APIs**.

## Anticipated Questions

**Q: Do I need to change any SASS import statements (e.g., the '~' syntax) after switching to the new compiler?**
A: Yes. The ADR describes that the old '~' import syntax is deprecated. All imports should use the standard relative path or the new tilde‑less syntax supported by Dart‑Sass.

**Q: Will the existing Karma unit tests and Playwright e2e tests still run after the migration?**
A: They should run, but because the compiled CSS may differ, you must run the full test suite to catch visual regressions. No test‑framework changes are required.

**Q: Do we need to upgrade the @angular/* packages to version 19 at the same time?**
A: The SASS migration is a prerequisite for the Angular 19 upgrade. Ideally, upgrade the Angular packages together with the builder change to avoid version mismatches.

**Q: Is there a fallback if the new builder breaks the build?**
A: You can temporarily revert the angular.json builder setting to the previous Webpack configuration, but the project will remain on Angular 18 until the migration is successful.

**Q: What specific CI changes might be needed?**
A: Ensure the CI environment uses a Node version compatible with the new Angular CLI (usually the latest LTS) and that any custom scripts invoking the old Webpack builder are updated to use "ng build" with the new builder.


## Linked Tasks

- UVZUSLNVV-5890 (this migration ticket)
- UVZ-09-ADR-003 (ADR describing SASS import deprecation)
- Potential Angular 19 upgrade epic (not listed here)