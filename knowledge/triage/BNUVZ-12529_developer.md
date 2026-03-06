# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a web‑based front‑end application used by internal users (e.g., notaries, administrators) to interact with the underlying back‑end services. It is built with Angular and a proprietary Pattern Library (PL) that provides UI components. The task is to move the front‑end stack from Angular 18 / PL 11.3.1 to Angular 19 / PL 12.6.0. This upgrade is required now because Angular 18 will no longer receive free security patches after 21‑Nov‑2025, forcing the team to either pay for extended support or upgrade. Not upgrading would leave the product exposed to security vulnerabilities and could violate compliance obligations.

## Scope Boundary

IN: All presentation‑layer code (Angular components, modules, services), the Angular CLI build pipeline, TypeScript configuration, Node.js version, and every runtime dependency listed in the acceptance criteria (ng-bootstrap, ng-select, ag‑grid, bnotk/ds‑ng, etc.). Update the Pattern Library to 12.6.0 and verify the vertical action bar remains functional. OUT: Back‑end Java services, database schema, infrastructure provisioning, and any non‑Angular libraries not listed (e.g., Playwright tests, unless they break because of the UI change).

## Affected Components

- All Angular UI components (presentation layer)
- Pattern Library integration module (presentation layer)
- Build configuration (Angular CLI, Webpack) (infrastructure layer)
- Node/TypeScript toolchain (infrastructure layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 requires a newer TypeScript (>=5.0) and a recent Node.js version (>=18). The current stack uses TypeScript 4.9.5 and an older Node.js version, so the toolchain must be upgraded before the framework can be upgraded.
_Sources: tech_versions.json: TypeScript 4.9.5, tech_versions.json: Angular 18-lts_

**[CAUTION] Dependency Risk**
Several UI libraries (ng-bootstrap, ng-select, ag‑grid) have version‑specific compatibility with Angular. Their current versions are tied to Angular 18; upgrading to Angular 19 will likely require newer library releases and may introduce breaking API changes. The ng‑bootstrap patch mentioned in the ticket must be re‑applied to the compatible version.
_Sources: Issue description: ng-bootstrap (Patch von UVZUSLNVV-5824 muss berücksichtigt werden), Acceptance criteria: list of runtime dependencies to update_

**[INFO] Pattern Library Dependency**
Pattern Library 12.6.0 is built for Angular 19. All components that import PL modules must be re‑compiled against the new PL version. The vertical action bar is deprecated but still supported up to PL 13.2.0, so it can remain unchanged for now.
_Sources: Acceptance criteria: Upgrade to Angular 19 and PL 12.6.0, Acceptance criteria: vertical action bar still usable until PL 13.2.0_

**[CAUTION] Testing Constraint**
Unit tests run with Karma and end‑to‑end tests with Playwright may fail after the framework upgrade because of changed Angular testing APIs. Test suites will need to be re‑validated and possibly updated.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_

**[INFO] Architecture Boundary**
The upgrade touches only the presentation container (frontend) and its infrastructure (build pipeline). All other containers (application, domain, data‑access, infrastructure) remain untouched.
_Sources: Architecture Overview: 5 containers, presentation layer = 287 components_


## Architecture Walkthrough

The UVZ system consists of five containers. The front‑end container (often called 'ui' or 'frontend') lives in the **presentation layer** and contains ~287 Angular components, services and UI modules. These components consume the Pattern Library (PL) modules and interact with back‑end APIs via HTTP services located in the application layer. The Angular CLI + Webpack build pipeline (infrastructure layer) compiles the TypeScript source into bundles served to browsers. For this upgrade, you will be working inside the **frontend container**, updating the Angular version, the TypeScript/Node toolchain, and the PL package. Neighboring components are the HTTP client services (application layer) and the shared UI utilities (bnotk/ds‑ng). The vertical action bar component is a deprecated UI element but still part of the PL until version 13.2.0, so it stays in place. All other containers (application, domain, data‑access, infrastructure) are unaffected by the version bump.

## Anticipated Questions

**Q: Which Node.js and TypeScript versions are required for Angular 19?**
A: Angular 19 expects Node.js >=18 and TypeScript >=5.0. The current project uses TypeScript 4.9.5 and an older Node version, so both must be upgraded before the Angular upgrade can succeed.

**Q: Do the listed UI libraries have compatible releases for Angular 19, and what about the ng‑bootstrap patch?**
A: Each library (ng‑bootstrap, ng‑select, ag‑grid) publishes versions aligned with Angular major releases. The latest releases that declare compatibility with Angular 19 should be selected, and the custom ng‑bootstrap patch must be applied to the new version as indicated in the ticket.

**Q: Will the existing unit and e2e tests run after the upgrade?**
A: Karma and Playwright tests may break due to changes in Angular testing APIs and component templates. Test failures are expected and test configurations may need adjustments to align with the new framework version.

**Q: Is the vertical action bar safe to keep, or should it be removed now?**
A: The vertical action bar is deprecated but still supported up to PL 13.2.0. Since the target PL version is 12.6.0, it remains functional and can stay in the codebase for now; removal can be planned for a later release.

**Q: Do we need to touch any back‑end Java code?**
A: No. The upgrade only affects the front‑end (presentation container). All Java services, domain logic, and data‑access layers stay unchanged.


## Linked Tasks

- UVZUSLNVV-5824 (ng‑bootstrap patch reference)
- BNUVZ-12529 (analysis "how to get to angular 21")