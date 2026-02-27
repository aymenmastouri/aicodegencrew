# Developer Context: BNUVZ-12529

## Big Picture

The upgrade touches the presentation container of the system (the Angular SPA) which sits on top of the backend REST services (e.g., ActionRestService). It involves the UI component library (Pattern Library), the build pipeline (Angular CLI, Webpack), and the test harness (Karma/Cypress). Security is enforced by an Angular guard (ActivateIfUserAuthorized) that must continue to work after the upgrade. The vertical action bar is a deprecated UI pattern that remains supported until Pattern Library 13.2.0.

## Scope Boundary

IN: All front‑end Angular code, Angular CLI configuration, Node.js/TypeScript versions, UI libraries (ng‑bootstrap, ng‑select, ag‑grid), Pattern Library 12.6.0, test suites (Karma, Cypress), and the Angular guard. OUT: Backend Java services, database schema, infrastructure provisioning, and any unrelated backend modules.

## Affected Components

- UVZ Frontend Application (presentation layer)
- Pattern Library UI components (presentation layer)
- Vertical Action Bar component (presentation layer)
- Action API (application layer – /action/{type} endpoint)
- Angular Guard ActivateIfUserAuthorized (security layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 requires a newer Node.js and TypeScript version than currently used (Node.js unspecified, TypeScript 4.9.5). The build tools (Angular CLI 18.x, Webpack 5.80.0) must be upgraded, otherwise the application will not compile.
_Sources: tech_versions.json: Angular 18.2.13, tech_versions.json: Angular CLI 18.2.19, tech_versions.json: TypeScript 4.9.5_

**[CAUTION] Dependency Risk**
Key UI dependencies (ng‑bootstrap, ng‑select, ag‑grid‑angular, ag‑grid‑community) may not yet have compatible releases for Angular 19, requiring version checks or patches.
_Sources: issue description: ng-bootstrap (patch required), issue description: ng-select, ag-grid-angular, ag-grid-community_

**[BLOCKING] Security Boundary**
The ActivateIfUserAuthorized Angular guard must remain functional after the framework upgrade; changes in Angular's router or guard APIs could break authorization checks.
_Sources: security_details.json: ActivateIfUserAuthorized (angular_guard)_

**[CAUTION] Testing Constraint**
The current test setup uses Karma 6.4.3, which is deprecated in Angular 19 and may need to be replaced or upgraded to stay compatible with the new build pipeline.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Cypress 14.0.3_

**[CAUTION] Integration Boundary**
Front‑end components interact with backend endpoints such as /action/{type}. Any change in request/response payloads caused by the upgrade must be verified to keep the backend ActionRestService stable.
_Sources: deterministic findings: entry_points component /action/{type}, deterministic findings: backend file ActionRestService.java_


## Architecture Notes

The system follows a layered architecture with a distinct presentation container (Angular SPA) that consumes REST services from the application layer. The upgrade stays within the presentation container but touches cross‑cutting concerns like security guards and test infrastructure. The vertical action bar is a deprecated UI pattern that remains supported until Pattern Library 13.2.0, so it must not be removed during this upgrade. Compatibility of third‑party UI libraries with Angular 19 is a known risk area.