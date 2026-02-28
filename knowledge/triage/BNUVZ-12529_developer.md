# Developer Context: BNUVZ-12529

## Big Picture

UVZ is an internal web application built with Angular that delivers business‑critical functionality to Bnotk’s users (e.g., staff, partners). The UI is assembled from the shared Design System (Pattern Library) and a collection of reusable Angular components. This task upgrades the front‑end framework from Angular 18 to Angular 19 and updates the Design System from PL 11.3.1 to 12.6.0. The upgrade is required now because Angular 18 loses its free security updates in November 2025, exposing the product to security risk and potential compliance violations. Without the upgrade, the application would either have to pay for a never‑ending support contract or operate with known vulnerabilities.

## Scope Boundary

IN: All Angular source code (presentation layer), the Pattern Library integration, the vertical action bar component, package.json / npm dependency list, Node.js and TypeScript version constraints, build tooling (Angular CLI, Webpack), and any test configuration that depends on Angular (Karma, Playwright). OUT: Backend Java services, database schemas, infrastructure provisioning, CI/CD pipeline scripts that are unrelated to the front‑end build, and any non‑Angular libraries that are not listed in the acceptance criteria.

## Affected Components

- Angular presentation components (presentation layer)
- Pattern Library integration components (presentation layer)
- Vertical action bar component (presentation layer)

## Context Boundaries

**[CAUTION] Technology Constraint**
Angular 19 requires Node.js ≥ 18 and TypeScript ≥ 5.2. The current stack (Node version not listed, TypeScript 4.9.5) must be upgraded before the framework can be upgraded, otherwise the build will fail.
_Sources: tech_versions.json: TypeScript 4.9.5, tech_versions.json: Angular 18-lts_

**[BLOCKING] Dependency Risk**
All listed runtime dependencies (ng-bootstrap, ng-select, ag‑grid, ds‑ng) have versions that are tied to Angular 18. Their Angular 19 compatible versions must be identified and any required patches (e.g., the ng‑bootstrap patch referenced in the ticket) applied, otherwise runtime errors or compile‑time incompatibilities will occur.
_Sources: dependencies.json: @angular/* v18-lts, issue description: ng-bootstrap (Patch muss berücksichtigt werden)_

**[INFO] Testing Constraint**
Karma 6.4.3 and Playwright 1.44.1 were released for Angular 18. Some test utilities (e.g., Angular testing utilities) may need updates to work with Angular 19, so test suites should be verified after the upgrade.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_

**[CAUTION] Pattern Constraint**
Pattern Library 12.6.0 introduces changes to component APIs and deprecates the vertical action bar after PL 13.2.0. The current UI must continue to use the vertical action bar, which is still supported in PL 12.6.0, but any future removal must be planned.
_Sources: issue description: vertical action bar is still being used (deprecated but still possible to use till PL 13.2.0)_


## Architecture Walkthrough

The UVZ front‑end lives in the **frontend-web** container. Within that container the code is organized into the **presentation layer** (≈287 components) which consumes services from the **application layer** via HTTP APIs. The Angular app imports the **Pattern Library** (design system) as a shared UI component library. Key neighbours are:
- **Application layer services** (REST endpoints) that provide data to the UI.
- **Pattern Library (PL 11.3.1 → 12.6.0)** which supplies UI widgets, including the vertical action bar.
- **Shared utility libraries** (ds‑ng, ng‑bootstrap, ng‑select, ag‑grid) that are bundled by Webpack.
- **Testing harness** (Karma + Playwright) that runs in the same container.
The upgrade will touch every Angular module, the package.json dependency graph, the Webpack configuration, and the CI build steps that compile the app. All other containers (backend, infra) remain untouched.

## Anticipated Questions

**Q: Which Node.js and TypeScript versions are required for Angular 19?**
A: Angular 19 officially supports Node.js ≥ 18 and TypeScript ≥ 5.2. The current project uses an unspecified Node version and TypeScript 4.9.5, so both must be upgraded before the Angular upgrade can succeed.

**Q: Are there breaking changes in Angular 19 that affect our existing code (e.g., the vertical action bar)?**
A: Angular 19 itself does not remove the vertical action bar, but the Pattern Library 12.6.0 deprecates it after PL 13.2.0. The component will continue to work for now, but any usage should be flagged for future refactoring.

**Q: Do we need to update our test setup (Karma, Playwright) as part of the upgrade?**
A: Yes. The Angular testing utilities bundled with Karma and the Playwright configuration were released for Angular 18. After moving to Angular 19, verify that the test runners compile and run; update any Angular‑specific test helpers if newer versions are required.

**Q: What is the required action for the ng‑bootstrap patch mentioned in the ticket?**
A: The ticket notes that a specific patch for ng‑bootstrap must be considered. Locate the patch (likely a PR or fork) referenced in the UVZUSLNVV‑5824 comment, ensure it is compatible with the ng‑bootstrap version that supports Angular 19, and apply it before the final build.

**Q: Will the backend APIs need any changes because of the front‑end upgrade?**
A: No backend changes are listed in the acceptance criteria. The front‑end continues to call the same REST endpoints; however, after the upgrade run integration tests to confirm that request/response contracts remain intact.


## Linked Tasks

- UVZUSLNVV-5824 (this upgrade task)
- BNUVZ-12529 (analysis comment "how to get to angular 21")