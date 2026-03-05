# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a client‑facing web portal built with Angular (presentation layer) that consumes backend services via REST/GraphQL. It is used by internal users and external partners to perform domain‑specific actions. The task is to move the UI stack from Angular 18 / Pattern Library 11.3.1 to Angular 19 / Pattern Library 12.6.0. This is required now because Angular 18 will no longer receive free security patches after 21‑Nov‑2025, exposing the portal to vulnerabilities and forcing the organisation to pay for a special support contract. If the upgrade is not performed, the portal will become a security liability and future feature work will be blocked by an outdated framework.

## Scope Boundary

IN: • Upgrade Angular core, CLI, RxJS, and all Angular packages to v19. • Update Pattern Library to 12.6.0. • Upgrade Node.js and TypeScript to versions required by Angular 19. • Update the listed UI dependencies (ng-bootstrap with its custom patch, ng-select, ag‑grid, bnotk/ds‑ng). • Verify that the vertical action bar (deprecated but still supported) continues to work. • Code that is only needed for Angular 18 / PL 11.3.1 and not supported in the new versions will be excluded. OUT: • Backend services, database schema, domain‑logic components, infrastructure containers, and any non‑UI libraries that are not listed in the acceptance criteria.

## Affected Components

- UVZ UI (presentation layer)
- Pattern Library integration (presentation layer)
- bnotk/ds-ng components (presentation layer)
- ng-bootstrap wrapper components (presentation layer)
- ag-grid Angular components (presentation layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 requires TypeScript >=5.0 and Node.js >=18. The current stack uses TypeScript 4.9.5 (tech_versions.json) and an unspecified Node version, so both must be upgraded before the framework can be upgraded; otherwise the build will fail.
_Sources: tech_versions.json: TypeScript 4.9.5, tech_versions.json: Angular 18‑lts_

**[CAUTION] Dependency Risk**
The project applies a custom patch to ng-bootstrap (mentioned in the issue description). That patch was created for Angular 18 and must be reviewed for compatibility with Angular 19; incompatibility could cause runtime errors in UI components.
_Sources: Issue description: "ng-bootstrap (Patch von UVZUSLNVV-5824 muss berücksichtigt werden)"_

**[INFO] Pattern Constraint**
The vertical action bar is deprecated but still supported until Pattern Library 13.2.0. After the upgrade to PL 12.6.0 it must be verified that the component still renders and that no breaking changes were introduced.
_Sources: Acceptance Criteria: "Vertical action bar is still being used (deprecated but still possible to use till PL 13.2.0)"_

**[CAUTION] Testing Constraint**
Current test tooling (Karma 6.4.3, Playwright 1.44.1) may have compatibility issues with Angular 19. Tests need to be run after the upgrade to confirm they still pass; if not, test‑framework versions may need to be bumped.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_


## Architecture Walkthrough

WALKTHROUGH: UVZ is composed of 5 containers (e.g., UI‑container, API‑gateway, Auth‑service, Data‑service, Infra‑utils). The Angular code lives in the **UI‑container**, specifically in the **presentation layer** (≈287 components). The UI container imports the Pattern Library (PL) and the shared design‑system library **bnotk/ds-ng**. Neighboring components include:
- **ng-bootstrap** wrappers used for modal/dialog UI.
- **ng-select** components for dropdowns.
- **ag-grid-angular** tables for data display.
- The **vertical action bar** component, which is part of the Pattern Library.
All of these are wired together via Angular modules and services that communicate with the backend through the **application layer** (services) but the upgrade does not touch those services. The developer’s work will be confined to the UI‑container, updating the Angular framework, its CLI, and the UI‑specific dependencies, then cleaning up any leftover Angular‑18‑only code.

## Anticipated Questions

**Q: Do we need to upgrade Node.js and TypeScript as part of this task?**
A: Yes. Angular 19 requires Node.js >=18 and TypeScript >=5.0. The current stack uses TypeScript 4.9.5, so both Node and TypeScript must be upgraded before the Angular packages can be updated.

**Q: Will the existing unit and e2e tests run after the upgrade?**
A: They should run, but the current versions of Karma (6.4.3) and Playwright (1.44.1) may need minor version bumps to stay compatible with Angular 19. Tests must be executed after the upgrade to confirm they pass.

**Q: What impact does the custom ng-bootstrap patch have?**
A: The patch was created for Angular 18. It must be reviewed and possibly adapted for Angular 19 because internal APIs of ng-bootstrap may have changed. If the patch is incompatible, UI components that rely on it could break.

**Q: Is the deprecated vertical action bar still usable after the upgrade?**
A: Yes, according to the acceptance criteria it remains supported until Pattern Library 13.2.0. However, after moving to PL 12.6.0 it should be manually verified that no breaking changes affect its rendering or behavior.

**Q: Are there any breaking changes in Angular 19 that could affect our code?**
A: Angular 19 introduces deprecations (e.g., removal of certain lifecycle hooks, stricter type checking) and may change default compiler options. A review of the Angular 19 release notes is required to identify any APIs used in UVZ that have been removed or altered.


## Linked Tasks

- UVZUSLNVV-5824 (this upgrade ticket)
- BNUVZ-12529 (analysis comment "how to get to angular 21")