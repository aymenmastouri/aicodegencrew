# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a client‑facing web portal built with Angular (presentation layer) that consumes backend services written in Java 17. End users are internal staff and external partners who use the portal for business processes. The task is to move the UI stack from Angular 18 / Pattern Library 11.3.1 to Angular 19 / PL 12.6.0. This upgrade is required now because the free security support for Angular 18 expires in November 2025; without it the portal would become vulnerable and would have to pay for a special support contract. Performing the upgrade now avoids a security gap and prepares the codebase for the next planned major version (Angular 20/21). If the upgrade is postponed, the team will face a forced, more expensive migration later and may have to operate an unsupported stack.

## Scope Boundary

IN: • Upgrade Angular core, CLI and related packages to v19. • Upgrade Pattern Library to 12.6.0. • Update all listed runtime dependencies (node.js, TypeScript, bnotk/ds-ng, ng‑bootstrap, ng‑select, ag‑grid). • Verify that the vertical action bar continues to work (it is deprecated but still supported until PL 13.2.0). • Remove code that is only compatible with Angular 18 / PL 11.3.1 unless still required by the new versions. OUT: • Backend Java services, database schema, and any non‑UI infrastructure. • New features unrelated to the upgrade (e.g., UI redesign). • Migration to Angular 20/21 (future work). • Changes to CI/CD pipelines that are not directly tied to the Angular version (unless they break the build).

## Affected Components

- AppModule (presentation)
- DesignSystemModule (presentation)
- VerticalActionBarComponent (presentation)
- NgBootstrapModule (presentation)
- NgSelectModule (presentation)
- AgGridModule (presentation)

## Context Boundaries

**[CAUTION] Technology Constraint**
Angular 19 requires a newer TypeScript (≥5.0) and Node.js (≥18). The current stack uses TypeScript 4.9.5 and an unspecified Node version, so the upgrade will force a TypeScript and Node version bump, which may affect tsconfig settings and build scripts.
_Sources: tech_versions.json: TypeScript 4.9.5, tech_versions.json: Angular 18-lts_

**[BLOCKING] Dependency Risk**
Third‑party UI libraries (ng‑bootstrap, ng‑select, ag‑grid) must have releases compatible with Angular 19. If a compatible version does not exist, custom patches or temporary work‑arounds will be needed, and the upgrade could be blocked.
_Sources: dependencies.json: @angular/* v18-lts, issue description: list of dependencies to update_

**[CAUTION] Pattern Constraint**
The vertical action bar component is deprecated in the Pattern Library but remains supported until PL 13.2.0. After the upgrade to PL 12.6.0 it must still compile and render; any removal of deprecated APIs in PL 12 could break it.
_Sources: issue description: vertical action bar still used (deprecated but allowed until PL 13.2.0)_

**[INFO] Integration Boundary**
The frontend communicates with backend services via HTTP APIs defined in the application layer. Angular 19 introduces stricter type‑checking and may change default HttpClient behavior; contracts must be verified to avoid runtime failures.
_Sources: analyzed_architecture.json: layers presentation=287, application=184_

**[CAUTION] Testing Constraint**
Current test stack uses Karma 6.4.3 and Webpack 5.80.0. Angular 19 may require updates to the test harness (e.g., @angular-devkit/build-angular) and possible migration to newer test utilities. Failing tests could block the release.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Webpack 5.80.0_


## Architecture Walkthrough

The UVZ system consists of five containers; the UI lives in the **frontend container** (presentation layer, ~287 components). Within this container the Angular application is bootstrapped by **AppModule**. The design system (Pattern Library) is provided through **DesignSystemModule** (bnotk/ds-ng) and supplies shared UI components such as the **VerticalActionBarComponent**. These UI modules depend on third‑party libraries (ng‑bootstrap, ng‑select, ag‑grid) which are imported as Angular modules. The presentation layer talks to the **application layer** (Angular services) that call backend REST endpoints hosted in the Java container. Upgrading Angular and the Pattern Library therefore touches the **frontend container → presentation layer → UI modules** and their dependencies, but does not affect the Java backend or data‑access components. The developer’s work zone is the **frontend container**, specifically the **AppModule**, **DesignSystemModule**, and any component libraries that import the listed third‑party modules.

## Anticipated Questions

**Q: Which Node.js and TypeScript versions do we need for Angular 19?**
A: Angular 19 officially supports Node ≥18 and TypeScript ≥5.0. The current project uses TypeScript 4.9.5, so the TypeScript version must be bumped (and tsconfig adjusted). The exact Node version used by the CI pipeline should be verified and upgraded if it is below 18.

**Q: Are the listed third‑party libraries (ng‑bootstrap, ng‑select, ag‑grid) already compatible with Angular 19?**
A: You need to check the npm release notes for each library. The issue description mentions a patch for ng‑bootstrap that must be considered, indicating that at least one library may need a custom fix. If a library does not yet have a version for Angular 19, you may have to stay on the latest compatible version or apply the patch until an official release is available.

**Q: Will the vertical action bar still work after the Pattern Library upgrade?**
A: The vertical action bar is deprecated but supported up to PL 13.2.0. After moving to PL 12.6.0 it should still compile, but you must verify that no API it relies on has been removed in PL 12. Run the UI and visual regression tests to confirm its behavior.

**Q: Do we need to update the test configuration (Karma, Webpack) as part of the upgrade?**
A: Angular 19 may require newer versions of @angular-devkit/build-angular, which can affect the Karma/Webpack configuration. Review the Angular upgrade guide for any required changes to the test runner and adjust the configuration accordingly.

**Q: Is any backend code affected by this UI upgrade?**
A: No. The backend Java services remain unchanged. The only integration point is the HTTP API contract, which is already stable. Ensure that any request/response payloads used by the UI are still compatible, but no backend code changes are required.


## Linked Tasks

- UVZUSLNVV-5824 (this upgrade ticket)
- BNUVZ-12529 (analysis "how to get to angular 21")