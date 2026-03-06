# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a large, browser‑based enterprise application used by internal staff to perform daily operational tasks. It is built as a single‑page application (SPA) in Angular and consumes backend services (Java 17, Gradle) via REST. The front‑end lives in the *presentation* layer of the overall architecture and is the visible part of the system for end‑users. This task upgrades the UI framework from Angular 18 to Angular 19 and updates the shared Pattern Library from 11.3.1 to 12.6.0. The upgrade is required now because Angular 18’s security support expires in November 2025; without it the application would be exposed to security vulnerabilities and would need costly paid support. Performing the upgrade now avoids future security risk and aligns the UI stack with the vendor’s supported versions.

## Scope Boundary

IN: • Upgrade Angular core, Angular CLI and TypeScript to the versions required by Angular 19. • Update Pattern Library to 12.6.0. • Update all front‑end runtime dependencies listed in the acceptance criteria (node.js, ng‑bootstrap, ng‑select, ag‑grid, etc.). • Verify that the vertical action bar component still works (it is deprecated but supported until PL 13.2.0). • Include code, modules or styles that are exclusive to Angular 18 or PL 11.3.1 and are not needed by the new versions. OUT: • Any backend Java services, Gradle build scripts unrelated to the front‑end, database schemas, CI/CD pipeline configuration, and non‑UI libraries that are not part of the listed dependencies.

## Affected Components

- Angular UI modules (presentation layer)
- Pattern Library integration components (presentation layer)
- Vertical Action Bar component (presentation layer)
- ng‑bootstrap wrappers (presentation layer)
- ng‑select components (presentation layer)
- ag‑grid tables (presentation layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular must move from the LTS 18 release to the 19 release. This changes the required TypeScript version, Angular CLI version, and may introduce breaking API changes (e.g., Ivy compiler updates, deprecation of certain RxJS operators). All UI code must be compatible with the new compiler and runtime.
_Sources: tech_versions.json: Angular 18‑lts, tech_versions.json: TypeScript 4.9.5_

**[CAUTION] Dependency Risk**
Third‑party UI libraries (ng‑bootstrap, ng‑select, ag‑grid) have specific version matrices for Angular 19. The current versions may not support Angular 19, so compatible releases must be identified and tested. The ng‑bootstrap patch referenced in the ticket must be merged before the upgrade.
_Sources: dependencies.json: @angular/* v18‑lts, issue description: ng‑bootstrap (Patch von UVZUSLNVV‑5824 muss berücksichtigt werden)_

**[INFO] Testing Constraint**
The project uses Karma for unit tests and Playwright for end‑to‑end tests. Both test runners have version compatibility requirements with Angular 19 and the updated TypeScript. Test configuration files may need adjustments.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_

**[CAUTION] Pattern Library Constraint**
Pattern Library 12.6.0 introduces new component APIs and removes some deprecated UI tokens that were still present in PL 11.3.1. All UI components that rely on those tokens must be refactored or the tokens must be kept via a compatibility shim if still required.
_Sources: issue description: Upgrade to Pattern Library 12.6.0_


## Architecture Walkthrough

The UVZ system consists of five containers. The front‑end SPA lives in the **frontend‑webapp** container (presentation layer, ~287 components). Within this container, Angular modules are grouped by feature (e.g., DashboardModule, UserManagementModule). The Pattern Library is imported as a shared UI module that provides styling, layout primitives and the vertical action bar component. These UI modules communicate with backend services via HTTP (REST) through services located in the application layer. Upgrading Angular and the Pattern Library therefore touches every component that imports the shared UI module, all routing definitions, and any custom wrappers around third‑party libraries (ng‑bootstrap, ng‑select, ag‑grid). The vertical action bar component, although deprecated, is still used in several feature modules and must remain functional until the next PL version (13.2.0).

## Anticipated Questions

**Q: Which Node.js version do we need for Angular 19?**
A: Angular 19 requires Node >= 18.0.0 (LTS). The current project likely runs an older LTS, so the Node version will need to be updated, and the CI pipeline should be aligned to the same version.

**Q: Do we have to migrate the existing unit and e2e tests?**
A: Karma and Playwright versions must be compatible with the new TypeScript and Angular compiler. After the upgrade, unit and e2e tests are expected to surface failures due to API changes, which will then need to be examined and adjusted.

**Q: Is the vertical action bar still supported after the upgrade?**
A: The vertical action bar is deprecated but remains supported up to Pattern Library 13.2.0, so it will continue to work with PL 12.6.0. No functional change is required, but verify that its CSS classes and component selectors have not been removed.

**Q: What should we do about the ng‑bootstrap patch mentioned in the ticket?**
A: The patch referenced by UVZUSLNVV‑5824 provides compatibility fixes for ng‑bootstrap with Angular 19; it should be incorporated into the codebase before the ng‑bootstrap version is bumped.

**Q: Will the upgrade affect the backend Java services?**
A: No. The backend runs on Java 17 and is accessed via REST. The upgrade only changes the front‑end build and runtime; backend contracts remain unchanged.


## Linked Tasks

- UVZUSLNVV-5824 (this upgrade ticket)
- BNUVZ-12529 (analysis comment "how to get to angular 21")