# Developer Context: BNUVZ-12529

## Big Picture

UVZ (likely a patient or case management system used in healthcare or public service) is a critical Angular-based frontend application that relies on the internal bnotk/ds-ng Pattern Library for UI consistency and components. Angular 18 is end-of-life for security fixes, and the team is constrained to a linear upgrade path (per Angular policy: 18 → 19, *not* 18 → 20 → 21 directly). This upgrade is the first step in a multi-phase modernization effort to stay on a supported Angular track. If not done, the application will face increasing security risks, degraded CI/CD compatibility (e.g., newer toolchains, test runners), and inability to consume security patches or future PL versions — potentially blocking releases and audits.

## Scope Boundary

IN scope: Full upgrade path from Angular 18 to 19, including PL 11.3.1 → 12.6.0, with all listed dependencies (node, typescript, ng-bootstrap, ng-select variants, ag-grid, ds-ng) updated per constraints in AC2. Vertical action bar usage must be preserved. IN scope also includes removing Angular 18/PL 11.3.1 artifacts no longer used or supported — unless preserved in Angular 19/PL 12.6.0. OUT of scope: Any work related to Angular 20/21, backend changes, or non-Angular technologies (e.g., Java/Gradle backend is not modified unless *required* for full compatibility).

## Affected Components

- Angular core modules (core, common, compiler, etc.) (framework)
- Pattern Library integration layer (ds-ng) (ui_library)
- ng-bootstrap, ng-select, ng-option-highlight (ui_library)
- ag-grid-angular + ag-grid-community (data_grid)
- TypeScript configuration and build tooling (build)
- Vertical action bar (deprecated UI pattern, ui_pattern)

## Context Boundaries

**[BLOCKING] Technology Constraint**
The current tech stack (TypeScript 4.9.5, Webpack 5.80.0, Gradle 8.2.1, Java 17) implies a Java/Gradle backend, but Angular upgrade is frontend-only. However, Angular 19 requires TypeScript ≥5.4, meaning TypeScript *must* be upgraded — which will affect build configuration and potentially break existing TypeScript-dependent code. Since Webpack 5.80.0 is used, compatibility with newer Angular CLI (which bundles Webpack) must be verified.
_Sources: tech_versions.json: TypeScript 4.9.5, tech_versions.json: Webpack 5.80.0_

**[BLOCKING] Dependency Risk**
All listed Angular packages (@angular/animations, core, cdk, etc.) are pinned to v18-lts. The upgrade to Angular 19 requires full migration to v19-compatible versions — and *all* related packages (e.g., ng-select, ag-grid, ng-bootstrap) must have v19-compatible releases. ng-bootstrap has a required patch from UVZUSLNVV-5824, meaning this patch must be preserved or re-applied during the upgrade. Failure to align these can cause runtime failures or silent regressions.
_Sources: dependencies.json: @angular/... v18-lts_

**[CAUTION] Pattern Constraint**
The vertical action bar is deprecated but still supported in PL 12.6.0 and up to PL 13.2.0. This means it must remain in the codebase *and* continue to work functionally — but any removal attempts or assumptions about deprecation removal (e.g., in build-time cleanup) are out of bounds. Any migration logic must preserve this UI construct and not assume it is safe to delete.
_Sources: issue context: vertical action bar is deprecated but allowed until PL 13.2.0_

**[CAUTION] Integration Boundary**
The app integrates with backend via HTTP clients, error handlers (e.g., DefaultExceptionHandler, InvalidAuthenticationTokenException). Though Angular upgrade is frontend-only, the upgrade may affect RxJS (currently 7.8.2) and HttpClient behavior, especially around observable error handling patterns. RxJS 7.x is compatible with Angular 19, but subtle breaking changes in error propagation or request interceptors must be tested.
_Sources: dependencies.json: RxJS 7.8.2, error_handling.json: DefaultExceptionHandler variants_

**[CAUTION] Infrastructure Constraint**
The upgrade may require newer Node.js versions than currently used (not listed, but Angular 19 requires Node ≥18.19 or ≥20). If current CI/CD or developer environments run older Node, a version lockstep plan (and upgrade of local + CI Node) is required before npm install succeeds or tests pass.
_Sources: Angular 19 docs: Node ≥18.19/≥20_


## Architecture Walkthrough

This task sits entirely in the *frontend container* — specifically, the Angular application layer built with @angular/* packages, the internal Pattern Library (bnotk/ds-ng), and third-party UI libraries (ng-bootstrap, ng-select, ag-grid). Architecturally, it's at the *ui-layer* boundary: all Angular modules are upgraded in-place; no backend or service-layer changes are needed *unless* runtime behavior changes (e.g., new HttpClient behavior, new NgSelect behavior, or changed grid rendering). The build process is mediated via Angular CLI (which wraps Webpack 5), and the output is bundled and served by the Java backend (Gradle-built). The vertical action bar component likely lives in the `bnotk/ds-ng` library but is consumed into UVZ's own feature modules. Developer work happens in `src/app`, `src/lib`, and config files (`angular.json`, `package.json`, `tsconfig.json`). Neighboring components: backend REST services (unknown to this task), Playwright E2E tests (1.44.1), Karma/Jasmine unit tests (Karma 6.4.3). No new containers or services are introduced — this is a versioned dependency lift.

## Anticipated Questions

**Q: Do I need to touch backend Java code or Gradle tasks?**
A: No — unless a compatibility issue forces backend API adjustments (e.g., new CORS headers, changed JSON parsing), this is strictly a frontend dependency upgrade. Java 17 and Gradle 8.2.1 are unchanged, and Angular CLI compiles to static assets consumed by the backend.

**Q: Where do I find the patch for ng-bootstrap mentioned in UVZUSLNVV-5824?**
A: The patch is referenced as part of issue UVZUSLNVV-5824 — check the Jira ticket’s attachments or comments. It may be a local fork, a patch file, or a branch — and must be preserved or reapplied when upgrading ng-bootstrap to a version compatible with Angular 19.

**Q: How do I verify the vertical action bar still works after the upgrade?**
A: Check the DS (Design System) storyboard (likely in Storybook or internal docs). The component is deprecated but supported up to PL 13.2.0, so its usage in PL 12.6.0 must still function. Identify all pages/components using `<bnotk-vertical-action-bar>` or similar and run regression tests on those routes.

**Q: Can I skip the Node.js version check?**
A: No — Angular 19 requires Node.js ≥18.19 (LTS) or ≥20. If current Node is <18.19, the build will fail at npm install or run. Confirm current Node version in CI + developer environments and align before proceeding.


## Linked Tasks

- BNUVZ-12529 (‘how to get to angular 21’)
- UVZUSLNVV-5824 (patch for ng-bootstrap)