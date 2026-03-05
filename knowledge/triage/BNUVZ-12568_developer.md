# Developer Context: BNUVZ-12568

## Big Picture

The project is a large Angular front‑end (≈300 presentation components) that powers the user interface for internal and external users of the BNOTK platform. It lives in the *frontend* container and belongs to the presentation layer, but its build configuration is part of the infrastructure layer. The upcoming Angular 19 release removes support for the legacy SASS import strategy, so the current build (using @angular-devkit/build-angular:browser) will no longer compile styles. This ticket drives the migration to the new SASS compiler (Angular Builder) so the UI can continue to be built and delivered without regressions. The migration is required now because the Angular 19 LTS is scheduled for release next sprint; postponing it would cause build breakage and block any further feature work.

## Scope Boundary

IN: Update angular.json (or workspace configuration) to use @angular-devkit/build-angular:application as the builder, adjust any custom SASS import paths that relied on the deprecated syntax, run the full unit‑test and e2e test suite, and verify CI/CD pipeline builds succeed. OUT: Any changes to application logic, backend services, unrelated UI components, or upgrades of other libraries (e.g., RxJS, Karma) that are not directly tied to the SASS compiler migration.

## Affected Components

- Angular Build Configuration (infrastructure layer)
- SASS Compilation Integration (presentation layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 18‑LTS currently uses the legacy SASS compiler which is removed in Angular 19. The new builder @angular-devkit/build-angular:application must be adopted, otherwise the build will fail after the framework upgrade.
_Sources: tech_versions.json: Angular 18‑lts, ADR: UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation_

**[CAUTION] Dependency Risk**
The new builder may have compatibility constraints with existing tooling such as Webpack 5.80.0 and the current Angular CLI 18‑LTS. Verify that the builder works with the existing Webpack configuration and that no hidden version conflicts arise.
_Sources: tech_versions.json: Webpack 5.80.0, tech_versions.json: Angular CLI 18‑lts_

**[INFO] Testing Constraint**
Because the SASS compilation pipeline changes, all unit tests (Karma) and end‑to‑end tests (Playwright) must be re‑run to catch regressions in styling or component rendering.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_


## Architecture Walkthrough

WALKTHROUGH: The frontend container hosts the Angular application. Within that container the **presentation layer** contains the UI components, while the **infrastructure layer** holds the build tooling (Angular CLI, Webpack, SASS compiler). The SASS compiler is wired through the Angular workspace configuration (angular.json) and is invoked by the build target defined in the *application* builder. Neighboring components are the CSS/SASS assets used by UI components and the CI/CD pipeline that triggers `ng build`. Updating the builder does not touch the domain or data‑access layers, but it does affect the build artefact that downstream deployment services consume.

## Anticipated Questions

**Q: Do we need to upgrade Angular itself to version 19 before changing the builder?**
A: Yes. The new builder is only available with Angular 19. The migration should be performed as part of the overall Angular upgrade, but the builder change can be committed and tested on the current branch before the final framework bump.

**Q: Will any existing SASS files need to be rewritten?**
A: Only if they rely on the deprecated `@import` syntax that the old compiler allowed. The new builder follows the standard Sass module system, so `@use`/`@forward` may be required for some files. A quick scan of the `src/**/*.scss` files will reveal any `@import` statements that need conversion.

**Q: How does this affect the CI/CD pipeline?**
A: The pipeline runs `ng build` using the Angular CLI. After the builder change, the pipeline must be updated to use the new target (`@angular-devkit/build-angular:application`). Verify that the Docker image or Node version used in CI still satisfies the Angular 19 peer‑dependency requirements.

**Q: Are there known incompatibilities with other libraries (e.g., Angular Material, CDK)?**
A: All current Angular Material and CDK packages are at v18‑lts, which are compatible with Angular 19 after a minor version bump. No breaking changes are expected for the SASS compiler itself, but run the full test suite to confirm.

**Q: What testing is required after the migration?**
A: Run the complete unit‑test suite (Karma) and the end‑to‑end suite (Playwright). Pay special attention to visual regression tests or snapshot tests that compare rendered CSS, as the new compiler may produce slightly different output.


## Linked Tasks

- UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation
- Angular 19 Upgrade Epic (e.g., UVZUSLNVV-5900)