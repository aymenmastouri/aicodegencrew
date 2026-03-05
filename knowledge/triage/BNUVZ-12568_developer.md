# Developer Context: BNUVZ-12568

## Big Picture

This repository contains the single‑page Angular front‑end that is used by internal employees and external partners to interact with the Bnotk platform. It lives in the *presentation* layer of a five‑container system (frontend, backend, integration, infra, data). The UI is built with Angular 18‑LTS, Webpack, Karma and Playwright. The task is to migrate the SASS compilation step to the new Angular Builder that Angular 19 mandates. Doing the migration now is required because the upcoming Angular 19 release will break the current build pipeline; postponing it would halt future releases and could introduce UI regressions.

## Scope Boundary

IN: Update the Angular build configuration (angular.json) to use @angular-devkit/build-angular:application, adjust any SASS import statements according to the ADR, run the full unit‑test (Karma) and end‑to‑end (Playwright) suites, and verify the CI/CD Gradle scripts that invoke the Angular build. OUT: Any backend Java services, domain logic, database schema, or unrelated UI components that do not touch SASS or the build pipeline.

## Affected Components

- Angular Build Configuration (infrastructure layer)
- SASS Stylesheets (presentation layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 drops support for the legacy SASS compiler; the new @angular-devkit/build-angular:application builder must be used or the project will fail to compile.
_Sources: tech_versions.json: Angular 18‑lts, ADR: https://wiki.bnotk.de/spaces/UVZUSLNAS/pages/386958007/UVZ-09-ADR-003+-+Frontend+Build+Strategy+SASS+Import+Deprecation_

**[CAUTION] Dependency Risk**
The new builder brings updated peer dependencies (sass, postcss, etc.). Compatibility with the currently pinned versions must be verified to avoid runtime build errors.
_Sources: dependencies.json: @angular/* v18‑lts (will be upgraded to 19), tech_versions.json: TypeScript 4.9.5_

**[BLOCKING] Pattern Constraint**
The ADR documents a deprecation of the old SASS import syntax. All style files may need to be refactored to the new import style before the builder can process them.
_Sources: ADR: https://wiki.bnotk.de/spaces/UVZUSLNAS/pages/386958007/UVZ-09-ADR-003+-+Frontend+Build+Strategy+SASS+Import+Deprecation_

**[CAUTION] Testing Constraint**
Because the compiler change can affect CSS output, the full test suite (Karma unit tests and Playwright e2e tests) must be executed to catch regressions in layout or theming.
_Sources: Issue description: "additional testing may be necessary to minimize the risk of potential regressions"_

**[INFO] Infrastructure Constraint**
The CI pipeline uses Gradle 8.2.1 to trigger the Angular build. Build scripts may need to be updated to pass the new builder options.
_Sources: tech_versions.json: Gradle 8.2.1_


## Architecture Walkthrough

The front‑end lives in the **frontend container** (one of the five containers). Within that container the **presentation layer** holds all Angular components, stylesheets and the build configuration. The SASS compiler is part of the **infrastructure sub‑layer** that supports the build process. The component to touch is the **Angular Build Configurator** (angular.json) which is consumed by the **CI/CD pipeline** (Gradle scripts). Neighbouring components are the **Webpack bundler**, **Karma unit‑test runner**, and **Playwright e2e runner** – all of which read the compiled CSS output. Changing the builder therefore ripples to those neighbours but does not affect backend services or domain logic.

## Anticipated Questions

**Q: Do I need to change any npm packages besides the builder?**
A: Only the builder package (@angular-devkit/build-angular) is required, but you should verify that the versions of @angular/*, sass, and postcss that are pulled in as peer dependencies are compatible with the rest of the stack.

**Q: Will the existing SASS files compile without changes?**
A: The ADR indicates that the old import syntax is deprecated. Some files may need to be updated to the new import style before the new builder can process them.

**Q: Is the CI pipeline affected?**
A: Yes. The Gradle task that runs `ng build` will need to reference the new builder configuration. Verify the Gradle script after the migration.

**Q: How extensive should the testing be?**
A: Run the full Karma unit‑test suite and the Playwright end‑to‑end tests. Pay special attention to visual regressions or layout changes caused by CSS output differences.

**Q: What is the fallback if the migration fails?**
A: Continuing with the old builder is not an option after Angular 19 is released, because the framework will reject the deprecated SASS compilation path. A temporary fix would be to stay on Angular 18, but that defeats the purpose of the planned upgrade.


## Linked Tasks

- UVZ-09-ADR-003 (Frontend Build Strategy SASS Import Deprecation)
- Angular 19 upgrade epic (if any)