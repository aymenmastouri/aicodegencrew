# Developer Context: BNUVZ-12568

## Big Picture

Our product is a web‑based portal used by internal employees and external partners to perform daily business processes. The front‑end is a single‑page Angular application that lives in the **presentation** container and is built by the CI/CD pipeline. The current task is to adapt the build configuration so that the new SASS compiler introduced in Angular 19 can compile the existing SCSS files. This migration is required now because the Angular 19 release will drop the old compiler; without it the application will no longer build after the framework upgrade, causing a production outage. If we skip the migration, the next scheduled release will be blocked and the UI will lose styling support.

## Scope Boundary

IN: Changes to angular.json (or workspace configuration) that set @angular-devkit/build-angular:application as the builder, modifications to custom webpack or SASS loader settings, inclusion of the full UI test suite execution, and verification that all SCSS imports still resolve. OUT: Any changes to the Angular version itself, backend services, domain logic, or unrelated UI components that do not touch the build configuration.

## Affected Components

- Angular Frontend Build (presentation layer)
- SASS Build Configuration (infrastructure layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 deprecates the legacy SASS compiler; the new @angular-devkit/build-angular:application builder must be used or builds will fail.
_Sources: tech_versions.json: Angular 18‑lts, ADR: UVZ‑09‑ADR‑003 (SASS Import Deprecation)_

**[CAUTION] Dependency Risk**
The new builder pulls in a newer version of the SASS compiler which may have incompatibilities with existing third‑party SCSS libraries or custom webpack loaders; these must be verified in the test suite.
_Sources: dependencies.json: @angular/compiler v18‑lts, dependencies.json: webpack 5.80.0_

**[CAUTION] Testing Constraint**
Because the migration can change the way SCSS imports are resolved, the full UI test suite (Karma + Playwright) must be executed to catch regressions in styling or component rendering.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_

**[INFO] Pattern Constraint**
The ADR UVZ‑09‑ADR‑003 mandates removal of deprecated SASS import syntax; any remaining deprecated imports must be refactored before the migration can succeed.
_Sources: ADR: https://wiki.bnotk.de/.../UVZ-09-ADR-003+-+Frontend+Build+Strategy+SASS+Import+Deprecation_


## Architecture Walkthrough

The front‑end lives in the **presentation** container (one of the five containers). Within that container the Angular application sits in the **presentation layer** and uses the **infrastructure layer** for its build pipeline. The SASS compiler is part of the build infrastructure, configured via angular.json (or workspace.json). Neighboring components include the CI/CD pipeline (which invokes `ng build`), the Karma/Playwright test runners, and any custom webpack configuration that may hook into the SASS loader. Updating the builder will affect the build step only; runtime components (components, services, domain logic) remain untouched.

## Anticipated Questions

**Q: Do any SCSS files need to be changed because of the new compiler?**
A: Only if they use the deprecated import syntax identified in ADR UVZ‑09‑ADR‑003. Those imports must be updated to the new syntax before the migration.

**Q: Will the CI/CD pipeline need changes?**
A: The pipeline will continue to run `ng build`, but the underlying builder changes. Verify that the pipeline’s Docker image or node version supports Angular 19 and the new @angular-devkit packages.

**Q: Is there any impact on existing unit/e2e tests?**
A: Potentially, because style‑related tests (e.g., snapshot or visual regression) could fail if SCSS imports resolve differently. Run the full Karma and Playwright suites after migration to catch regressions.

**Q: Do we need to upgrade other build tools like Webpack?**
A: The new Angular builder abstracts Webpack; the existing Webpack 5.80.0 version remains but is managed internally. No direct upgrade is required unless custom webpack config is used.

**Q: What is the fallback if the migration breaks the build?**
A: Revert the angular.json changes to the previous builder and keep the application on Angular 18 until the issue is resolved.
