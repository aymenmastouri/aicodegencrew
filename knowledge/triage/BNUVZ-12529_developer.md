# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a front‑end web portal built with Angular that serves internal (or external) users of the BNOTK ecosystem. The UI lives in the presentation container and consumes the BNOTK Design System (Pattern Library). This task upgrades the UI framework from Angular 18 to Angular 19 and the design system from PL 11.3.1 to PL 12.6.0. The upgrade is required now because Angular 18 loses security support on 21 Nov 2025, leaving the portal exposed unless we move to a supported version. Not upgrading would either force us to buy expensive extended support or expose the system to unpatched vulnerabilities.

## Scope Boundary

IN: • Upgrade Angular core, Angular CLI and related @angular/* packages to v19.
    • Update Node.js and TypeScript to versions compatible with Angular 19.
    • Upgrade Pattern Library (bnotk/ds‑ng) to 12.6.0.
    • Update all listed third‑party UI libraries (ng‑bootstrap, ng‑select, ag‑grid‑angular, ag‑grid‑community) to versions that support Angular 19.
    • The vertical action bar (deprecated) is expected to remain functional after the PL upgrade.
    • Code, components, or styles exclusive to Angular 18 / PL 11.3.1 will be identified and excluded from the upgraded build.
OUT: • Backend Java services, domain logic, data‑access layer, and infrastructure containers.
    • Non‑UI related libraries (e.g., Playwright, edge‑js, log‑timestamp).
    • Business logic tests that do not touch the UI layer (they remain untouched unless they fail after the upgrade).

## Affected Components

- UVZ Frontend (presentation layer)
- Pattern Library Integration Component (presentation layer)

## Context Boundaries

**[CAUTION] Technology Constraint**
Angular 19 requires TypeScript ≥5.0 and Node.js ≥16. The current stack lists TypeScript 4.9.5 and an unspecified Node version, so the upgrade must include a compatible TypeScript and Node release.
_Sources: tech_versions.json: TypeScript 4.9.5, tech_versions.json: Angular 18-lts_

**[BLOCKING] Dependency Risk**
ng‑bootstrap has a custom patch referenced in the ticket; its current version may not be compatible with Angular 19. The patch must be re‑applied or a newer compatible version must be used.
_Sources: Issue description: ng-bootstrap (Patch von UVZUSLNVV-5824 muss berücksichtigt werden)_

**[CAUTION] Dependency Risk**
Third‑party UI libraries (ng‑select, ag‑grid‑angular, ag‑grid‑community) often have major version bumps aligned with Angular major releases. Their current versions are tied to Angular 18 and may break under Angular 19.
_Sources: Issue description: list of dependencies to update_

**[BLOCKING] Security Boundary**
Security support for Angular 18 ends on 21 Nov 2025. Continuing to run the current version would leave the application without official security patches, violating compliance and increasing risk.
_Sources: Issue description: support for security updates ended on 21.11.2025 for Angular 18_

**[INFO] Pattern Library Dependency**
Pattern Library 12.6.0 deprecates some components but still provides the vertical action bar until PL 13.2.0. The upgrade must ensure that the vertical action bar remains functional and that no removed components are still referenced.
_Sources: Issue description: vertical action bar is still used (deprecated but allowed until PL 13.2.0)_

**[CAUTION] Testing Constraint**
Current test tooling (Karma 6.4.3, Webpack 5.80.0) may need configuration updates to work with Angular 19 and the newer CLI. Tests should be run after the upgrade to catch regressions.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Webpack 5.80.0_


## Architecture Walkthrough

The UVZ system is split into 5 containers. The Angular front‑end lives in the **UI container** (presentation layer, ~287 components). Within this container, the main entry point is the Angular application module, which imports the **Pattern Library module (bnotk/ds‑ng)** and various UI component libraries (ng‑bootstrap, ng‑select, ag‑grid). The vertical action bar component is a UI widget that sits in the shared layout module. Upgrading Angular and the Pattern Library touches the core Angular module, the shared layout module, and all feature modules that depend on the UI libraries. Downstream, the presentation layer communicates with the application layer via REST/GraphQL endpoints (not affected by this task). Upstream, the data‑access and domain layers remain unchanged.

## Anticipated Questions

**Q: Which Node.js and TypeScript versions do we need for Angular 19?**
A: Angular 19 officially supports Node.js ≥16.14 and TypeScript ≥5.0. The project will need to bump both Node and TypeScript to meet these minima before the Angular upgrade can succeed.

**Q: Do we have to modify the CI/CD pipeline (Webpack, Angular CLI) for the new versions?**
A: Yes. The Angular CLI will be upgraded from 18‑lts to the 19 release, which may require adjustments to the Webpack configuration and build scripts. Existing build tooling (Webpack 5.80.0) is generally compatible, but the pipeline should be validated after the upgrade.

**Q: Will the vertical action bar still work after moving to Pattern Library 12.6.0?**
A: The vertical action bar is deprecated but remains supported up to PL 13.2.0, so it should continue to work after the upgrade. However, the component must be tested to ensure no breaking changes were introduced in PL 12.6.0.

**Q: Are there known breaking changes in ag‑grid‑angular for Angular 19?**
A: ag‑grid‑angular releases are usually aligned with Angular major versions. Verify the latest ag‑grid‑angular version that declares compatibility with Angular 19 and update accordingly. Check the release notes for any API changes that affect existing grid configurations.

**Q: Do we need to update unit and e2e tests now?**
A: All existing Karma/Jasmine unit tests and Playwright e2e tests should be executed after the upgrade. If they fail due to API changes in Angular or the UI libraries, the tests will need to be updated, but the primary scope is the framework upgrade itself.


## Linked Tasks

- UVZUSLNVV-5824 (this ticket)
- BNUVZ-12529 (analysis comment "how to get to angular 21")