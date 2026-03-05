# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a client‑facing web application built with Angular (presentation layer) that consumes backend services (application and domain layers) via REST/GraphQL. The UI is composed of components from the internal Pattern Library (PL) and third‑party libraries (ng‑bootstrap, ag‑grid, ng‑select, etc.). End users are internal staff and external partners who rely on a stable, secure UI. This task upgrades the front‑end framework from Angular 18 to Angular 19 and updates the Pattern Library to version 12.6.0, ensuring continued security updates and compatibility with the latest UI standards. The upgrade is required now because Angular 18’s free security support expires in November 2025; without it the product would become vulnerable and would require costly paid support. If the upgrade is postponed, the system will lose security patches, risk compliance violations, and may face breaking changes when a later major version is finally adopted.

## Scope Boundary

IN: All front‑end code in the UVZ container (Angular application), build configuration (Angular CLI, Webpack), Pattern Library assets, and the npm dependencies listed in the acceptance criteria (node.js, TypeScript, bnotk/ds‑ng, ng‑bootstrap, ng‑select, ag‑grid‑angular, ag‑grid‑community). Update related unit/e2e tests (Karma, Playwright) to compile against Angular 19. OUT: Backend Java services, database schemas, infrastructure (servers, CI pipelines) that are not directly tied to the Angular version, and any UI components that are already removed or unrelated to the listed dependencies.

## Affected Components

- UVZ Frontend (presentation)
- Pattern Library 11.3.1 → 12.6.0 (presentation)
- ng-bootstrap integration (presentation)
- ag-grid integration (presentation)
- ng-select integration (presentation)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 18 LTS loses free security support on 21‑Nov‑2025; upgrading to Angular 19 is mandatory to stay within the supported lifecycle and receive security patches.
_Sources: Issue description: Security support for Angular 18 ends on 21.11.2025_

**[CAUTION] Dependency Risk**
ng-bootstrap requires a custom patch that was created for Angular 18; this patch must be reviewed and possibly adapted for Angular 19 to avoid runtime errors.
_Sources: Acceptance criteria: ng-bootstrap (Patch von UVZUSLNVV-5824 muss berücksichtigt werden)_

**[INFO] Technology Constraint**
Node.js and TypeScript versions must be compatible with Angular 19; using versions that are too old will cause compilation failures.
_Sources: Acceptance criteria: node.js, typescript_

**[INFO] Pattern Library Constraint**
The vertical action bar component is deprecated but still supported until Pattern Library 13.2.0; it must remain functional after the upgrade but can be flagged for future removal.
_Sources: Acceptance criterion 3: Vertical action bar is still being used (deprecated but still possible to use till PL 13.2.0)_


## Architecture Walkthrough

The UVZ system consists of five containers; the front‑end container hosts the Angular application (presentation layer). Within this container, the Angular CLI builds the app using Webpack, and the UI components are sourced from the internal Pattern Library (PL) and third‑party libraries (ng‑bootstrap, ag‑grid, ng‑select). These presentation components call backend APIs exposed by the application layer (REST/GraphQL services) which in turn interact with domain and data‑access layers. For this upgrade, you will be working inside the **frontend container → presentation layer**. Neighboring components include: 
- **API Service Layer** (application container) – provides data contracts that the Angular services consume.
- **Pattern Library** – supplies UI widgets; will be upgraded from PL 11.3.1 to 12.6.0.
- **Build Pipeline** – Angular CLI, Webpack, Karma, Playwright configurations that must be updated to the new framework version.
- **Third‑party integrations** – ng‑bootstrap, ag‑grid, ng‑select; each has its own version matrix with Angular 19.
The developer should locate the `package.json`, `angular.json`, and any custom patches (e.g., ng‑bootstrap patch) within the frontend repo, and ensure that the updated dependencies are reflected throughout the build and test scripts.

## Anticipated Questions

**Q: Which Node.js and TypeScript versions are required for Angular 19?**
A: Angular 19 officially supports Node.js 18+ and TypeScript 5.2+. The current project uses TypeScript 4.9.5, so it will need to be upgraded to at least 5.2 to avoid compilation errors. Verify the exact minimum versions in the Angular 19 release notes.

**Q: Are there breaking changes in Angular 19 that could affect existing components, especially the vertical action bar?**
A: Angular 19 deprecates several APIs from Angular 18 (e.g., certain lifecycle hooks and ViewEngine‑related features). The vertical action bar is already marked deprecated in the Pattern Library but remains functional until PL 13.2.0. Review the Angular 19 migration guide for removed APIs and test the action bar after the upgrade.

**Q: What do I need to do with the custom ng‑bootstrap patch mentioned in the ticket?**
A: The patch was created for Angular 18. You must locate the patch files (likely under `patches/ng-bootstrap`) and verify whether they still apply cleanly to the ng‑bootstrap version compatible with Angular 19. If not, the patch will need to be updated or the upstream library upgraded to a version that already includes the fix.

**Q: Do the unit and e2e test suites need changes?**
A: Yes. Karma and Playwright configurations reference Angular compiler APIs that may have changed. After upgrading, run the full test suite; update any failing specs, especially those that rely on deprecated APIs or component selectors that changed in the new Pattern Library version.

**Q: Is there any impact on the backend services?**
A: The upgrade is confined to the front‑end container. Backend APIs remain unchanged, but ensure that any contract changes (e.g., request payload shapes) introduced by updated UI components are still compatible with the existing backend endpoints.


## Linked Tasks

- UVZUSLNVV-5824 (current upgrade ticket)
- BNUVZ-12529 (analysis comment "how to get to angular 21")