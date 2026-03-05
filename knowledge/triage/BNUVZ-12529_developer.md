# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a client‑facing web portal built with Angular (frontend) that consumes backend services written in Java 17. It is used by internal and external users to access business functions. The task is to move the frontend from Angular 18 (which is already deprecated) to Angular 19 and to update the shared Pattern Library to version 12.6.0. This upgrade is required now because Angular 18 will lose free security updates on 21 Nov 2025, leaving the portal exposed. Without the upgrade the system either becomes a security liability or forces the organisation to pay for a special support contract.

## Scope Boundary

IN: • Upgrade Angular core, Angular CLI, RxJS if needed • Update TypeScript and Node.js to versions compatible with Angular 19 • Upgrade Pattern Library to 12.6.0 • Bring forward all listed UI dependencies (ng‑bootstrap, ng‑select, ag‑grid, bnotk/ds‑ng) to versions that support Angular 19 • Keep the vertical action bar functional (it is deprecated but still allowed until PL 13.2.0) • Remove any code, components or styles that belong exclusively to Angular 18/PL 11.3.1 and are not required by the new versions OUT: • Backend Java services, database schema, infrastructure provisioning • Non‑UI modules (domain, application, data‑access layers) • New feature development unrelated to the UI stack • Migration of unrelated third‑party libraries not listed in the acceptance criteria

## Affected Components

- UVZ Frontend (presentation layer)
- Pattern Library Integration (presentation layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 requires TypeScript 5.x and a newer Node.js runtime. The project currently uses TypeScript 4.9.5 (tech_versions.json) and an unspecified Node.js version, so both must be upgraded before the Angular upgrade can succeed.
_Sources: tech_versions.json: TypeScript 4.9.5, tech_versions.json: Angular 18‑lts_

**[CAUTION] Dependency Risk**
UI libraries such as ng‑bootstrap, ng‑select, and ag‑grid have to be at versions that declare compatibility with Angular 19. The issue description explicitly mentions a patch for ng‑bootstrap that must be considered, indicating a potential breakage risk.
_Sources: issue description: ng‑bootstrap (Patch von UVZUSLNVV‑5824 muss berücksichtigt werden), dependencies.json: @angular/* v18‑lts_

**[INFO] Integration Boundary**
The vertical action bar component is deprecated but still supported until Pattern Library 13.2.0. The upgrade must preserve its usage and avoid removal, even though it will be flagged as deprecated in the UI component library.
_Sources: issue acceptance criteria: Vertical action bar is still used (deprecated but possible until PL 13.2.0)_

**[CAUTION] Testing Constraint**
Current test tooling (Karma 6.4.3, Playwright 1.44.1) may not be fully compatible with Angular 19’s build output. Tests will need to be verified and possibly upgraded to newer versions of Karma or switched to a supported test runner.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_


## Architecture Walkthrough

The UVZ system is split into five containers. The Angular UI lives in the **frontend container** (presentation layer, ~287 components). It consumes REST APIs exposed by the **backend container** (Java 17, application & domain layers). The UI imports the shared **Pattern Library** (PL) which provides reusable UI components and styling. During the upgrade you will be working inside the frontend container, specifically the presentation layer components that import @angular/* packages and the PL modules. Neighboring components include:
- **API Service Layer** (Angular services that call backend endpoints) – must continue to work after the framework bump.
- **UI Component Library** (bnotk/ds‑ng, ng‑bootstrap, ng‑select, ag‑grid) – these are direct dependencies that will be upgraded alongside Angular.
- **Build Pipeline** (Webpack, Angular CLI) – resides in the same container and will need to be updated to the CLI version that matches Angular 19.
- **Testing Suite** (Karma, Playwright) – also part of the frontend container and will need verification.
Think of the upgrade as replacing the core Angular version while keeping the surrounding UI component ecosystem and the contract with the backend unchanged.

## Anticipated Questions

**Q: Which Node.js and TypeScript versions are required for Angular 19?**
A: Angular 19 expects Node.js >= 18.x and TypeScript 5.2 (or newer). The current project uses TypeScript 4.9.5, so both Node.js and TypeScript must be upgraded before the Angular packages can be updated.

**Q: Do the current versions of ng‑bootstrap, ng‑select, and ag‑grid support Angular 19?**
A: Only the versions that explicitly declare compatibility with Angular 19 can be used. The issue notes a required patch for ng‑bootstrap, indicating that the present version is not yet compatible. Verify the latest releases of each library and apply the patch or upgrade to a compatible release.

**Q: Will our existing unit and e2e tests still run after the upgrade?**
A: Karma 6.4.3 and Playwright 1.44.1 were released for Angular 18. Angular 19 may need newer Karma adapters or a different test runner configuration. Tests should be executed after the upgrade and any failing tests updated accordingly.

**Q: Can we keep the deprecated vertical action bar?**
A: Yes. The acceptance criteria state that the vertical action bar may remain in use until Pattern Library 13.2.0. Ensure it is not removed during cleanup, but be aware that it will be flagged as deprecated in the UI library.

**Q: Do we need to modify the build pipeline (Webpack, Angular CLI) as part of the upgrade?**
A: Angular 19 ships with a matching Angular CLI version (19.x). The current pipeline uses Angular CLI 18‑lts, so the CLI must be upgraded and any Webpack configuration that references Angular‑specific loaders should be reviewed for compatibility.


## Linked Tasks

- UVZUSLNVV-5824 (this upgrade ticket)
- BNUVZ-12529 (analysis comment "how to get to angular 21")
- UVZUSLNVV-5824 (patch for ng‑bootstrap referenced in the description)