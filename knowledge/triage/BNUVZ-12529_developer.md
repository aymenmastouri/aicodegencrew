# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a web‑based client application built with Angular that serves internal users (e.g., staff of the BNOTK ecosystem) to interact with backend services. The UI lives in the presentation container and consumes a shared Pattern Library for UI components. This task upgrades the front‑end framework from Angular 18 to Angular 19 and updates the Pattern Library from 11.3.1 to 12.6.0. The upgrade is required now because Angular 18 loses free security support on 21‑Nov‑2025, exposing the product to unpatched vulnerabilities. If the upgrade is not performed, the application will either have to pay for a support contract or run an unsupported stack, risking security incidents and compliance breaches.

## Scope Boundary

IN: All Angular front‑end code (presentation layer), the Pattern Library integration, related npm dependencies (ng‑bootstrap, ng‑select, ag‑grid, etc.), build configuration (Angular CLI, Webpack), Node.js and TypeScript versions, and the vertical action bar component. OUT: Backend services, database schemas, non‑UI business logic, infrastructure‑as‑code unrelated to the front‑end, and any feature work unrelated to the upgrade.

## Affected Components

- Angular Application (presentation layer)
- Pattern Library Integration Module (presentation layer)
- Vertical Action Bar Component (presentation layer)
- UI Component Library Wrappers (ng-bootstrap, ng-select, ag-grid) (presentation layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 18 LTS support ends on 21‑Nov‑2025; the product must move to a supported major version to receive free security updates.
_Sources: tech_versions.json: Angular 18-lts (framework), https://endoflife.date/angular (support end date)_

**[CAUTION] Dependency Risk**
ng-bootstrap requires a specific patch that is mentioned in the ticket; the patch must be applied after the version bump to avoid regressions.
_Sources: Issue description: ng-bootstrap (Patch von UVZUSLNVV-5824 muss berücksichtigt werden)_

**[INFO] Pattern Constraint**
Pattern Library 11.3.1 will be removed; upgrade to PL 12.6.0 is required. The vertical action bar is deprecated but still supported until PL 13.2.0, so it can remain temporarily.
_Sources: Issue acceptance criteria: Pattern Library 12.6.0, Issue acceptance criteria: Vertical action bar still used (deprecated but allowed until PL 13.2.0)_

**[CAUTION] Testing Constraint**
Current test stack (Karma 6.4.3, Playwright 1.44.1) must be verified for compatibility with Angular 19; some test utilities may need updates.
_Sources: tech_versions.json: Karma 6.4.3 (library), tech_versions.json: Playwright 1.44.1 (library)_

**[BLOCKING] Infrastructure Constraint**
Angular 19 requires a newer Node.js (>= 18) and a newer TypeScript version (>= 5.2). Both must be upgraded as part of the task.
_Sources: Issue acceptance criteria: node.js, Issue acceptance criteria: typescript_


## Architecture Walkthrough

The UVZ system consists of 5 containers. The front‑end Angular application lives in the **frontend container** (presentation layer, ~287 components). It consumes the shared **Pattern Library** (also part of the presentation layer) and talks to backend APIs via HTTP. Upgrading Angular and the Pattern Library touches every UI component, the build pipeline (Angular CLI, Webpack), and the npm dependency graph (ng‑bootstrap, ng‑select, ag‑grid, etc.). Neighboring layers are the **application layer** (services that expose REST endpoints) and the **infrastructure layer** (CI/CD pipelines, Docker images). The vertical action bar component is a UI widget that resides in the presentation layer and is currently deprecated but still functional until PL 13.2.0. All changes will be confined to the presentation container; no changes are expected in the data‑access or domain layers.

## Anticipated Questions

**Q: Which Node.js and TypeScript versions are required for Angular 19?**
A: Angular 19 officially supports Node.js 18 LTS and newer (Node 20 is recommended) and TypeScript 5.2+. The current project uses Node.js (unspecified) and TypeScript 4.9.5, so both need to be upgraded to meet the minimum requirements.

**Q: Do we need to modify the test configuration (Karma, Playwright) after the upgrade?**
A: Yes. Verify that Karma 6.4.3 and Playwright 1.44.1 are compatible with Angular 19. If not, update to versions that support the newer Angular compiler and test utilities.

**Q: Is it safe to keep the vertical action bar until PL 13.2.0?**
A: Yes. The acceptance criteria state that the vertical action bar may remain in use because it is still supported by the Pattern Library up to version 13.2.0. No immediate code changes are required for this component.

**Q: What impact will the ng-bootstrap patch have on our codebase?**
A: The patch referenced in the ticket must be applied after updating ng-bootstrap to a version compatible with Angular 19. Review the patch details (UVZUSLNVV-5824) and ensure it is merged before running the application.

**Q: Will other UI libraries (ng-select, ag-grid) need version bumps?**
A: Yes. The acceptance criteria list ng-select, ng-option-highlight, ag-grid-angular, and ag-grid-community as dependencies that must be updated. Check each library’s release notes for Angular 19 compatibility and upgrade accordingly.


## Linked Tasks

- UVZUSLNVV-5824
- BNUVZ-12529 (analysis comment "how to get to angular 21")