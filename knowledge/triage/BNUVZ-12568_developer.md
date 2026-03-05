# Developer Context: BNUVZ-12568

## Big Picture

Our product is a web‑based application delivered to internal and external users via a browser. The front‑end is a large Angular SPA (single‑page application) that lives in the **presentation layer** of the overall system. It is compiled and bundled by the Angular CLI and shipped through our CI/CD pipeline. The task at hand is to adapt the SASS compilation configuration to the new Angular Builder that will be required once we move the whole front‑end to **Angular 19**. This migration is a prerequisite for the upcoming major framework upgrade, prevents build breakage, and ensures we stay on a supported toolchain. Doing it now avoids a last‑minute rush when the Angular 19 upgrade is performed and reduces the risk of regressions in the UI styling.

## Scope Boundary

IN: Update angular.json (or workspace configuration) to use @angular-devkit/build-angular:application for SASS, adjust any custom SASS import paths, run the front‑end build locally and in CI, verify that the UI renders correctly after the change. OUT: Any other Angular 19 migration work (e.g., RxJS updates, TypeScript version bump, component refactorings), back‑end services, non‑SASS related build steps, and unrelated test suites.

## Affected Components

- Angular workspace configuration (presentation)
- Front‑end build pipeline (infrastructure)
- SASS stylesheets used throughout the UI (presentation)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 drops support for the legacy SASS compiler; the new @angular-devkit/build-angular:application builder must be used, otherwise the project will not compile after the framework upgrade.
_Sources: tech_versions.json: Angular 18-lts (current), tech_versions.json: Angular CLI 18-lts (current), ADR: UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation_

**[CAUTION] Dependency Risk**
The new builder brings its own version of the SASS compiler. Compatibility with existing third‑party SASS libraries or custom import paths must be verified; mismatches could cause silent style regressions.
_Sources: dependencies.json: @angular/common v18-lts, dependencies.json: @angular/compiler v18-lts_

**[INFO] Testing Constraint**
Because the change touches the build process and potentially the generated CSS, regression testing of the UI (visual and unit tests) is required to catch styling breakages.
_Sources: analyzed_architecture.json: Tests count 926_

**[CAUTION] Workflow Constraint**
CI pipelines currently invoke the old builder via Angular CLI 18. The pipeline scripts will need to be updated to reference the new builder, and the build cache may need to be cleared.
_Sources: tech_versions.json: Gradle 8.2.1 (used for CI orchestration), tech_versions.json: Webpack 5.80.0 (still used under the hood by Angular)_


## Architecture Walkthrough

The SASS compiler lives in the **frontend container** (the only container that hosts the Angular SPA). Within that container the relevant layer is **presentation**, where UI components, stylesheets, and the Angular workspace configuration reside. The immediate neighbor is the **infrastructure layer** that runs the build pipeline (Gradle scripts, CI jobs). The SASS configuration is referenced by the Angular CLI (presentation) and consumed by the build tooling (infrastructure). No back‑end or domain components are directly affected, but the CI pipeline (infrastructure) must be updated to call the new builder. Think of the map as: Frontend Container → Presentation Layer (AppModule, component styles) → Infrastructure Layer (build scripts) → CI/CD pipeline.

## Anticipated Questions

**Q: Do I need to change any TypeScript version for Angular 19?**
A: The issue description and current tech stack only mention Angular 18 and TypeScript 4.9.5. Angular 19 typically requires TypeScript 5.x, but that is a separate upgrade task. This ticket focuses solely on the SASS compiler migration; you can keep the current TypeScript version for now and address the TypeScript bump in the broader Angular 19 upgrade.

**Q: Will existing SASS files need to be rewritten?**
A: Most SASS files will continue to work unchanged. The migration only switches the compiler implementation. However, you should verify that any custom import paths or deprecated SASS features still compile with the new builder, and run UI regression tests to catch subtle differences.

**Q: Is the CI pipeline affected?**
A: Yes. The pipeline currently invokes the Angular CLI with the old builder. After migration you must update the build step to reference @angular-devkit/build-angular:application. Also clear any cached build artifacts to avoid stale outputs.

**Q: Do we need to update any npm packages?**
A: The primary change is to add or update the @angular-devkit/build-angular package to a version compatible with Angular 19. No other runtime dependencies are listed as directly impacted, but you should check that the version you install does not conflict with existing Angular packages.

**Q: What level of testing is expected?**
A: Run the full front‑end test suite (unit, integration, and visual tests) after the migration. Pay special attention to components that heavily rely on SASS variables or mixins, as CSS output may differ slightly.
