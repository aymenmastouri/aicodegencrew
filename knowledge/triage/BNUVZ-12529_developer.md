# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a Bnotk‑owned front‑end application that provides a user interface for internal/external users (e.g., public service staff). It lives in the presentation container of the overall system and is built with Angular, consuming the shared Pattern Library (PL) for UI components. The task is to move the UI stack from Angular 18 / PL 11.3.1 to Angular 19 / PL 12.6.0. This is required now because Angular 18 loses free security updates in November 2025, and the organization wants to stay on a supported stack without paying for extended support. Not upgrading would leave the UI exposed to security vulnerabilities and could force a costly support contract.

## Scope Boundary

IN: • Upgrade Angular core, CLI and related Angular packages to v19. • Upgrade Pattern Library to 12.6.0. • Update all listed runtime dependencies (node.js, TypeScript, bnotk/ds‑ng, ng‑bootstrap with its patch, ng‑select/ng‑option‑highlight, ng‑select, ag‑grid‑angular, ag‑grid‑community). • Adjust code for deprecations (e.g., vertical action bar) and remove any leftover Angular 18 / PL 11.3.1 artifacts that are not required by the new versions. • Run the full UI test suite (Karma, Playwright) to verify behaviour.
OUT: • Any backend Java services, database schema, infrastructure provisioning, CI/CD pipeline scripts unrelated to the UI build, and libraries not listed above. • Migration to Angular 20 or later (planned for a future ticket).

## Affected Components

- AppModule (presentation)
- SharedModule (presentation)
- UI components from Pattern Library 11.3.1 (presentation)
- VerticalActionBarComponent (presentation)
- ng-bootstrap integration (presentation)
- ag-grid wrappers (presentation)

## Context Boundaries

**[CAUTION] Technology Constraint**
Angular 19 requires a newer TypeScript (≥5.0) and a recent Node.js version (≥18). The current stack uses TypeScript 4.9.5 and an unspecified Node version, so the upgrade will force a TypeScript and possibly a Node upgrade before the Angular upgrade can succeed.
_Sources: tech_versions.json: TypeScript 4.9.5, tech_versions.json: Angular 18‑lts_

**[BLOCKING] Dependency Risk**
ng‑bootstrap, ng‑select and ag‑grid versions listed are built for Angular 18. Their peer‑dependency ranges may not include Angular 19, so they must be upgraded to versions that explicitly support Angular 19 or patched accordingly. Failure to do so will cause compile‑time or runtime errors.
_Sources: issue description: ng‑bootstrap (Patch muss berücksichtigt werden)_

**[INFO] Integration Boundary**
The vertical action bar component is deprecated but still supported up to Pattern Library 13.2.0. After the upgrade it must continue to render correctly; any removal would break existing UI screens that rely on it.
_Sources: issue description: Vertical action bar still used (deprecated)_

**[CAUTION] Testing Constraint**
Karma (6.4.3) and Playwright (1.44.1) test suites are tied to Angular 18 tooling. Angular 19 may introduce breaking changes in test harnesses, so the test configuration and possibly test code will need verification after the upgrade.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_

**[BLOCKING] Security Boundary**
Staying on Angular 18 after 21‑Nov‑2025 would mean no free security patches, exposing the UI to known vulnerabilities. The upgrade directly mitigates this risk.
_Sources: issue description: Security support for Angular 18 ends 21.11.2025_


## Architecture Walkthrough

The UVZ front‑end lives in the **Presentation Container** (one of the five system containers). Within this container the Angular application occupies the **presentation layer** (≈287 components). Core entry points are the `AppModule` and the routing module. The UI components consume the **Pattern Library** (currently version 11.3.1) which provides shared widgets such as buttons, forms, and the vertical action bar. Adjacent layers are the **application layer** (services that call backend APIs) and the **infrastructure layer** (build tooling: Webpack, Angular CLI). The upgrade will touch the following path: `frontend/presentation/angular-app` → update `package.json` → run `ng update` → rebuild with Webpack → redeploy. All components that import `@angular/*` packages, the PL components, and any custom wrappers around `ng-bootstrap`, `ng-select`, and `ag-grid` are the immediate neighbors that may need code adjustments.

## Anticipated Questions

**Q: Which Node.js and TypeScript versions do I need for Angular 19?**
A: Angular 19 officially supports Node 18 LTS (or newer) and TypeScript 5.2+. The current project uses TypeScript 4.9.5, so you will need to bump TypeScript and verify the Node version used in the CI pipeline.

**Q: Do the listed third‑party libraries have Angular 19 compatible releases?**
A: Check the npm release notes for each library. ng‑bootstrap, ng‑select, and ag‑grid have released versions that declare peer dependency `@angular/core >=19`. Use those versions or apply the existing patch for ng‑bootstrap if it already supports Angular 19.

**Q: Will the vertical action bar continue to work after the upgrade?**
A: Yes, it is still supported up to Pattern Library 13.2.0. After upgrading to PL 12.6.0 you must run the UI tests that cover the vertical action bar to confirm no regressions.

**Q: What impact does this have on our automated tests?**
A: Karma and Playwright test configurations may need updates because Angular 19 changes the test harness API. After the upgrade run the full test suite; fix any failing specs or configuration errors before considering the work complete.

**Q: Is there any risk of breaking backend API contracts?**
A: No. The upgrade only touches the front‑end stack. Backend contracts remain unchanged, but ensure that any generated HTTP clients (e.g., via OpenAPI) are re‑generated if the Angular HttpClient version changes its typings.


## Linked Tasks

- UVZUSLNVV-5824 (this ticket)
- BNUVZ-12529 (analysis comment "how to get to angular 21")