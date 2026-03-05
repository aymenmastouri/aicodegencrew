# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a client‑facing (or internal) web portal built with Angular. It lives in the presentation container of a larger system that also includes Java‑based backend services. Users interact with the UI to perform business processes that are serviced by the backend APIs. The task is to move the UI stack from Angular 18 (LTS) to Angular 19 and update the shared Pattern Library to version 12.6.0. This is required now because Angular 18 will no longer receive free security patches after 21 Nov 2025, exposing the portal to vulnerabilities and forcing the business to pay for a special support contract. Not upgrading would mean operating an insecure, unsupported front‑end, which could lead to compliance breaches and increased maintenance cost.

## Scope Boundary

IN: • Upgrade Angular core, Angular CLI, RxJS, and all Angular‑related packages to the 19.x line. • Update the Pattern Library to 12.6.0. • Bump Node.js, TypeScript, and the listed third‑party UI libraries (ng‑bootstrap, ng‑select, ag‑grid, bnotk/ds‑ng). • Verify that the vertical action bar (still deprecated) continues to work under PL 12.6.0. • Remove code that is only required for Angular 18/PL 11.3.1 unless it is still needed by the new versions. OUT: • Backend Java services, Gradle build scripts, non‑UI infrastructure, and unrelated UI modules that are not part of the UVZ front‑end. • Test suite refactoring (only run after the upgrade, not part of the core scope). • Any UI redesign beyond keeping existing functionality.

## Affected Components

- UVZ Frontend (presentation layer)
- Pattern Library integration (presentation layer)
- UI component library bnotk/ds-ng (presentation layer)

## Context Boundaries

**[CAUTION] Technology Constraint**
Angular 19 requires Node.js ≥ 18 and TypeScript ≥ 5.2. The current stack lists Node.js and TypeScript without versions, so the upgrade will force a Node.js and TypeScript version bump, which may affect any custom build scripts or CI pipelines.
_Sources: tech_versions.json: Angular 18-lts, tech_versions.json: TypeScript 4.9.5_

**[BLOCKING] Dependency Risk**
Third‑party UI libraries (ng‑bootstrap, ng‑select, ag‑grid) have specific version compatibility matrices with Angular. The issue notes a required patch for ng‑bootstrap; failing to apply compatible versions will cause runtime errors or broken UI components.
_Sources: issue_context: ng-bootstrap (Patch von UVZUSLNVV-5824 muss berücksichtigt werden), issue_context: ag-grid-angular, ag-grid-community_

**[INFO] Pattern Constraint**
The vertical action bar is deprecated but still supported up to Pattern Library 13.2.0. The upgrade to PL 12.6.0 must keep this component functional; any removal would break existing screens that rely on it.
_Sources: issue_context: Vertical action bar is still being used (deprecated but still possible to use till PL 13.2.0)_

**[CAUTION] Testing Constraint**
Current test stack uses Karma 6.4.3 and Angular testing utilities tied to Angular 18. After the upgrade, test configuration files (karma.conf.js, tsconfig.spec.json) will need to be aligned with the new Angular version, otherwise tests will fail to compile.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Angular 18-lts_


## Architecture Walkthrough

The UVZ system consists of five containers; the front‑end Angular application lives in the **frontend container** (presentation layer). Within this container, the UI is built from components that consume the shared **Pattern Library (PL)** and the **bnotk/ds-ng** design system. These components call backend APIs (application layer) via HTTP. The upgrade touches only the presentation container: Angular core, Angular CLI, RxJS, and UI libraries. Neighboring components include the vertical action bar (a UI widget) and any custom components that depend on the Pattern Library. The backend containers (Java 17, Gradle) remain untouched, but they expose contracts that the front‑end must continue to honor after the upgrade.

## Anticipated Questions

**Q: Which Node.js and TypeScript versions do we need for Angular 19?**
A: Angular 19 officially supports Node.js 18+ and TypeScript 5.2+. The current project uses TypeScript 4.9.5, so the TypeScript version must be upgraded. Verify the CI pipeline and any custom scripts for compatibility with the newer Node.js runtime.

**Q: Are there breaking changes in Angular 19 that could affect our existing code?**
A: Angular 19 introduces deprecations (e.g., the vertical action bar) and may change APIs for NgModules, router, and forms. Review the Angular upgrade guide for version 19 and run the Angular update schematic (`ng update`) to see suggested migrations. Pay special attention to any usages of deprecated APIs that were still allowed in 18.

**Q: Do the listed third‑party libraries have compatible releases for Angular 19?**
A: Check the release notes of ng‑bootstrap, ng‑select, and ag‑grid for versions that declare compatibility with Angular 19. The issue already mentions a required patch for ng‑bootstrap; that patch must be applied or the library must be upgraded to a version that includes it.

**Q: Will the vertical action bar still work after the Pattern Library upgrade?**
A: Yes, the vertical action bar is supported up to PL 13.2.0, and the target PL version is 12.6.0, so it should continue to function. However, run the UI regression tests to confirm no visual or functional regressions.

**Q: Do we need to adjust the test configuration (Karma, Jasmine) after the upgrade?**
A: Karma itself remains compatible, but the Angular testing utilities (e.g., `@angular/core/testing`) will be upgraded to the 19.x line. Update `tsconfig.spec.json` and any test harness code to match the new TypeScript version and Angular testing APIs.


## Linked Tasks

- UVZUSLNVV-5824 (current ticket)
- BNUVZ-12529 (analysis comment "how to get to angular 21")