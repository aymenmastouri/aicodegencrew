# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a client‑facing, browser‑based portal built with Angular. It is used by internal staff and external partners to access business services. The portal’s UI is assembled from the in‑house Pattern Library (PL) and third‑party UI components. This task upgrades the front‑end framework from Angular 18 (now out of security support) to Angular 19 and updates the Pattern Library to 12.6.0, together with all dependent UI libraries. The upgrade is required now because the security support window for Angular 18 closes in November 2025; without it the application would be exposed to unpatched vulnerabilities and could breach compliance. If the upgrade is postponed, the team would have to pay for a special support contract or risk operating an insecure system.

## Scope Boundary

IN: All front‑end code in the presentation container – Angular core, Angular CLI, TypeScript configuration, Pattern Library integration, UI component libraries (ng‑bootstrap, ng‑select, ag‑grid), Node.js version, and the vertical action bar usage. OUT: Back‑end Java services, database schema, infrastructure (servers, CI/CD pipelines unless they directly build the Angular app), non‑UI business logic, and any feature flags unrelated to UI rendering.

## Affected Components

- Angular Core (presentation)
- Pattern Library Integration (presentation)
- UI Modules (presentation)
- Vertical Action Bar Component (presentation)
- ng-bootstrap Wrapper (presentation)
- ng-select Wrapper (presentation)
- ag-grid Wrapper (presentation)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 18 LTS reached end‑of‑security‑support on 21‑Nov‑2025; continuing to run it would leave the portal without security patches. The upgrade to Angular 19 is therefore mandatory to stay within a supported lifecycle.
_Sources: tech_versions.json: Angular 18-lts_

**[CAUTION] Dependency Risk**
Third‑party UI libraries (ng‑bootstrap, ng‑select, ag‑grid) must have versions compatible with Angular 19. Some of the listed packages may only support Angular 18, so version mismatches could cause compile‑time or runtime errors.
_Sources: Issue description: ng-bootstrap, ng-select, ag-grid-angular, ag-grid-community_

**[INFO] Pattern Library Version**
Pattern Library 12.6.0 deprecates the vertical action bar after PL 13.2.0 but still supports it now. The upgrade must ensure the vertical action bar continues to function and that any removed components are cleaned up.
_Sources: Issue description: vertical action bar usage_

**[CAUTION] Technology Constraint**
Angular 19 requires at least Node.js 18.x and TypeScript 5.2+. The current stack (Node.js version not listed, TypeScript 4.9.5) may need to be bumped, otherwise the build will fail.
_Sources: tech_versions.json: TypeScript 4.9.5, issue description: node.js_


## Architecture Walkthrough

The UVZ system is split into five containers. The front‑end container (named *uvz‑frontend* in the architecture) hosts the presentation layer (≈287 components). Within this container, the Angular application is the core of the presentation layer. It imports the Pattern Library (PL) as a shared UI component library and wraps third‑party UI packages (ng‑bootstrap, ng‑select, ag‑grid). The Angular app communicates with back‑end services via HTTP APIs (application layer). The vertical action bar is a UI component provided by the Pattern Library and used across many pages. Upgrading Angular and PL therefore touches the core Angular module, the shared UI component modules, and the build pipeline (Webpack + Angular CLI). All downstream components (page modules, feature modules) will be affected because they depend on the upgraded core APIs.

## Anticipated Questions

**Q: Which Node.js and TypeScript versions are required for Angular 19?**
A: Angular 19 officially supports Node.js 18 LTS and TypeScript 5.2+. The project currently uses TypeScript 4.9.5, indicating a version mismatch that would need to be resolved for a successful build.

**Q: Are there breaking changes in Angular 19 that could affect our existing code?**
A: Angular 19 introduces stricter type checking, updates to RxJS, and deprecates several APIs that were still present in Angular 18. Components relying on those deprecated APIs may encounter compile‑time or runtime failures, and the vertical action bar remains usable only until PL 13.2.0.

**Q: Do the UI libraries (ng‑bootstrap, ng‑select, ag‑grid) have compatible releases for Angular 19?**
A: Compatibility depends on the specific library versions; most have released Angular‑19‑compatible builds, but any library lacking such a release would create a version gap that could cause build errors.

**Q: Will the existing unit and e2e tests still run after the upgrade?**
A: The test suite targets Angular 18 APIs and TypeScript 4.9.5; after the upgrade, compilation may fail for tests that import deprecated symbols, and test configurations may need adjustments to align with newer TypeScript and Angular versions.

**Q: Is any change needed in the CI/CD pipeline (Webpack, Angular CLI) for the new versions?**
A: Angular CLI 19 replaces CLI 18, and the built‑in build system supersedes some custom Webpack configurations. Pipeline scripts invoking `ng build` will target the new CLI, and any custom Webpack plugins must be verified for compatibility with the updated toolchain.


## Linked Tasks

- UVZUSLNVV-5824 (this upgrade ticket)
- BNUVZ-12529 (analysis comment "how to get to angular 21")