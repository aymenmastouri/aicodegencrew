# Developer Context: BNUVZ-12568

## Big Picture

The project is a large Angular single‑page application that serves internal users (e.g., employees of the client) and external customers via a web UI. It lives in the **frontend** container and belongs to the **presentation** layer of the overall system architecture. The task is to migrate the SASS compilation step to the new Angular Builder because Angular 19 deprecates the old SASS import strategy. This migration is part of the scheduled Angular 19 upgrade, which is required now to stay on a supported framework version and to avoid build breakage. If the migration is not performed, the next framework upgrade will fail, causing downtime for UI releases and increasing the technical debt of the styling pipeline.

## Scope Boundary

IN: Update `angular.json` (or workspace configuration) to use `@angular-devkit/build-angular:application` for SASS, adjust any custom SASS loader settings, verify that all `.scss` files compile, run the full UI test suite (Karma, Playwright) to catch regressions. OUT: Any other Angular version upgrades (e.g., core, router), backend services, database schema changes, or feature development unrelated to the build process.

## Affected Components

- AngularBuildConfig (presentation)
- StyleCompilation (presentation)
- CI/CD Build Pipeline (infrastructure)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 no longer supports the legacy SASS import syntax; the project must switch to the SASS compiler provided by `@angular-devkit/build-angular:application`. This drives the need to change the build configuration and may require updating the SASS version used by the project.
_Sources: tech_versions.json: Angular 18-lts, tech_versions.json: Angular CLI 18-lts, ADR: UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation_

**[CAUTION] Testing Constraint**
The migration can introduce subtle style regressions. All existing unit tests (Karma) and end‑to‑end tests (Playwright) must be executed after the change to ensure the UI renders correctly.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_

**[INFO] Dependency Risk**
The new builder may depend on a newer version of the `sass` npm package. Verify that the current `sass` version in `package.json` satisfies the builder’s peer‑dependency range to avoid install failures.
_Sources: dependencies.json: @angular/compiler v18-lts_

**[CAUTION] Workflow Constraint**
CI/CD pipelines that invoke `ng build` need to be checked for any custom flags that were previously used for the old SASS compiler. Those flags may be obsolete or cause errors with the new builder.
_Sources: architecture_overview: 5 containers, 1003 components_


## Architecture Walkthrough

The SASS compilation lives inside the **frontend** container, specifically in the **presentation** layer. The key component is `AngularBuildConfig`, which is defined in `angular.json` and is consumed by the Angular CLI during the build step. This component talks to the **CI/CD pipeline** (infrastructure) that triggers `ng build` and later to the **test harness** (Karma for unit tests, Playwright for e2e). After migration, the `AngularBuildConfig` will point to the `@angular-devkit/build-angular:application` builder, which internally uses the new SASS compiler. No other containers (e.g., backend, data‑access) are affected. The neighboring components are:
- `StyleCompilation` (processes `.scss` files)
- `CI/CD Build Pipeline` (executes the build)
- `Karma` and `Playwright` test runners (validate output).
The migration involves updating the builder entry in `angular.json` and ensuring the test suite runs successfully to validate the output.

## Anticipated Questions

**Q: Do I need to update the `sass` npm package version as part of this migration?**
A: Check the peer‑dependency range of `@angular-devkit/build-angular` (documented in its package.json). If the current `sass` version is outside that range, bump it to a compatible version. Otherwise, no change is required.

**Q: Will this migration affect existing unit or e2e tests?**
A: Potentially. The new compiler may produce slightly different CSS output (e.g., ordering, source maps). Run the full Karma and Playwright suites after the change to catch any visual regressions.

**Q: Are there any CI/CD script changes needed?**
A: Review the build scripts for custom flags that were specific to the old SASS compiler. Those flags may be removed or replaced. The basic `ng build` command stays the same.

**Q: Is this migration tied to the Angular version bump, or can it be done independently?**
A: The new SASS compiler is only available in the Angular 19 builder package. Therefore the migration must be performed as part of the Angular 19 upgrade; doing it earlier would require pulling in a future‑preview version of the builder, which is not recommended.

**Q: What should I do if the build fails after switching the builder?**
A: Typical causes are missing peer dependencies or leftover custom loader configurations in `angular.json`. Reviewing the error output and aligning the configuration with the new builder resolves most issues.


## Linked Tasks

- UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation (architectural decision record)
- Angular 19 Upgrade Epic (parent epic for this migration)