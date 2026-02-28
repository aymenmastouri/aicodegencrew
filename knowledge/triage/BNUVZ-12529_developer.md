# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a front‑end portal used by internal users (e.g., staff of the BNO‑TK organization) to access business functions. The UI is built as a single‑page Angular application that lives in the *frontend* container and belongs to the presentation layer. This task upgrades the UI framework from Angular 18 to Angular 19 and moves the shared component library (Pattern Library) from version 11.3.1 to 12.6.0. The upgrade is required now because Angular 18 loses free security support on 21 Nov 2025, creating a security risk and a potential compliance issue. Without the upgrade the portal would either have to pay for paid support or operate with unpatched vulnerabilities, which could lead to data breaches or forced downtime.

## Scope Boundary

IN: All Angular source code, Angular CLI build configuration, npm package.json, related TypeScript configuration, Pattern Library assets, UI‑related unit/e2e tests, CI/CD steps that compile the front‑end. OUT: Backend Java services, database schemas, non‑UI micro‑services, infrastructure provisioning unrelated to the front‑end, and any feature work unrelated to the UI stack.

## Affected Components

- AppModule (presentation)
- RootComponent (presentation)
- VerticalActionBarComponent (presentation)
- SharedUiComponents (presentation)
- PatternLibraryWrapper (presentation)

## Context Boundaries

**[CAUTION] Technology Constraint**
Angular 19 requires TypeScript ≥ 5.0 and a recent Node.js version (≥ 16/18). The current codebase uses TypeScript 4.9.5 and an unspecified Node version, so the upgrade will force a TypeScript and Node version bump.
_Sources: tech_versions.json: Angular 18.2.13, tech_versions.json: TypeScript 4.9.5_

**[CAUTION] Dependency Risk**
Third‑party UI libraries (ng‑bootstrap, ng‑select, ag‑grid) must have versions that are compatible with Angular 19. Their current versions are aligned with Angular 18 and may cause compile‑time or runtime errors after the framework upgrade.
_Sources: Issue description: ng-bootstrap (patch required), ng-select, ag-grid-angular, ag-grid-community_

**[INFO] Pattern Library Constraint**
Pattern Library 12.6.0 still ships the deprecated vertical action bar, but it will be removed after PL 13.2.0. The upgrade must keep the component functional while ensuring no hidden deprecation warnings break the build.
_Sources: Issue description: vertical action bar is still usable until PL 13.2.0_

**[BLOCKING] Security Boundary**
Angular 18 security support ends on 21 Nov 2025. Continuing to run the current version would leave the portal without free security patches, violating internal security policies.
_Sources: Issue description: support for security updates ended on 21.11.2025 for Angular 18_


## Architecture Walkthrough

The UVZ system consists of five containers. The front‑end container (often named *uvz‑frontend* or similar) hosts the Angular SPA. Within this container the code is organized into layers: presentation (≈202 components), application (≈112 components), and domain (≈239 components). The Angular upgrade touches the presentation layer directly – all UI components, modules, and the root bootstrap module live here. These components call services in the application layer (e.g., AuthService, DataFetchService) which in turn communicate with backend APIs via HTTP. The Pattern Library is imported as an npm package and provides shared UI widgets; it sits at the boundary between presentation and application layers. After the upgrade, the build pipeline (Angular CLI → Webpack) will produce new bundles that are served by the same container, so the deployment artifact remains unchanged. Neighboring components that may be indirectly affected are the CI/CD scripts that invoke `ng build` and the e2e test suites (Cypress/Playwright) that run against the compiled app.

## Anticipated Questions

**Q: Which Node.js and TypeScript versions do we need for Angular 19?**
A: Angular 19 officially supports Node 16 LTS and newer (Node 18 is recommended) and requires TypeScript 5.0 or later. The current project uses TypeScript 4.9.5, so both the `tsconfig.json` and the CI environment will need to be updated accordingly.

**Q: Are there breaking API changes in Angular 19 that could affect our existing code?**
A: Angular 19 deprecates several APIs (e.g., the old `Renderer` API, certain lifecycle hooks) and removes support for some legacy providers. A review of the codebase for usage of these deprecated APIs is required; most will be covered by the Angular migration schematic, but manual adjustments may be needed for custom directives or low‑level DOM manipulation.

**Q: Do the current versions of ng‑bootstrap, ng‑select, and ag‑grid work with Angular 19?**
A: These libraries release separate compatibility versions. The versions referenced in the issue are aligned with Angular 18, so you will need to check the latest releases that declare compatibility with Angular 19 and bump the `package.json` entries accordingly. The ng‑bootstrap patch mentioned in the ticket must also be applied to the new version.

**Q: Will the vertical action bar still compile with Pattern Library 12.6.0?**
A: Yes, the vertical action bar is still shipped in PL 12.6.0 and is supported until PL 13.2.0. However, it is marked as deprecated, so the compiler may emit deprecation warnings. Ensure that the component is still imported from the library and that no removal occurs in the upcoming PL version.

**Q: How does the upgrade affect our CI/CD pipeline and test suites?**
A: The pipeline must use the new Angular CLI version (19.x) and the updated Node/TS versions. Unit tests (Karma/Jasmine) and e2e tests (Cypress, Playwright) should be re‑run after the upgrade to catch any breaking changes. No changes to the test code are expected unless they rely on now‑removed Angular APIs.


## Linked Tasks

- UVZUSLNVV-5824 (this upgrade ticket)
- BNUVZ-12529 (analysis comment "how to get to angular 21")