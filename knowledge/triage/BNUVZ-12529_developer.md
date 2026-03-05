# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a client‑facing web application built with Angular. It is used by internal and external users to perform domain‑specific tasks (e.g., notarisation services). The front‑end lives in the **presentation container** and consumes backend APIs built in Java 17. This task upgrades the UI framework from Angular 18 to Angular 19 and updates the shared Pattern Library to version 12.6.0. The upgrade is required now because Angular 18 loses security support in November 2025, and the product must stay within the supported lifecycle to avoid security exposure and costly vendor support contracts.

## Scope Boundary

IN: All Angular source code, package.json, Angular CLI configuration, webpack build files, UI component library (Pattern Library) version, and the listed third‑party dependencies (node.js, TypeScript, bnotk/ds-ng, ng‑bootstrap, ng‑select, ag‑grid). Verify that the vertical action bar continues to work after the upgrade. OUT: Backend Java services, database schemas, CI/CD pipeline scripts that are not Angular‑specific, infrastructure provisioning, and any unrelated front‑end modules that are not part of UVZ.

## Affected Components

- UVZ Front‑end (presentation layer)
- Pattern Library integration (presentation layer)
- Vertical Action Bar component (presentation layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 requires TypeScript 5.x and Node >= 18. The current stack (TypeScript 4.9.5, unknown Node version) must be upgraded, otherwise the build will fail or runtime errors will appear.
_Sources: tech_versions.json: Angular 18‑lts, tech_versions.json: TypeScript 4.9.5_

**[CAUTION] Dependency Risk**
Third‑party UI libraries (ng‑bootstrap, ng‑select, ag‑grid) have specific compatibility matrices with Angular 19. The versions used today are tied to Angular 18; they must be upgraded to versions that declare Angular 19 support, otherwise compilation or runtime errors will occur.
_Sources: issue description: ng‑bootstrap (patch), ng‑select, ag‑grid‑angular, ag‑grid‑community_

**[INFO] Integration Boundary**
The vertical action bar is deprecated but still supported up to Pattern Library 13.2.0. The upgrade to PL 12.6.0 must keep this component functional; removal is out of scope for now.
_Sources: issue description: vertical action bar still used (deprecated but allowed until PL 13.2.0)_

**[BLOCKING] Security Boundary**
Security patches for Angular stop on 21 Nov 2025. Staying on Angular 18 would leave the front‑end unpatched, violating the organization’s security policy.
_Sources: issue description: support for security updates ended on 21.11.2025 for Angular 18_

**[CAUTION] Testing Constraint**
Current test stack (Karma 6.4.3, Playwright 1.44.1) may need updates to work with Angular 19 and newer TypeScript. Tests must be re‑run after the upgrade to ensure no regressions.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_


## Architecture Walkthrough

The UVZ system consists of 5 containers. The front‑end lives in the **Web‑UI container** (presentation layer, ~287 components). Within this container, the Angular application is the core component, pulling UI widgets from the **Pattern Library** (shared UI component library). The vertical action bar is a UI widget that communicates with the application via internal services. The front‑end talks to the **Backend‑API container** (application layer, Java 17) over HTTP. Upgrading Angular touches the Angular core component, the build pipeline (Angular CLI, Webpack), and all UI‑library dependencies. All other containers (backend, infra) remain untouched.

## Anticipated Questions

**Q: Which Node and TypeScript versions are required for Angular 19?**
A: Angular 19 officially supports Node >= 18 and TypeScript 5.x. The current project uses TypeScript 4.9.5, so both Node and TypeScript must be upgraded before the Angular packages can be updated.

**Q: Do the listed third‑party libraries have Angular 19 compatible releases?**
A: Each library (ng‑bootstrap, ng‑select, ag‑grid) publishes a compatibility matrix. The upgrade will need to select the latest versions that declare support for Angular 19. The patch for ng‑bootstrap mentioned in the ticket must be merged into the new version.

**Q: Will the vertical action bar still work after the upgrade?**
A: Yes, it is deprecated but remains supported up to Pattern Library 13.2.0. The upgrade to PL 12.6.0 stays within that range, so the component should continue to function, but functional verification is required.

**Q: Are there any changes needed for the test suite?**
A: Karma and Playwright versions may need minor updates to be compatible with the newer Angular compiler. After the upgrade, all front‑end tests should be executed to catch regressions.

**Q: What is the fallback if the upgrade cannot be completed in time?**
A: The only fallback is to purchase the vendor’s "Never‑Ending Support" for Angular 18, which provides security patches at additional cost, but this does not address the long‑term obsolescence.


## Linked Tasks

- UVZUSLNVV-5824 (this ticket)
- BNUVZ-12529 (analysis comment "how to get to angular 21")