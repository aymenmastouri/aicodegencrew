# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a web‑based application used by internal BNOTK users to access notary‑related services. The front‑end is built with Angular and a proprietary Pattern Library (PL) that provides UI components. This task upgrades the UI stack from Angular 18 / PL 11.3.1 to Angular 19 / PL 12.6.0 so that the product stays within the supported security window and can continue to receive vendor updates. The upgrade is required now because Angular 18’s free security support expires in November 2025; without it the application would be exposed to security risks and would need an expensive support contract. If we do not upgrade, the front‑end will become insecure and eventually non‑functional as browsers and other libraries move forward.

## Scope Boundary

IN: All front‑end source code (TypeScript, HTML, SCSS) in the presentation container, package.json / angular.json, build pipeline (Webpack, Angular CLI), Pattern Library usage, vertical action bar component, and all listed third‑party UI libraries (ng‑bootstrap, ng‑select, ag‑grid, bnotk/ds‑ng). Update Node.js and TypeScript versions required for Angular 19. Verify and adjust unit/e2e tests (Karma, Playwright). OUT: Backend Java services, database schema, infrastructure (servers, CI/CD pipelines unrelated to the front‑end build), non‑UI micro‑services, and any unrelated libraries not listed.

## Affected Components

- HeaderComponent (presentation)
- VerticalActionBarComponent (presentation)
- DataGridComponent (presentation)
- PatternLibraryWrapper (presentation)
- AppModule (presentation)

## Context Boundaries

**[CAUTION] Technology Constraint**
Angular 19 requires TypeScript ≥5.0 and a newer Node.js runtime. The project currently uses TypeScript 4.9.5 and an older Node version, so both must be upgraded before the Angular upgrade can succeed.
_Sources: tech_versions.json: TypeScript 4.9.5, tech_versions.json: Angular 18-lts_

**[BLOCKING] Dependency Risk**
ng‑bootstrap has a custom patch referenced in the ticket; that patch may not be compatible with Angular 19. Compatibility must be verified or the patch adapted, otherwise the UI will break at compile time.
_Sources: Issue description: ng-bootstrap (Patch von UVZUSLNVV-5824 muss berücksichtigt werden)_

**[INFO] Pattern Library Constraint**
Pattern Library 12.6.0 deprecates the vertical action bar but still supports it up to PL 13.2.0. The component can stay, but any usage of removed PL 11.3.1 parts must be eliminated.
_Sources: Issue acceptance criteria: vertical action bar is still being used (deprecated but still possible to use till PL 13.2.0)_

**[BLOCKING] Security Boundary**
Security support for Angular 18 ends 21 Nov 2025. Continuing to run the current version would leave the application without security patches, violating internal security policies.
_Sources: Issue description: support for security updates ended on 21.11.2025 for Angular 18_

**[CAUTION] Testing Constraint**
The test stack (Karma 6.4.3, Playwright 1.44.1) was aligned with Angular 18. Some test utilities may need updates to work with Angular 19 and the new TypeScript version.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_


## Architecture Walkthrough

The UVZ system consists of 5 containers; the front‑end lives in the **frontend‑webapp** container (presentation layer). Within this container, Angular modules and components form the bulk of the 287 presentation components. The upgrade touches the **AppModule** (root module), all UI components (e.g., HeaderComponent, VerticalActionBarComponent, DataGridComponent), and the **PatternLibraryWrapper** that bridges the proprietary Pattern Library. These components call services in the **application** layer (e.g., AuthService, DataService) via Angular's dependency injection, which in turn communicate with backend APIs (infrastructure layer). The vertical action bar is a UI component that currently depends on PL 11.3.1 styles; after the upgrade it will depend on PL 12.6.0 styles but remains functional until PL 13.2.0. All third‑party UI libraries (ng‑bootstrap, ng‑select, ag‑grid, bnotk/ds‑ng) are imported as npm packages and are wired into the Angular modules. The build pipeline (Webpack 5.80.0, Angular CLI 18‑lts) will be switched to the Angular 19 CLI, which updates the Webpack configuration automatically.

## Anticipated Questions

**Q: Which Node.js and TypeScript versions are required for Angular 19?**
A: Angular 19 officially supports Node 16.14+ (or newer) and TypeScript 5.0+. The project currently uses an older Node version and TypeScript 4.9.5, so both must be upgraded before the Angular upgrade.

**Q: Will the vertical action bar continue to work after the upgrade?**
A: Yes. The vertical action bar is deprecated but still supported up to Pattern Library 13.2.0. After moving to PL 12.6.0 it will compile, but you should verify that no PL 11.3.1‑specific CSS classes remain.

**Q: What do we need to do about the custom ng‑bootstrap patch?**
A: The patch referenced in UVZUSLNVV‑5824 must be reviewed for compatibility with Angular 19. If the patch touches Angular internals that changed, it will need to be updated or replaced with an official Angular 19‑compatible version.

**Q: Are there breaking changes in Pattern Library 12.6.0 that affect our UI?**
A: PL 12.6.0 introduces several component API changes and removes some legacy styles. All usages of PL 11.3.1 components must be audited; only those still present in PL 12.6.0 may remain. The vertical action bar is an exception until PL 13.2.0.

**Q: Do we need to update our test configuration?**
A: Karma and Playwright versions are compatible with Angular 18 but may need minor configuration tweaks for Angular 19 (e.g., updated tsconfig for TypeScript 5). Ensure the test runner versions are still supported after the TypeScript bump.


## Linked Tasks

- BNUVZ-12529 (analysis comment "how to get to angular 21")
- UVZUSLNVV-5824 (current ticket)