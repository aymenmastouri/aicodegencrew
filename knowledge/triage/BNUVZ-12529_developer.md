# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a front‑end web portal used by internal BNOTK users to access various services. The UI is built with Angular and a proprietary Pattern Library (PL) that provides reusable UI components. This task upgrades the UI framework from Angular 18 (now out of security support) to Angular 19 and updates the Pattern Library to version 12.6.0. The upgrade is required now because the current framework will stop receiving security patches after 21‑Nov‑2025, leaving the portal exposed. Without the upgrade the portal would become non‑compliant with security policies and could be attacked, forcing a costly paid support contract or a forced migration later under tighter time pressure.

## Scope Boundary

IN: All Angular packages (core, CLI, CDK, animations, common, compiler, etc.), the Pattern Library (bnotk/ds-ng) to version 12.6.0, Node.js version, TypeScript version, UI‑related third‑party libs (ng‑bootstrap, ng‑select, ag‑grid‑angular, ag‑grid‑community), build tooling (Webpack, Karma, Playwright) where version compatibility is affected, and any UI code that uses deprecated Angular 18 APIs or removed PL components. OUT: Backend Java services, database schemas, non‑UI infrastructure, unrelated npm packages, and any feature work not touching the UI layer.

## Affected Components

- UI Root Module (presentation)
- Pattern Library Integration (presentation)
- All Angular Components (presentation)
- Build Configuration (presentation)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 requires TypeScript 5.x and Node >= 18. The current stack uses TypeScript 4.9.5 and an older Node version, so the upgrade must include a compatible TypeScript and Node release; otherwise the compiler will fail.
_Sources: tech_versions.json: TypeScript 4.9.5, tech_versions.json: Angular 18-lts_

**[CAUTION] Dependency Risk**
ng‑bootstrap has a custom patch referenced in this ticket; the patch requires re‑application or verification against the Angular 19 compatible version of ng‑bootstrap to avoid runtime errors.
_Sources: issue_context: ng-bootstrap (Patch von UVZUSLNVV-5824 muss berücksichtigt werden)_

**[INFO] Pattern Constraint**
The vertical action bar is deprecated in PL 12 but still supported until PL 13.2.0. The upgrade must ensure the bar continues to render and that no removed PL components remain.
_Sources: issue_context: Vertical action bar is still being used (deprecated but still possible to use till PL 13.2.0)_

**[BLOCKING] Security Boundary**
Angular 18 security support ends 21‑Nov‑2025. Continuing to run the current version after that date would leave the portal without security patches, violating internal security policies.
_Sources: issue_context: Support for security updates ended on 21.11.2025 for Angular 18_

**[CAUTION] Testing Constraint**
Karma and Playwright test suites are tied to the current Angular version. Upgrading may require configuration changes or test code updates to align with Angular 19 testing APIs.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_

**[INFO] Infrastructure Constraint**
The project is built with Webpack 5.80.0 and Gradle 8.2.1 for the overall build. Angular 19 may introduce new build‑plugin requirements; ensure Webpack config remains compatible.
_Sources: tech_versions.json: Webpack 5.80.0, tech_versions.json: Gradle 8.2.1_


## Architecture Walkthrough

The UVZ system consists of five containers; the front‑end container (often named *uvz-webapp* or similar) lives in the **presentation** layer and contains ~287 components. This container imports the Angular framework and the Pattern Library (bnotk/ds-ng). Those components communicate with the **application** layer via HTTP APIs. The upgrade work is confined to the front‑end container, which includes the Angular core packages, the Angular CLI, and the Pattern Library version. All dependent UI components (buttons, grids, selects, action bar) are neighbours within the same presentation layer. Build tooling (Webpack, Karma, Playwright) also resides in this container. No changes are required in the backend containers (Java 17, Gradle) or the data‑access/domain layers.

## Anticipated Questions

**Q: Which Node and TypeScript versions do I need for Angular 19?**
A: Angular 19 officially supports Node >= 18 and TypeScript 5.x. The current project uses TypeScript 4.9.5, so you will need to bump TypeScript to the latest 5.x release and ensure the Node version in the CI/CD pipeline meets the minimum requirement.

**Q: Will the existing ng‑bootstrap patch still apply after the upgrade?**
A: The patch was created for the Angular 18 compatible version of ng‑bootstrap. Its applicability to the Angular 19 compatible ng‑bootstrap release depends on compatibility; if it cannot be applied directly, an adaptation of the patch or an upstream fix would be required.

**Q: Do I need to modify the test configuration (Karma/Playwright) after the upgrade?**
A: Yes. Angular 19 introduces changes to the testing APIs. The Karma configuration and Playwright end‑to‑end tests may contain version‑specific imports or globals that are deprecated in the new version.

**Q: Is the vertical action bar guaranteed to keep working after moving to PL 12.6.0?**
A: The vertical action bar is deprecated but remains supported up to PL 13.2.0. After upgrading to PL 12.6.0 it is expected to continue working, provided that none of its dependent PL components were removed in the 12.x series.

**Q: Are there any backend changes required because of the UI upgrade?**
A: No. The upgrade only touches the front‑end container and its dependencies. Backend APIs remain unchanged, so no Java or database work is needed.


## Linked Tasks

- UVZUSLNVV-5824 (this upgrade ticket)
- BNUVZ-12529 (analysis comment "how to get to angular 21")