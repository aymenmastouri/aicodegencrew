# Developer Context: BNUVZ-12568

## Big Picture

Our product is a web‑based application delivered to internal and external users via a browser. The UI is a large Angular monorepo (≈287 presentation components) that is compiled and bundled as part of the CI/CD pipeline. The customer (the business units that rely on the web UI) expects a stable, visually correct interface. The task is to migrate the SASS compilation step from the deprecated Angular 18 builder to the new Angular 19 builder (@angular-devkit/build-angular:application). This migration is required now because Angular 19 removes support for the old SASS import syntax; without it the next scheduled Angular upgrade will cause the build to fail and could introduce visual regressions. If we do not perform the migration, the upcoming release will be blocked and the UI may show broken styles, harming user experience and delaying the product roadmap.

## Scope Boundary

IN: Update angular.json and any related build configuration to use @angular-devkit/build-angular:application, adjust SASS import statements that rely on the deprecated syntax, run the full UI test suite (unit, integration, e2e) to verify no visual regressions, and update CI pipelines if they reference the old builder. OUT: Any backend Java services, domain logic, data‑access layers, or non‑Angular front‑ends; also, feature development unrelated to styling or build configuration.

## Affected Components

- Angular UI components (presentation layer)
- Build configuration (application layer)
- CI/CD pipeline scripts that invoke the Angular builder

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 drops support for the legacy SASS import strategy; the new builder must be used or the build will fail.
_Sources: tech_versions.json: Angular 18‑lts, ADR: https://wiki.bnotk.de/spaces/UVZUSLNAS/pages/386958007/UVZ-09-ADR-003+-+Frontend+Build+Strategy+SASS+Import+Deprecation_

**[CAUTION] Dependency Risk**
The new @angular-devkit/build-angular:application brings its own version of the SASS compiler; incompatibilities with existing @types/chai‑arrays or other dev dependencies may surface and need verification.
_Sources: dependencies.json: @angular/animations v18‑lts, dependencies.json: @angular/core v18‑lts_

**[CAUTION] Testing Constraint**
Because the SASS compilation pipeline changes, existing unit tests (Karma) and e2e tests (Playwright) must be re‑run to catch style‑related regressions.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_

**[INFO] Infrastructure Constraint**
CI pipelines currently invoke the Webpack‑based builder; they will need to be updated to call the Angular 19 builder, otherwise builds will continue using the deprecated path.
_Sources: tech_versions.json: Webpack 5.80.0, tech_versions.json: Gradle 8.2.1_


## Architecture Walkthrough

The frontend lives in the **Web‑App container** (one of the 5 system containers). Within that container the **presentation layer** holds ~287 Angular components that reference SASS style files. Build configuration lives in the **application layer** (angular.json, package.json, CI scripts). The SASS compiler is a cross‑cutting concern: it is invoked by the Angular builder during the build step, producing CSS that is then consumed by the presentation components. Neighboring pieces are the CI/CD pipeline (which triggers the build) and the test suites (Karma for unit tests, Playwright for e2e). Updating the builder will affect the build step only; runtime components remain unchanged.

## Anticipated Questions

**Q: Do I need to change any component code, or is it only the build configuration?**
A: Primarily the build configuration (angular.json) and any SASS import statements that use the deprecated syntax need to be updated. Component TypeScript code is untouched, but you should verify that style URLs still resolve after the migration.

**Q: Will the existing unit and e2e tests still run after the migration?**
A: They should run, but because the SASS compilation pipeline changes you must re‑run the full test suite to ensure no style‑related failures appear. Pay special attention to visual regression tests if any exist.

**Q: Are there any CI/CD changes required?**
A: If the CI scripts invoke the old builder directly (e.g., via a Webpack command), they need to be updated to use the Angular 19 builder. Otherwise the pipeline will continue using the deprecated path and may fail on the next Angular upgrade.

**Q: Is there a fallback if the migration introduces breaking changes?**
A: You can temporarily revert to the Angular 18 LTS branch and the old builder, but that defeats the purpose of the Angular 19 upgrade. The recommended approach is to perform the migration in a feature branch, run all tests, and only merge when the build passes.


## Linked Tasks

- SUPPORT-5890
- UVZUSLNVV-5890
- ADR UVZ-09-ADR-003 (Frontend Build Strategy SASS Import Deprecation)