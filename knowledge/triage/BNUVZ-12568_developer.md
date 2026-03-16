# Developer Context: BNUVZ-12568

## Big Picture

This project is the core UVZ frontend application, built with Angular (v18-lts), running in a Java/Gradle backend containerized environment. It serves internal users across German federal agencies and handles sensitive data (PKI-based auth, exception handling for auth/token errors, etc.). This task supports the strategic frontend build modernization to align with Angular 19’s evolution, specifically addressing the deprecation of legacy SASS compilation semantics. The new SASS compiler enforces stricter import rules and is more performant; skipping this migration risks build instability, visual regressions, and inability to upgrade to Angular 19. Immediate action is needed because Angular 19 is imminent, and SASS-style changes are non-backward-compatible.

## Scope Boundary

IN: Migration of build configuration (e.g., angular.json builders, build options), identification and remediation of deprecated `@import` → `@use` in SASS files, pre-deployment regression tests (visual/functional). OUT: Any Angular core framework changes beyond the build step (e.g., RxJS, Angular DI changes); backend Java changes; non-SASS asset processing (e.g., font embedding, SVG); migration of build tools other than the SASS compiler (e.g., Webpack still remains configured as-is).

## Affected Components

- angular.json (build configuration)
- Sass stylesheets (src/styles/**/*.scss)
- Component styles (src/app/**/*.scss)
- angular-devkit/build-angular:application builder
- Style compilation pipeline (via Webpack loader chain)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 18-lts (current) uses sass-loader v12–v13 internally, which allows loose `@import` behavior; Angular 19's new SASS compiler enforces stricter scoping and import resolution (via Dart Sass 1.75+). This means any legacy `@import 'variables';` statements (without `.scss` extension or relative path) may now fail at build time unless migrated to `@use '~@angular/material' as mat;` style.
_Sources: dependencies.json: @angular/* v18-lts, tech_versions.json: Webpack 5.80.0_

**[CAUTION] Dependency Risk**
The project relies on multiple third-party SASS libraries (e.g., Angular Material). If those libraries expose SASS via `@import` instead of `@use`, and do not ship ESM or `@forward`-ready files, the new compiler will throw import errors. This requires upfront audit of imported SASS modules before migration.
_Sources: dependencies.json: @angular/animations, @angular/cdk, @angular/common etc. v18-lts_

**[CAUTION] Testing Constraint**
Visual regressions are possible due to different SASS variable scoping, precedence, or `!default` resolution. Since the project uses Playwright for e2e tests, those should be extended to cover visual regression checks on key pages (e.g., login, dashboard, forms) — but this task does *not* include writing those tests; only that their need is a consequence.
_Sources: dependencies.json: playwright ~1.44.1, dependencies.json: @angular/animations v18-lts_

**[INFO] Workflow Constraint**
Gradle 8.2.1 is used as the build tool, but it wraps Angular CLI commands. If the Angular build script is invoked through Gradle (e.g., `./gradlew build` → `ng build`), care must be taken to ensure the new builder path is correctly configured in angular.json and propagated to Gradle tasks — no manual Webpack or sass-loader config overrides should persist.
_Sources: tech_versions.json: Gradle 8.2.1_

**[CAUTION] Integration Boundary**
SASS import resolution may differ between old node-sass (now deprecated) and Dart Sass used by Angular’s new builder. Any `~`-based imports like `@import '~styles/variables';` need updating to `@use 'styles/variables';` (without `~`) or adjusted path aliases. This affects how global styles integrate with component-scoped styles — misalignment could cause missing theme tokens or incorrect button/input styles.
_Sources: dependencies.json: @angular/compiler v18-lts, tech_versions.json: Webpack 5.80.0_


## Architecture Walkthrough

You are working on the *frontend build layer*, specifically the SASS compilation step inside the Angular CLI build pipeline. Architecturally, this sits between the `src/` source tree (where `.scss` files live) and the Webpack-based bundler (configured via angular.json and angular-devkit). The builder `@angular-devkit/build-angular:application` now owns both TypeScript *and* SASS compilation via its embedded sass-loader/Dart Sass pipeline. This is distinct from the legacy `@angular-devkit/build-angular:browser` + external sass-loader combo. Your changes will ripple through: (1) angular.json (builder config), (2) any custom Webpack overrides (if present), (3) all `.scss` files that use `@import`. Key neighbors: the `ng build`/`ng serve` CLI entry point (triggered via Gradle), the Storybook or dev server (if used), and the CI pipeline that runs `ng build --prod` or `npm run build`. You must ensure build-time style compilation is fully compatible before the Angular 19 switch.

## Anticipated Questions

**Q: Do I need to manually update every `@import` to `@use`?**
A: Yes — the new Angular SASS compiler enforces Dart Sass semantics. `@import` is deprecated and may break silently or cause specificity issues. Use `@use` for namespacing (e.g., `@use '@angular/material' as mat;`) and ensure paths are absolute relative to `src/`, not relying on webpack aliases like `~styles/variables.scss`. The ADR (UVZ-09-ADR-003) explicitly covers this.

**Q: Will my custom Webpack overrides still work?**
A: No — the new builder abstracts away Webpack config. If you previously extended the Webpack config to customize SASS behavior (e.g., custom loaders or `sassOptions`), those must be migrated to builder options in `angular.json` or removed (if obsolete). The `@angular-devkit/build-angular:application` builder manages the full pipeline, so custom Webpack patches are incompatible.

**Q: How do I verify visual regressions?**
A: Run both pre- and post-migration builds (`ng build --configuration production`) and compare `dist/` output manually and via Playwright visual diff if available. Pay special attention to theme usage (e.g., `mat-light-theme`, `mat-color()`), custom global variables, and component-specific overrides. The test scope is out of this task, but regression *detection* must be part of QA planning.


## Linked Tasks

- UVZUSLNVV-5890 (primary ticket)
- ADR: UVZ-09-ADR-003 (policy basis)