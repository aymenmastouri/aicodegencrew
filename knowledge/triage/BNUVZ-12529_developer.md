# Developer Context: BNUVZ-12529

## Big Picture

The issue lives in the presentation container of the system (the Angular SPA) and touches the UI component library (Pattern Library). It interacts with the backend only through standard REST/GraphQL APIs, so the change is confined to the front‑end layer, the build pipeline (Angular CLI, Webpack) and the CI/CD jobs that compile and test the UI.

## Scope Boundary

IN: Angular application source, Pattern Library, npm dependencies (ng‑bootstrap, ng‑select, ag‑grid, etc.), Angular CLI/Webpack build configuration, unit‑ and integration‑test suites (Karma, Cypress, Playwright). OUT: Java backend services, database schema, domain logic, unrelated micro‑services.

## Classification Assessment

Evidence FOR bug: – The deterministic finder flagged the ticket as a bug (keyword: support, deprecate). – Security‑guard configuration mentions Angular version‑specific behavior. Evidence AGAINST bug: – The description explicitly requests an upgrade to a newer, supported version; no error logs, stack traces, or failing tests are cited. – The need for upgrade is driven by external support policy, not by a malfunction. – All referenced documents (Jira ticket, end‑of‑life page) describe a planned migration, not a defect. → Conclusion: the classification as a bug is weak; the issue is a maintenance task. (Likely NOT a bug — 25%)

## Affected Components

- UVZ Front‑end (Presentation Layer)
- Pattern Library UI Components (Presentation Layer)
- Build & CI Pipeline (Infrastructure Layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 18 reached end‑of‑life for security updates on 21‑Nov‑2025; continuing to run it without paid support would expose the system to unpatched vulnerabilities, making the upgrade mandatory.
_Sources: Issue description: security support for Angular 18 ends 21.11.2025, End‑of‑life reference URLs_

**[CAUTION] Dependency Risk**
Key UI libraries (ng‑bootstrap, ng‑select, ag‑grid) must be upgraded to versions compatible with Angular 19; mismatched versions can cause compile‑time or runtime failures.
_Sources: Acceptance criterion 1 lists required dependency updates, Current dependency list shows all libraries at Angular 18 versions_

**[CAUTION] Testing Constraint**
The current test stack uses Karma, which is deprecated in Angular 19+. Test configuration will need to be migrated to supported runners (e.g., Jest or updated Cypress), otherwise CI will break.
_Sources: Analysis input: Karma 6.4.3 listed as current library, Angular 19 release notes deprecate Karma_

**[CAUTION] Security Boundary**
The Angular guard ActivateIfUserAuthorized is tied to framework internals; a major version bump may alter guard behavior, requiring verification that authorization still works as expected.
_Sources: Security configuration: ActivateIfUserAuthorized (angular_guard)_

**[INFO] Pattern Constraint**
The vertical action bar component is deprecated but still supported up to Pattern Library 13.2.0; the upgrade must retain it without removal to satisfy existing UI contracts.
_Sources: Acceptance criterion 2 mentions continued use of vertical action bar_


## Architecture Notes

The upgrade is confined to the presentation container (Angular SPA) and its supporting libraries. It does not affect domain or data‑access layers, which remain on Java 17/Gradle 8.2.1. The change will ripple through the CI pipeline (build, lint, test) and may require updates to Docker images or node runtime versions. Ensure that any shared contracts (API contracts, authentication guards) remain compatible after the framework bump.