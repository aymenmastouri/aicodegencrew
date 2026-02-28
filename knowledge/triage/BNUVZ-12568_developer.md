# Developer Context: BNUVZ-12568

## Big Picture

The project is a large Angular single‑page application that serves Bnotk’s customers (both internal users and external partners). It lives in the *presentation* container of the overall system and communicates with backend services via REST/GraphQL. The current task is not about adding a user‑facing feature; it is about preparing the build pipeline for the scheduled Angular 19 upgrade. The new SASS compiler introduced by Angular‑Builder is required for the upgrade to succeed. Doing the migration now avoids a hard break in the CI pipeline, keeps the UI styling process maintainable, and reduces the risk of hidden regressions that could affect the look‑and‑feel of the product. If the migration is skipped, the next build after the Angular version bump will fail, causing release delays and forcing a rushed, higher‑risk fix later.

## Scope Boundary

IN: angular.json builder configuration, any custom webpack or builder overrides, all .scss/.sass source files, CI build scripts that invoke ng build, unit tests (Karma) and e2e tests (Playwright) that validate styling. OUT: backend Java services, domain logic, data‑access layer, any unrelated containers, and non‑SASS related frontend code.



## Affected Components

- frontend‑webapp (presentation layer)
- build‑pipeline (infrastructure layer)
- style‑assets (presentation layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 replaces the legacy SASS compiler with the Angular‑Builder implementation. The build configuration (angular.json) must be updated to use the new builder, otherwise the project will not compile after the framework upgrade.
_Sources: tech_versions.json: Angular 18‑lts, ADR: https://wiki.bnotk.de/spaces/UVZUSLNAS/pages/386958007/UVZ-09-ADR-003+-+Frontend+Build+Strategy+SASS+Import+Deprecation_

**[CAUTION] Dependency Risk**
Existing SASS files may use the deprecated @import syntax or rely on webpack‑sass‑loader options that are no longer supported by the new builder. These files must be audited and possibly refactored to @use/@forward syntax to avoid compilation errors.
_Sources: ADR: https://wiki.bnotk.de/spaces/UVZUSLNAS/pages/386958007/UVZ-09-ADR-003+-+Frontend+Build+Strategy+SASS+Import+Deprecation_

**[CAUTION] Testing Constraint**
Because the SASS compilation path changes, visual regressions can appear. All existing Karma unit tests and Playwright e2e tests must be executed after migration to verify that component styling still renders correctly.
_Sources: Issue description: "additional testing may be necessary to minimize the risk of potential regressions"_

**[INFO] Infrastructure Constraint**
The CI pipeline currently invokes Gradle 8.2.1 which in turn runs npm scripts. The Node.js version used by the pipeline must satisfy Angular 19’s minimum (Node >=18). If the pipeline runs an older Node version, the new builder will fail.
_Sources: tech_versions.json: Gradle 8.2.1, tech_versions.json: Node version not listed but implied by Angular requirements_

**[INFO] Workflow Constraint**
The migration is part of a larger Angular 19 upgrade effort. It should be coordinated with other tasks that update @angular/* packages, routing, and RxJS usage to avoid cascading breakages.
_Sources: tech_versions.json: @angular/* v18‑lts_


## Architecture Walkthrough

WALKTHROUGH: The SASS compiler lives inside the *frontend‑webapp* container, which belongs to the **presentation** layer (287 components). The container is built by the CI pipeline (Gradle → npm → ng build). The build step uses the Angular CLI (currently 18‑LTS) and a Webpack 5 configuration. The SASS compilation is a cross‑cutting concern: every component that imports a .scss file passes through the builder. Changing the builder to @angular-devkit/build-angular:application will affect all style assets, but does not touch runtime code or backend services. Neighboring components include the *style‑assets* module (holds global SCSS files) and the *component‑library* (individual component SCSS). The CI job that runs Karma and Playwright will consume the compiled CSS, so any breakage will surface there. In the diagram: **Container**: frontend‑webapp → **Layer**: presentation → **Component**: angular.json / build‑pipeline → **Neighbors**: webpack config, style‑assets, CI scripts.

## Anticipated Questions

**Q: Do we need to upgrade Node.js in the CI environment before migrating the SASS compiler?**
A: Angular 19 requires Node >=18. Verify the CI agents are running a compatible Node version; if not, upgrade them before applying the new builder.

**Q: Will existing @import statements in SCSS files break?**
A: The new Angular‑Builder deprecates the legacy @import syntax. Files that still use @import should be migrated to the modern @use/@forward syntax to avoid compilation errors.

**Q: Is any custom webpack configuration affected?**
A: If the project overrides the default Angular build with a custom webpack config, those overrides may need to be adjusted because the new builder handles SASS internally and may ignore previous sass‑loader settings.

**Q: How extensive is the required testing?**
A: Run the full suite of Karma unit tests and Playwright e2e tests after migration. Pay special attention to visual regression tests or snapshot tests that compare rendered CSS.

**Q: Will this change impact runtime performance of the application?**
A: The change only affects the build step; the generated CSS should be functionally identical. No runtime performance impact is expected, but verify that bundle sizes remain within acceptable limits.


## Linked Tasks

- UVZ-09-ADR-003 (Frontend Build Strategy SASS Import Deprecation)
- Angular 19 upgrade epic (if exists in the backlog)