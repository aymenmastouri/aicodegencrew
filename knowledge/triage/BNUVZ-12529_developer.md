# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a front‑end web application that provides the user interface for the UVZ service platform. It is used by internal employees and external partners to access domain‑specific functionality (e.g., notary registers). The UI is built with Angular and a proprietary Pattern Library (PL) that supplies reusable UI components. This task upgrades the UI framework from Angular 18 (now out of support) to Angular 19 and updates the Pattern Library from 11.3.1 to 12.6.0. The upgrade is required now because security patches for Angular 18 stop on 21 Nov 2025, and the organization wants to avoid paying for a special support contract. If the upgrade is not performed, the application will become vulnerable to security issues and may eventually fail to run on newer browsers or Node.js versions.

## Scope Boundary

IN: • Upgrade Angular core, CLI and related @angular/* packages to v19. • Upgrade Pattern Library to 12.6.0. • Update all listed runtime dependencies (node.js, TypeScript, bnotk/ds‑ng, ng‑bootstrap, ng‑select, ag‑grid‑angular, ag‑grid‑community) to versions compatible with Angular 19. • Verify that the vertical action bar (deprecated but still supported until PL 13.2.0) continues to work. • Remove any code, modules, or styles that belong exclusively to Angular 18 or PL 11.3.1 and are no longer needed. OUT: • Backend Java services, Gradle build scripts, and infrastructure containers. • Non‑UI domain logic. • Existing test suites unless they break because of the upgrade (test‑related fixes are incidental, not a primary deliverable).

## Affected Components

- UVZ Frontend Application (presentation layer)
- Pattern Library Integration (presentation layer)
- Vertical Action Bar Component (presentation layer)
- All UI components that import @angular/* packages (presentation layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 18 LTS support ends on 21 Nov 2025, making the current version a security liability. The upgrade to Angular 19 is mandatory to stay within a supported lifecycle.
_Sources: tech_versions.json: Angular 18-lts (framework)_

**[CAUTION] Dependency Risk**
ng‑bootstrap requires a custom patch referenced in this ticket; the patch must be re‑applied or a compatible version must be selected for Angular 19, otherwise UI components will break.
_Sources: Issue description: ng-bootstrap (Patch von UVZUSLNVV-5824 muss berücksichtigt werden)_

**[INFO] Pattern Constraint**
Pattern Library 11.3.1 will be replaced by 12.6.0. The vertical action bar is deprecated but remains supported until PL 13.2.0, so it can stay but must be verified after the upgrade.
_Sources: Issue acceptance criteria: vertical action bar still being used (deprecated but still possible to use till PL 13.2.0)_

**[CAUTION] Testing Constraint**
Current test tooling (Karma 6.4.3, Angular CLI 18) may be incompatible with Angular 19; test runner versions may need to be upgraded to keep the CI pipeline green.
_Sources: tech_versions.json: Karma 6.4.3 (library), tech_versions.json: Angular CLI 18-lts (build_tool)_


## Architecture Walkthrough

The UVZ system consists of 5 containers; the front‑end container (often named `uvz-webapp` or similar) lives in the **presentation** layer and contains ~287 components. This container hosts the Angular application and the Pattern Library integration. The Angular core modules (@angular/core, @angular/common, etc.) are imported by virtually every UI component. The vertical action bar component is a shared UI widget used across many pages. The Pattern Library provides styled components (buttons, forms, dialogs) that are consumed by the UI components. The front‑end container communicates with backend services (Java 17, Gradle) via REST/GraphQL APIs (application layer). Upgrading Angular and the Pattern Library therefore touches the entire presentation container, but does not affect the backend containers or the infrastructure container.

## Anticipated Questions

**Q: Do we also need to upgrade Node.js and TypeScript versions?**
A: Yes. Angular 19 requires at least Node 18 and TypeScript 5.0+. The current stack lists Node.js (unspecified) and TypeScript 4.9.5, so both will need to be bumped to meet Angular 19’s minimum requirements.

**Q: Will the vertical action bar still work after the upgrade?**
A: The vertical action bar is deprecated but officially supported until Pattern Library 13.2.0. After moving to PL 12.6.0 it should continue to function, but you must run the UI regression tests to confirm no breaking changes.

**Q: Which third‑party libraries must be checked for Angular‑19 compatibility?**
A: ng‑bootstrap (with the custom patch), ng‑select (including ng‑option‑highlight), ag‑grid‑angular, ag‑grid‑community, and any other UI libraries that depend on Angular internals. Their package.json versions need to be aligned with Angular 19’s peer‑dependency requirements.

**Q: Do we need to modify the build tooling (Webpack, Angular CLI) as part of the upgrade?**
A: Angular CLI will be upgraded to the 19 version, which may bring a newer Webpack configuration. Existing custom Webpack tweaks should be reviewed for compatibility, but the core upgrade does not require a full rebuild of the Webpack config unless errors appear.

**Q: What is the fallback if the upgrade introduces regressions?**
A: You can revert the `package.json` and lock files to the previous Angular 18 versions and re‑run the build. The alternative is to keep Angular 18 under a paid Never‑Ending Support contract, but that incurs additional cost and does not resolve the underlying security risk.


## Linked Tasks

- UVZUSLNVV-5824 (this upgrade ticket)
- BNUVZ-12529 (analysis comment "how to get to angular 21")