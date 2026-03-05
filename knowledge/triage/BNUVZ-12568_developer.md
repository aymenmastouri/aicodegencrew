# Developer Context: BNUVZ-12568

## Big Picture

Our product is a large enterprise web application whose UI is built with Angular (currently v18 LTS). The UI is used by internal users and external customers to perform business processes. The task is to migrate the SASS compilation from the old Angular Builder to the new @angular-devkit/build-angular:application builder as part of the upcoming Angular 19 upgrade. This migration is required now because Angular 19 has deprecated the previous SASS import strategy; without the change the build will fail and we would lose the ability to ship new features or security updates. Not doing it would block the Angular 19 upgrade and could cause production outages when the CI pipeline attempts to build the UI.

## Scope Boundary

IN: Angular UI project (presentation layer), angular.json / build configuration, all .scss/.sass files, CI/CD steps that invoke the Angular build. OUT: Backend Java services, domain and data‑access layers, unrelated micro‑frontends, runtime business logic, and any non‑UI infrastructure.

## Affected Components

- frontend‑app (presentation)
- frontend‑build‑pipeline (infrastructure)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 removes the legacy SASS compiler; the project must switch to the new @angular-devkit/build-angular:application builder to keep the build pipeline functional.
_Sources: ADR: UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation_

**[CAUTION] Dependency Risk**
Existing SASS files may use deprecated import syntax (e.g., @import) that the new builder no longer supports, creating a risk of UI regressions after migration.
_Sources: ADR: UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation_

**[CAUTION] Testing Constraint**
Because the SASS compilation change can affect styling and component rendering, additional UI tests (unit, integration, visual regression) must be executed to verify no regressions are introduced.
_Sources: Issue description: "additional testing may be necessary to minimize the risk of potential regressions"_

**[INFO] Integration Boundary**
The frontend build is triggered from the overall Gradle build (Gradle 8.2.1) and the CI pipeline; any change to the Angular build configuration must remain compatible with the existing Gradle scripts.
_Sources: tech_versions.json: Gradle 8.2.1, tech_versions.json: Angular CLI 18‑lts_

**[INFO] Technology Constraint**
The project currently uses Webpack 5.80.0 for bundling; the new Angular builder may replace or bypass Webpack for SASS processing, so compatibility with existing Webpack configuration must be verified.
_Sources: tech_versions.json: Webpack 5.80.0_


## Architecture Walkthrough

WALKTHROUGH: The application consists of five containers; the UI lives in the **frontend‑app** container, which belongs to the **presentation** layer (≈287 components). The SASS compilation is part of the **frontend‑build‑pipeline** (infrastructure container) that is invoked by the Gradle build. Neighboring components include the Angular CLI configuration (angular.json), the Webpack config, and the CI/CD scripts that call `ng build`. Changing the SASS compiler will affect only the build pipeline and the SASS source files; runtime components (services, domain logic) remain untouched. Think of the map as: **Container: frontend‑app → Layer: presentation → Component: UI components (styles) ↔ Component: build pipeline (infrastructure)**. Your work will be on the build pipeline component and the style assets it processes.

## Anticipated Questions

**Q: Do I need to modify the existing SASS files, or only the build configuration?**
A: The primary change involves the build configuration (angular.json) referencing the new @angular-devkit/build-angular:application builder. Audit of SASS files for deprecated @import statements is recommended, with conversion to the modern @use syntax where applicable.

**Q: Will the change affect the CI/CD pipeline or the Gradle build scripts?**
A: The CI/CD pipeline invokes the Gradle build, which triggers the Angular build. Compatibility of the new builder with existing Gradle scripts is expected; typically Gradle scripts remain unchanged, and the `ng build` command should continue to function from the Gradle task after migration.

**Q: What testing is expected after the migration?**
A: The migration may affect styling, so the full suite of UI unit tests (Karma), integration tests, and visual regression tests (Playwright) are relevant for detecting regressions. Components that heavily rely on SASS variables or mixins are especially sensitive to styling changes.

**Q: Is there any impact on other front‑end libraries (e.g., Angular Material, CDK)?**
A: Angular Material and CDK are on Angular 18 LTS versions and are compatible with the new builder. Library version changes are not required, and their styles are expected to be imported correctly after migration.

**Q: Do we need to upgrade Angular CLI to version 19 now?**
A: The SASS compiler switch is part of the broader Angular 19 upgrade. It can be performed while still on Angular 18, with final verification after upgrading the Angular CLI to version 19 to confirm end‑to‑end compatibility.
