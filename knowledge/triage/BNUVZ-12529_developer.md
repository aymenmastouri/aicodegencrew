# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a web‑based application used by internal BNOTK users (e.g., staff, partners) to access domain‑specific services. The front‑end is built with Angular and consumes a shared Pattern Library (PL) that provides UI components and styling. The task is to move the front‑end from Angular 18 / PL 11.3.1 to Angular 19 / PL 12.6.0. This upgrade is required now because Angular 18 loses free security support on 21 Nov 2025, and the organization wants to avoid paying for extended support while keeping the UI stack modern and safe. If the upgrade is postponed, the application will become a security liability and may breach internal security policies.

## Scope Boundary

IN: All Angular source code, Angular CLI configuration, package.json / npm lock files, TypeScript configuration, Node version used for builds, Pattern Library integration, UI component libraries listed in the acceptance criteria (ng‑bootstrap, ng‑select, ag‑grid, bnotk/ds‑ng), CI/CD build steps that compile the front‑end, unit/e2e test suites (Karma, Playwright). 
OUT: Backend Java services, database schemas, non‑UI micro‑services, infrastructure provisioning (servers, containers), any unrelated front‑end modules that are not part of UVZ, documentation not directly tied to the UI stack.

## Affected Components

- UVZ Front‑end (presentation layer)
- Pattern Library integration (presentation layer)
- Build pipeline for UI (infrastructure layer)
- UI component libraries (presentation layer)

## Context Boundaries

**[CAUTION] Technology Constraint**
Angular 19 requires TypeScript ≥5.0 and Node ≥18. The current stack uses TypeScript 4.9.5 and an unspecified Node version that matches Angular 18‑lts. Upgrading will therefore force a bump of the TypeScript compiler and the Node runtime used in CI/CD and local development.
_Sources: tech_versions.json: Angular 18-lts, tech_versions.json: TypeScript 4.9.5_

**[CAUTION] Dependency Risk**
Several UI libraries (ng‑bootstrap, ng‑select, ag‑grid) have version‑specific compatibility matrices with Angular. The ticket mentions a required patch for ng‑bootstrap; this patch must be re‑evaluated against Angular 19 to ensure it still applies and does not introduce regressions.
_Sources: Issue description: ng-bootstrap (Patch von UVZUSLNVV-5824 muss berücksichtigt werden), Acceptance criteria: list of runtime dependencies to update_

**[INFO] Integration Boundary**
The vertical action bar component is deprecated but remains supported until Pattern Library 13.2.0. The upgrade to PL 12.6.0 must keep this component functional; removal is not required now but future deprecation plans should be noted.
_Sources: Acceptance criteria: Vertical action bar is still used (deprecated but possible until PL 13.2.0)_


## Architecture Walkthrough

The UVZ system consists of 5 containers; the front‑end lives in the **UI container** (presentation layer, ~287 components). This container consumes the shared **Pattern Library** (also part of the UI container) and talks to backend services via HTTP APIs (application layer). The Angular application is built with Webpack and Angular CLI, and its output is served by a static web server in the infrastructure container. Neighboring components include: 
- **bnotk/ds‑ng** (design‑system wrapper) that bridges the Pattern Library to Angular components, 
- **ng‑bootstrap**, **ng‑select**, **ag‑grid** which are imported into various UI components, 
- **Vertical Action Bar** component used across many screens. 
During the upgrade, the developer will be working inside the UI container, updating the Angular version, its CLI, the TypeScript config, and the npm dependencies listed above. After the code changes, the build pipeline (infrastructure layer) will re‑run Webpack to produce the new bundle, which is then deployed to the static server.
Thus, the “you are here” map is: **UI Container → Presentation Layer → Angular App & Pattern Library → Neighboring UI component libraries**.

## Anticipated Questions

**Q: Do we need to upgrade TypeScript and Node versions as part of this task?**
A: Yes. Angular 19 requires TypeScript ≥5.0 and a recent Node version (≥18). The current stack uses TypeScript 4.9.5, so both the TypeScript compiler and the Node runtime used in development and CI must be upgraded.

**Q: Will the existing unit (Karma) and e2e (Playwright) tests continue to run after the upgrade?**
A: Most tests should still run, but breaking changes in Angular 19 (e.g., Ivy compiler updates, changed APIs) may cause failures. Tests need to be executed after the upgrade and any failing specs should be fixed.

**Q: Is the vertical action bar going to be removed during this upgrade?**
A: No. The component is deprecated but still supported up to Pattern Library 13.2.0, so it must remain functional after the upgrade.

**Q: Are there known compatibility issues between Angular 19 and the listed UI libraries (ng‑bootstrap, ng‑select, ag‑grid)?**
A: Each library publishes a compatibility matrix. The ticket notes a specific patch for ng‑bootstrap that must be considered. Before upgrading, verify that the versions you plan to use are declared compatible with Angular 19.

**Q: Will the CI/CD pipeline need changes because of the Angular CLI version bump?**
A: The pipeline currently invokes Angular CLI 18‑lts. After the upgrade, the build scripts must reference the new CLI version, and any custom Webpack or build‑step configurations should be reviewed for deprecations.


## Linked Tasks

- UVZUSLNVV-5824 (this upgrade ticket)
- BNUVZ-12529 (analysis comment "how to get to angular 21")