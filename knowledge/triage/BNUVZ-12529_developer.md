# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a Bnotk‑owned single‑page web application that provides internal users with access to various services via a rich Angular UI. The UI layer (presentation container) consumes backend APIs (application layer) and uses the internal Pattern Library (PL) for shared components and styling. This task upgrades the UI framework from Angular 18 to Angular 19 and the Pattern Library from 11.3.1 to 12.6.0. The upgrade is required now because Angular 18 will lose free security updates after 21 Nov 2025, exposing the application to vulnerabilities and forcing a costly support contract. If the upgrade is not performed, the system will become insecure, may violate internal compliance policies, and could incur additional licensing fees.

## Scope Boundary

IN: All Angular packages (core, common, compiler, etc.), Angular CLI, TypeScript, Node.js version, Pattern Library 12.6.0, and every UI‑related third‑party library listed (ng‑bootstrap, ng‑select, ag‑grid, etc.). Update build tooling (Webpack, Karma) and test suites (Playwright) as needed. Verify that the vertical action bar continues to work. Remove any code that is only required for Angular 18/PL 11.3.1 unless still needed by the new versions.
OUT: Backend Java services, database schemas, non‑UI infrastructure, unrelated micro‑services, and any feature work not touching the presentation layer.

## Affected Components

- UVZ Frontend (presentation layer) – all Angular components and modules
- Pattern Library integration (presentation layer)
- UI test suites (Karma, Playwright) – presentation layer

## Context Boundaries

**[CAUTION] Technology Constraint**
Angular 19 requires TypeScript ≥ 5.0 and Node.js ≥ 18. The current stack uses TypeScript 4.9.5 and an unspecified Node version, so the runtime and compile‑time environment must be upgraded before the framework can be upgraded.
_Sources: tech_versions.json: TypeScript 4.9.5, tech_versions.json: Angular 18‑lts_

**[BLOCKING] Dependency Risk**
Third‑party UI libraries (ng‑bootstrap, ng‑select, ag‑grid) have version‑specific peer dependencies. Their current versions are built for Angular 18; incompatible versions will cause compile errors or runtime failures after the upgrade. The issue also mentions a custom ng‑bootstrap patch that must be re‑applied or replaced with a compatible version.
_Sources: Issue description: ng‑bootstrap (Patch von UVZUSLNVV‑5824 muss berücksichtigt werden), Issue description: ng‑select, ag‑grid‑angular, ag‑grid‑community_

**[INFO] Integration Boundary**
The vertical action bar component is deprecated but still supported up to Pattern Library 13.2.0. After the upgrade it must still compile and render, otherwise UI functionality will break.
_Sources: Issue acceptance criteria: Vertical action bar is still being used (deprecated but still possible to use till PL 13.2.0)_

**[CAUTION] Testing Constraint**
Karma and Playwright test configurations reference Angular 18 specific globals and build artifacts. After the framework upgrade these configs may need adjustments to work with Angular 19 and the new CLI.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_


## Architecture Walkthrough

The UVZ system consists of five containers. The one we touch is the **UVZ Frontend** container (presentation layer, ~287 components). Inside this container the Angular application is built with Webpack and the Angular CLI. It consumes shared UI components from the **Pattern Library** (also part of the presentation container) and communicates with backend services via HTTP (application layer). Neighboring components include:
- UI services (data fetching, auth) that depend on Angular HttpClient.
- Reusable UI widgets from `bnotk/ds-ng` (design system) which in turn rely on ng‑bootstrap, ng‑select, and ag‑grid.
- The vertical action bar component, currently deprecated but still part of the UI.
The upgrade will replace the Angular core packages and the Pattern Library version, which cascades to all dependent UI modules and the build pipeline (Webpack, Karma). All presentation‑layer components must be re‑compiled against the new versions, while the backend containers remain untouched.

## Anticipated Questions

**Q: Which Node.js and TypeScript versions are required for Angular 19?**
A: Angular 19 officially supports Node ≥ 18.x and TypeScript ≥ 5.0. The current project uses TypeScript 4.9.5, so both the TypeScript compiler and the Node runtime will need to be upgraded before the Angular packages can be upgraded.

**Q: Are the current versions of ng‑bootstrap, ng‑select, and ag‑grid compatible with Angular 19?**
A: The listed versions are built for Angular 18. Compatibility must be verified by checking each library’s release notes. If a compatible version exists, upgrade to it; otherwise a migration path (e.g., replacing the library or applying a compatibility patch) is required. The custom ng‑bootstrap patch mentioned in the ticket also needs to be reviewed for Angular 19 compatibility.

**Q: Will the deprecated vertical action bar still work after the upgrade?**
A: Yes, the vertical action bar is supported up to Pattern Library 13.2.0. After moving to PL 12.6.0 it should continue to compile, but tests should be run to confirm no breaking changes were introduced.

**Q: Do we need to adjust our CI/CD pipeline and test suites?**
A: Potentially. Karma and Playwright configurations reference Angular‑specific globals and build outputs. After the framework upgrade, the build scripts (Webpack, Angular CLI) may produce different artifact paths or require new flags, so the CI pipeline and test configs should be reviewed and updated accordingly.

**Q: What is the fallback if we encounter a blocker during the upgrade?**
A: The fallback is to continue using Angular 18 with a paid Never‑Ending Support contract, but this incurs additional cost and does not address the security risk. The upgrade should therefore be treated as a mandatory path, with any blockers escalated to the architecture team for guidance.


## Linked Tasks

- UVZUSLNVV-5824
- BNUVZ-12529