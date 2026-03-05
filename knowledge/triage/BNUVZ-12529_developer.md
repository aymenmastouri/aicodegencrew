# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a front‑end web application that provides user‑facing functionality for internal BNOTK services. It is built with Angular and consumes a shared Pattern Library (PL) for UI components. The primary users are internal employees who rely on the UI for daily workflows. This task upgrades the UI framework from Angular 18 to Angular 19 and updates the Pattern Library from 11.3.1 to 12.6.0. The upgrade is required now because Angular 18 loses free security support on 21‑Nov‑2025, exposing the system to potential vulnerabilities and forcing a costly support contract. Without the upgrade, the application would become insecure and could violate internal security policies.

## Scope Boundary

IN: • All Angular core packages (core, common, compiler, etc.) and Angular CLI. • TypeScript version required by Angular 19. • Node.js version required by Angular 19. • Pattern Library 12.6.0 and its integration points. • UI third‑party libraries listed in the acceptance criteria (ng‑bootstrap, ng‑select, ag‑grid‑angular, ag‑grid‑community, bnotk/ds‑ng). • Verification that the vertical action bar continues to work (deprecated but still supported until PL 13.2.0). • Removal of any code that is only valid for Angular 18/PL 11.3.1 and not needed by the new versions.
OUT: • Backend Java services, domain logic, data‑access layer, and infrastructure containers. • Non‑UI micro‑services. • Database schema changes. • Major redesign of test frameworks unless a compatibility issue forces it.

## Affected Components

- UI components (presentation layer)
- Pattern Library integration (presentation layer)
- Design System wrapper bnotk/ds-ng (presentation layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 18‑lts is out of security support on 21‑Nov‑2025; upgrading to Angular 19 is mandatory to receive security patches. This is a blocking constraint for the release.
_Sources: tech_versions.json: Angular 18‑lts, tech_versions.json: Angular CLI 18‑lts_

**[CAUTION] Dependency Risk**
Third‑party UI libraries (ng‑bootstrap, ng‑select, ag‑grid) must have versions compatible with Angular 19. The issue notes a specific patch for ng‑bootstrap that must be applied, otherwise runtime errors may occur.
_Sources: Issue description: ng-bootstrap (Patch von UVZUSLNVV-5824 muss berücksichtigt werden)_

**[INFO] Pattern Constraint**
Pattern Library 11.3.1 will be replaced by 12.6.0. The vertical action bar component is deprecated but still functional up to PL 13.2.0; its continued use must be verified after the upgrade.
_Sources: Issue acceptance criteria: Vertical action bar is still being used (deprecated but still possible to use till PL 13.2.0)_

**[CAUTION] Testing Constraint**
Current test stack (Karma 6.4.3, Playwright 1.44.1) may need updates to work with Angular 19. All unit and e2e tests must pass after the framework upgrade.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_

**[BLOCKING] Infrastructure Constraint**
Angular 19 requires a newer Node.js runtime (>= 18). The project’s Node version must be upgraded accordingly, which may affect CI pipelines and Docker images.
_Sources: Issue acceptance criteria: node.js_


## Architecture Walkthrough

The UVZ front‑end lives in the **frontend container** (one of the 5 containers). It sits in the **presentation layer** (≈287 components) and consumes services from the **application layer** via HTTP APIs. The Angular app imports the shared Pattern Library (PL) and the internal design‑system wrapper **bnotk/ds‑ng**. Key neighboring components are:
- UI components (buttons, grids, selects) that depend on ng‑bootstrap, ng‑select, ag‑grid.
- The vertical action bar component, which is part of the PL.
- Backend API services (application layer) that remain unchanged.
During the upgrade, every presentation‑layer component that imports Angular core modules, the PL, or the third‑party UI libs will need to be re‑compiled against Angular 19. The design‑system wrapper (bnotk/ds‑ng) also needs to be aligned to the new PL version. All other containers (backend, data‑access, domain) are untouched.
**YOU ARE HERE**: Inside the frontend container, presentation layer, updating the Angular framework and its UI dependencies.

## Anticipated Questions

**Q: Which Node.js version do we need for Angular 19?**
A: Angular 19 requires Node.js 18 or newer. The current CI/CD pipeline and Docker images will need to be updated to use at least Node 18 LTS.

**Q: Are there breaking changes in Angular 19 that affect our code?**
A: Angular 19 introduces deprecations (e.g., the vertical action bar) and may change compiler APIs. All usages of deprecated APIs must be identified and either updated or confirmed to still work under the new version.

**Q: Do we need to bump TypeScript as well?**
A: Yes. Angular 19 supports TypeScript 5.x; the project currently uses TypeScript 4.9.5, so the TypeScript version must be upgraded to the minimum required by Angular 19.

**Q: Is the vertical action bar still usable after the upgrade?**
A: The vertical action bar is deprecated but remains supported until Pattern Library 13.2.0. After upgrading to PL 12.6.0 it should still work, but verification tests are required.

**Q: What about the third‑party UI libraries – are compatible versions available?**
A: ng‑bootstrap, ng‑select, and ag‑grid all publish versions compatible with Angular 19. The ng‑bootstrap patch mentioned in the ticket must be applied, and the latest compatible releases of the other libraries should be used.


## Linked Tasks

- UVZUSLNVV-5824
- BNUVZ-12529 (comment "how to get to angular 21")