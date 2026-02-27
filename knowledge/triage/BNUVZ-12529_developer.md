# Developer Context: BNUVZ-12529

## Big Picture

The system consists of five containers with a clear separation between presentation (Angular SPA), application, domain, data‑access and infrastructure layers. The upgrade touches the presentation container and the shared Pattern Library used across UI components. It interacts with backend REST services (e.g., /action/{id}) but does not change backend business logic.

## Scope Boundary

IN: All front‑end source code, Angular configuration, Pattern Library assets, npm dependencies listed in the acceptance criteria (Node.js, TypeScript, bnotk/ds‑ng, ng‑bootstrap, ng‑select, ag‑grid, etc.), build tooling (Angular CLI, Webpack), test suites (Karma, Cypress) and security guards. OUT: Backend Java services, database schemas, infrastructure containers, and any UI components that are already deprecated and removed by the upgrade.

## Affected Components

- Action UI (presentation layer)
- Vertical Action Bar component (presentation layer)
- Pattern Library components (presentation layer)
- ng‑bootstrap integration (presentation layer)
- ag‑grid integration (presentation layer)

## Context Boundaries

**[CAUTION] Technology Constraint**
Angular 19 requires a compatible Node.js version and a minimum TypeScript version. The current stack lists TypeScript 4.9.5 and an unspecified Node version, so compatibility must be verified before the upgrade.
_Sources: tech_versions.json: Angular 18.2.13, tech_versions.json: TypeScript 4.9.5_

**[BLOCKING] Dependency Risk**
Key UI libraries (ng‑bootstrap, ng‑select, ag‑grid) have specific major‑version compatibility matrices with Angular. Their current versions are tied to Angular 18 and must be upgraded to versions that support Angular 19, otherwise the application will fail to compile or run.
_Sources: issue_context: ng-bootstrap, issue_context: ng-select, issue_context: ag-grid-angular_

**[CAUTION] Pattern Constraint**
Pattern Library 12.6.0 deprecates some components but still supports the vertical action bar until PL 13.2.0. The upgrade must ensure the vertical action bar continues to function and that no obsolete PL 11 components remain.
_Sources: issue_context: Vertical action bar, issue_context: Pattern Library 12.6.0_

**[BLOCKING] Security Boundary**
The Angular guard ActivateIfUserAuthorized is critical for authorisation checks. Angular 19 may introduce breaking changes to guard APIs; the guard must be retained and tested to avoid security regressions.
_Sources: security_details.json: ActivateIfUserAuthorized (angular_guard)_

**[CAUTION] Testing Constraint**
Karma 6.4.3, used for unit tests, is deprecated in Angular 19+. Continuing to rely on it could lead to failing test pipelines; a migration to a supported test runner (e.g., Jest) may be required.
_Sources: tech_versions.json: Karma 6.4.3_

**[INFO] Integration Boundary**
Front‑end endpoints such as /action/{id} remain unchanged, but the upgraded UI must continue to call them with the same contract. Any change in request/response handling introduced by Angular 19 must be validated against these backend services.
_Sources: deterministic_findings: entry_points /action/{id}_


## Architecture Notes

The upgrade is confined to the presentation container and its shared Pattern Library. It must respect the existing layered architecture, keep the security guard intact, and avoid breaking the contract with backend REST services. Dependency versions and test framework compatibility are the main risk areas.