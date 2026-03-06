# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a large Angular‑based front‑end (the presentation container) that delivers the user interface for the UVZ business application. Internal users (employees, partners) interact with it to perform domain‑specific tasks. The task is to upgrade the UI framework from Angular 18 LTS to Angular 19 LTS and to move the UI component library from Pattern Library 11.3.1 to 12.6.0. This upgrade is required now because Angular 18 loses its free security support on 21 Nov 2025, leaving the product exposed. Upgrading now prevents a security gap, aligns the UI stack with the vendor’s supported versions, and prepares the codebase for future upgrades (e.g., Angular 20/21). If the upgrade is postponed, the system will either have to pay for expensive support contracts or run with known vulnerabilities.

## Scope Boundary

IN: All front‑end code in the ‘frontend’ container – Angular core packages, Angular CLI, TypeScript configuration, the bnotk/ds‑ng pattern library integration, ng‑bootstrap (including the custom patch referenced in this ticket), ng‑select (and its option‑highlight sub‑module), ag‑grid‑angular and ag‑grid‑community, the vertical action bar component, and any build scripts (Webpack, Karma, Playwright) that depend on these versions. OUT: Backend Java services, database schemas, infrastructure (servers, CI pipelines) that are not directly tied to the Angular version, unrelated UI containers, and any feature work not mentioned in the acceptance criteria.

## Affected Components

- UVZ Web UI (presentation)
- Pattern Library Integration (presentation)
- Vertical Action Bar Component (presentation)
- Build & Test Scripts (infrastructure)

## Context Boundaries

**[CAUTION] Technology Constraint**
Angular 19 requires a newer Node.js and TypeScript version than the current stack (Node.js and TypeScript are listed as upgrade items). The existing TypeScript 4.9.5 and Node.js version must be verified for compatibility before the upgrade can succeed.
_Sources: tech_versions.json: Angular 18-lts, tech_versions.json: TypeScript 4.9.5_

**[BLOCKING] Dependency Risk**
The ng‑bootstrap library has a custom patch that was created for Angular 18. That patch must be re‑evaluated or re‑implemented for Angular 19, otherwise the UI may break.
_Sources: issue_description: ng-bootstrap (Patch von UVZUSLNVV-5824 muss berücksichtigt werden)_

**[INFO] Pattern Library Version**
Pattern Library 12.6.0 deprecates the vertical action bar after PL 13.2.0, but the acceptance criteria require the bar to stay functional until then. The upgrade must keep the component working and ensure no hidden breakage.
_Sources: issue_description: Vertical action bar is still being used (deprecated but still possible to use till PL 13.2.0)_

**[BLOCKING] Security Boundary**
Angular 18 security support ends 21 Nov 2025. Continuing to run without a paid support contract would leave the application exposed to unpatched vulnerabilities.
_Sources: issue_description: Support for security updates ended on 21.11.2025 for Angular 18_


## Architecture Walkthrough

The UVZ system consists of five containers; the front‑end container hosts the Angular SPA. Within that container the presentation layer contains ~287 components, including the main AppComponent, routing modules, UI widgets, and the Pattern Library wrapper. The Angular core packages (@angular/*) sit at the base of this layer and are consumed by all UI components. The Pattern Library (bnotk/ds‑ng) is a separate library that provides styled components such as the vertical action bar. Adjacent to the presentation layer are the application‑level services that call backend APIs (REST) hosted in the backend container. Build tooling (Webpack, Angular CLI) and test runners (Karma, Playwright) are part of the infrastructure sub‑layer but live inside the same container. The upgrade work will replace the Angular core packages, update the CLI, bump TypeScript, and swap the Pattern Library version, while ensuring the vertical action bar component (still used) continues to function. All other containers (backend, data‑access, domain) remain untouched.

## Anticipated Questions

**Q: Which Node.js version do we need for Angular 19?**
A: Angular 19 LTS officially supports Node.js 18.x and newer. Verify the current Node.js version used in the CI pipeline and bump it if it is older than 18.x before running the upgrade.

**Q: Are there breaking API changes in Angular 19 that could affect our existing code (e.g., the vertical action bar)?**
A: Angular 19 deprecates several APIs that were still present in 18, but the vertical action bar is only deprecated in the Pattern Library, not Angular itself. Review the Angular 19 changelog for removed APIs (e.g., ViewEngine removal) and run the Angular migration schematic which will flag any usage that needs adjustment.

**Q: Do we need to update our test setup (Karma, Playwright) as part of the upgrade?**
A: Yes. Both Karma and Playwright have peer‑dependency ranges that may require updates to work with Angular 19 and the newer TypeScript version. Check the latest compatible versions and update the configuration files accordingly.

**Q: What is the status of the custom ng‑bootstrap patch referenced in the ticket?**
A: The patch was created for Angular 18. It must be reviewed to see if it still applies to Angular 19's component APIs. If not, a new patch or an upstream upgrade of ng‑bootstrap may be required.

**Q: Can we postpone removing the vertical action bar until after the upgrade to PL 13.2.0?**
A: Yes. The acceptance criteria explicitly allow the bar to remain until PL 13.2.0, so it can stay in place after the upgrade to PL 12.6.0. However, ensure that no new deprecations in Angular 19 affect its rendering.


## Linked Tasks

- UVZUSLNVV-5824 (this upgrade ticket)
- BNUVZ-12529 (analysis on how to get to Angular 21)