# Developer Context: BNUVZ-12568

## Big Picture

This project is a mission-critical Angular-based frontend (UVZ) used in a German public health/insurance context — high availability, strict compliance, and enterprise-grade UX are required. The customer is internal developers and QA engineers relying on stable, deterministic builds. This task solves the looming compatibility breakage from Angular 19's enforced SASS compiler migration. It's needed NOW because Angular 19 removes support for legacy build behaviors (e.g., global `@import` resolution), and delaying this risks blocking the entire Angular 19 upgrade — which itself is likely tied to security, support, or feature-compatibility deadlines. If not done, builds may break or visual regressions could silently enter production.

## Scope Boundary

IN: Adjusting `angular.json` build configuration to use `@angular-devkit/build-angular:application`, verifying SASS import compatibility (e.g., removal of deprecated global imports), updating any custom build scripts that reference old SASS behavior. OUT: Refactoring SASS code logic (e.g., variable/function changes), migrating non-SASS assets, upgrading Angular itself (that’s assumed to be pre-done), or modifying backend code.

## Affected Components

- Angular Builder Configuration (build)
- SASS Entry Points (styles/imports)
- CI/CD Build Pipeline (infrastructure)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 18-LTS currently in use (per `@angular/core v18-lts`) means the project is still on the old SASS compiler path — this migration is only triggered by upgrading to Angular 19. The build configuration must be updated *before* the Angular 19 migration is complete, as the new builder is incompatible with legacy SASS behavior (e.g., automatic `@import` injection from node_modules).
_Sources: dependencies.json: @angular/core v18-lts, issue context: migration to @angular-devkit/build-angular:application_

**[CAUTION] Dependency Risk**
The project uses Webpack 5.80.0 and Angular CLI (implied via `@angular-devkit/build-angular`), which tightly couples the SASS compilation pipeline to Angular CLI internals. Changing the builder may alter how `sass` files are resolved, especially if custom Webpack overrides exist. Any custom loader or `sass` options (e.g., `prependData`) may need reconfiguration.
_Sources: tech_versions.json: Webpack 5.80.0_

**[CAUTION] Testing Constraint**
The issue explicitly notes that additional testing is needed to minimize regressions — this is not a silent refactor. Visual regression tests or E2E test suites (e.g., Playwright 1.44.1) should be run post-migration. Without this, visual bugs (e.g., misaligned components, missing themes) may go unnoticed in CI.
_Sources: tech_versions.json: Playwright 1.44.1, issue context: 'additional testing may be necessary'_

**[INFO] Infrastructure Constraint**
Gradle 8.2.1 is used as the build tool — but this is likely for the *backend*. The frontend build is Angular CLI-based, so Gradle does not directly control SASS compilation. However, if the CI pipeline chains Gradle → frontend build, any breakage in the SASS step may cause Gradle builds to fail. Thus, SASS changes must be verified end-to-end in CI.
_Sources: tech_versions.json: Gradle 8.2.1_


## Architecture Walkthrough

This task sits at the *build orchestration layer* — specifically, in `angular.json` and related CLI configuration files. The Angular application uses the CLI’s builder pattern (`architect.build.builder`) to compile TypeScript + SASS into static assets. The migration targets the `@angular-devkit/build-angular:application` builder (replacing older `application` or `browser` builders), which uses the modern `sass` compiler implementation and enforces stricter import resolution (no auto-injection of `styles.scss` from node_modules). This change affects the *asset generation stage* of the build pipeline, upstream of bundling and minification. Neighboring components: `webpack.config.js` (if present), CI job definitions, and the `src/styles.scss` / `src/theme/` folders that contain global SASS imports. The SASS files themselves are not changing — only the *rules* under which they’re processed.

## Anticipated Questions

**Q: Do I need to update `angular.json` manually — what exactly changes?**
A: Yes. You must replace the `builder` value under `architect.build` (and possibly `architect.serve`) from the old value (likely `@angular-devkit/build-angular:browser` or similar) to `@angular-devkit/build-angular:application`. Also, verify `styles` and `stylePreprocessorOptions` sections — especially if you use `styleUrls` that rely on legacy `@import` resolution. If your project uses `angular.json`’s `buildOptions.styles` to inject global SASS (e.g., via `prependData`), that may no longer work and must be replaced with explicit `@import` in entry SASS files.

**Q: Why is the ADR (UVZ-09-ADR-003) relevant — should I read it?**
A: Yes — it documents the decision to adopt the new builder due to deprecation of the old SASS import behavior. It likely includes migration steps, rationale for rejecting alternatives (e.g., staying on older Angular), and acceptance criteria (e.g., 'no visual regressions in smoke tests'). The ADR is the source of the policy requiring this change.

**Q: What kind of tests do we need — can I reuse existing Playwright/E2E tests?**
A: Yes, but with caveats: Playwright E2E tests will catch major layout issues, but minor visual regressions (e.g., font-weight, spacing) require visual regression testing (e.g., percy-like tools). At minimum, run full E2E test suite and manually verify theme consistency (e.g., login screen, dashboard, forms). The issue explicitly asks for 'additional testing' — so don’t assume unit test coverage is sufficient.
