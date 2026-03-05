# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a web‑based application that provides a user interface for internal (or external) stakeholders. The UI is built as a single‑page Angular application (presentation layer) that consumes backend services via HTTP. The UI uses the in‑house Pattern Library (PL) for consistent look‑and‑feel. This task upgrades the front‑end framework from Angular 18 to Angular 19 and updates the Pattern Library from 11.3.1 to 12.6.0, together with all dependent npm packages. The upgrade is required now because Angular 18 loses security support on 21 Nov 2025, and the organization wants to avoid paying for a proprietary support contract. Without the upgrade the application would become a security liability and could fall out of compliance with corporate security standards.

## Scope Boundary

IN: All front‑end source code (Angular modules, components, services), Angular CLI build configuration, npm package.json, Pattern Library integration, UI tests (Karma, Playwright), CI/CD pipeline steps that install Node/TypeScript/Angular CLI, and the vertical action bar component. OUT: All backend Java services, database schemas, infrastructure provisioning, non‑UI micro‑services, and any unrelated front‑end modules that are not part of the UVZ UI bundle.

## Affected Components

- UVZ Angular Application (presentation layer)
- Pattern Library Integration (presentation layer)
- ng-bootstrap wrapper components (presentation layer)
- Vertical Action Bar component (presentation layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 18 LTS loses security support on 21 Nov 2025, making the current version unacceptable for production. The upgrade to Angular 19 is therefore a mandatory, blocking requirement.
_Sources: tech_versions.json: Angular 18-lts_

**[CAUTION] Dependency Risk**
ng-bootstrap requires a specific patch (referenced in the ticket) that must be compatible with Angular 19. The patch may need to be re‑applied or a newer version of ng-bootstrap may be required, so verification is needed.
_Sources: Issue description: ng-bootstrap (Patch von UVZUSLNVV-5824 muss berücksichtigt werden)_

**[CAUTION] Technology Constraint**
Angular 19 requires Node.js ≥ 18 and TypeScript ≥ 5.2. The current stack (Node version not listed, TypeScript 4.9.5) must be upgraded accordingly, otherwise the build will fail.
_Sources: tech_versions.json: TypeScript 4.9.5, tech_versions.json: Angular 18-lts_

**[INFO] Integration Boundary**
The vertical action bar is deprecated but still supported until Pattern Library 13.2.0. After the upgrade it must continue to render correctly; any removal would be a breaking change for existing UI screens.
_Sources: Issue acceptance criteria: vertical action bar still being used (deprecated but still possible to use till PL 13.2.0)_


## Architecture Walkthrough

The UVZ system consists of five containers; the front‑end lives in the **UVZ‑Web** container (presentation layer). Within this container the Angular application is the top‑level component that bootstraps the app. It imports the Pattern Library (PL) as a shared UI component library. Key neighboring components are: • HTTP client services that call backend APIs (application layer) • State management via RxJS (presentation layer) • UI wrappers such as ng-bootstrap, ng-select, ag‑grid that sit directly under the Angular component tree. The build pipeline uses Angular CLI 18‑lts, Webpack 5, Karma for unit tests and Playwright for e2e tests. After the upgrade the Angular CLI version will move to the 19 release, Webpack configuration may stay the same, but the npm lockfile will be refreshed with newer package versions. All UI components, including the vertical action bar, will be re‑compiled against Angular 19 and PL 12.6.0.

## Anticipated Questions

**Q: Which Node.js and TypeScript versions are required for Angular 19?**
A: Angular 19 officially supports Node.js 18+ and TypeScript 5.2+. The current project uses TypeScript 4.9.5, so TypeScript must be upgraded. Verify the Node version used in CI/CD and update the engine field in package.json if necessary.

**Q: Are there breaking changes in Angular 19 that could affect existing components?**
A: Angular 19 removes several deprecated APIs (e.g., certain lifecycle hooks, ViewEngine‑related features) and updates RxJS to a newer minor version. Review the Angular upgrade guide for migration steps, especially for any custom directives or the vertical action bar that may rely on deprecated APIs.

**Q: How should the ng-bootstrap patch mentioned in the ticket be handled?**
A: Locate the custom patch applied to ng-bootstrap in the repository (likely in a post‑install script or a fork). Verify whether the upstream ng-bootstrap version compatible with Angular 19 already includes the needed changes; if not, re‑apply the patch to the new version.

**Q: Do we need to adjust the CI/CD pipeline (Angular CLI, Karma, Playwright) after the upgrade?**
A: Yes. The pipeline must install the Angular 19 CLI, update the Karma configuration if any Angular‑specific plugins have changed, and ensure Playwright tests run against the new compiled bundles. Verify that the build step still uses Webpack 5 (still compatible).

**Q: Will the vertical action bar continue to work after the upgrade?**
A: The vertical action bar is deprecated but supported until PL 13.2.0. After upgrading to PL 12.6.0 it should still function, but you must run UI regression tests to confirm no styling or API breakage.


## Linked Tasks

- UVZUSLNVV-5824 (this upgrade task)
- BNUVZ-12529 (analysis comment "how to get to angular 21")