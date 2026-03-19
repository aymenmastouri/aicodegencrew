# Developer Context: BNUVZ-12568

## Big Picture

This project is a large Angular-based frontend application (currently on Angular 18 LTS) used for secure public-sector services in Germany (UVZ – 'Versorgungsverwaltungszentrale'). The migration is part of a strategic effort to modernize the frontend build stack ahead of the Angular 19 upgrade. The new SASS compiler improves build performance, enforces stricter import resolution (addressing deprecation of `~` imports), and aligns with Angular’s unified build strategy. This task is needed NOW because Angular 19 removes support for the legacy `sass` builder and will break builds if the migration is not completed. Failure to migrate risks delaying the Angular 19 upgrade and introduces styling inconsistencies across environments.

## Scope Boundary

{
  "in_scope": [
    "Migration of the Angular build configuration to use `@angular-devkit/build-angular:application` as the builder",
    "Validation of SASS import compatibility (e.g., removal of deprecated `~` imports, path alias handling)",
    "Testing of visual regression and build output (CSS/SCSS compilation, asset handling, sourcemaps)",
    "Updating documentation or build scripts if needed (e.g., CI/CD pipeline adjustments)"
  ],
  "out_of_scope": [
    "Upgrading Angular itself (this is a preparatory migration for Angular 19, not the upgrade itself)",
    "Refactoring component logic or business logic",
    "Changes to backend services or APIs",
    "Performance tuning beyond verifying build correctness"
  ]
}

## Classification Assessment

The issue is classified as a 'feature' with low confidence (0.5), but this is misleading — it's a *required* upgrade/migration step, not a feature. Evidence FOR 'upgrade': (1) Explicit mention of migration due to Angular 19 update, (2) ADR explicitly addresses SASS import deprecation, (3) Builder change is version-gated (Angular 19+). Evidence AGAINST 'bug' (0.0 score) is clear — no error logs, no broken behavior, only forward-looking change. The correct classification is 'upgrade' (confidence should be 0.95+). (Confirmed bug — 95%)

## Affected Components

- Build configuration
- SASS dependencies
- SASS import statements
- Build pipelines
- E2E test harnesses

## Context Boundaries

**[CAUTION] Technology Constraint**
The project currently uses Angular 18 LTS, and Angular 19 deprecates the old SASS compiler. The new builder (`@angular-devkit/build-angular:application`) enforces stricter SASS import semantics — e.g., `~` imports for node_modules are no longer supported. This means any legacy `@import '~...'` or `@use '~...'` statements must be rewritten to use relative or aliased paths (e.g., `@use '@angular/material'`).
_Sources: @angular/core v18-lts, Webpack 5.80.0_

**[CAUTION] Dependency Risk**
The project uses Webpack 5.80.0 and RxJS 7.8.2. While Webpack is abstracted by Angular CLI, the new builder uses a different internal bundler stack (Vite-based in Angular 19+). This increases risk of subtle build output differences (e.g., CSS chunking, sourcemap generation, asset handling). Any custom Webpack overrides or SASS loader patches must be reviewed.
_Sources: Webpack 5.80.0, RxJS 7.8.2_

**[BLOCKING] Testing Constraint**
The ADR explicitly states 'additional testing may be necessary'. The project uses Playwright 1.44.1 and Karma 6.4.3 for E2E and unit tests, respectively. Visual regression tests (e.g., pixel diffing of styled components) must be added or re-run to catch SASS compilation differences. Without such tests, regressions in UI rendering (e.g., misaligned elements, broken themes) may slip into production.
_Sources: Playwright 1.44.1, Karma 6.4.3_

**[CAUTION] Infrastructure Constraint**
The project uses Gradle 8.2.1 for backend builds, but the frontend build is handled via Angular CLI. The new builder may alter output paths, cache locations, or build artifacts (e.g., `dist/` layout, `styles.css` vs `styles.[hash].css`). Integration with Gradle tasks (e.g., `./gradlew buildFrontend`) must be validated to avoid breaking CI/CD.
_Sources: Gradle 8.2.1_


## Architecture Walkthrough

This work sits at the *infrastructure layer* of the frontend container, specifically in the *build tooling* and *asset compilation* sub-layer. The Angular application (frontend container) is built using Angular CLI, which currently leverages `@angular-devkit/build-angular:sass` or `sass` (legacy) for SASS compilation. This task migrates to `@angular-devkit/build-angular:application`, which is the new unified builder for Angular 19+ that handles both TypeScript and SASS compilation natively. Neighboring components include: (1) Build configuration, (2) SASS dependencies, (3) E2E test runners (Playwright), and (4) CI/CD pipelines. Changes propagate to the compiled CSS assets that feed into the UI rendering layer — any miscompilation here affects *all* visual elements.

## Anticipated Questions

**Q: Do I need to manually update all `~` imports in `.scss` files?**
A: Yes. The new SASS compiler in Angular 19 removes support for the `~` alias for node_modules. You must replace `@import '~@angular/material/theming';` with `@use '@angular/material/theming';` and ensure the package is listed in `dependencies` or `devDependencies`. Use `npm ls sass` to verify version compatibility.

**Q: Will this affect our existing CI/CD or Docker builds?**
A: Potentially. If your CI uses custom Webpack or SASS configs (e.g., `sass-loader`), they may conflict with the new builder. The builder is now part of `@angular-devkit/build-angular`, so ensure the `angular.json` builder is updated and the `@angular-devkit/build-angular` package is upgraded to >=19.0.0 (even if Angular itself is still 18.x).

**Q: What tests must be run to confirm success?**
A: 1. `ng build` succeeds with no SASS errors, 2. All CSS assets are generated (check `dist/styles.css`), 3. Visual regression tests pass (e.g., via Playwright screenshot diffs), 4. Local dev server (`ng serve`) renders styles correctly. Also verify sourcemaps and build time — performance should be similar or better.


## Linked Tasks

- UVZUSLNVV-5890 (SASS Compiler Migration)
- ADR UVZ-09-ADR-003 (Frontend Build Strategy)