# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a large, browser‑based client application used by internal BNOTK users to access notarisation services. It lives in the presentation container of a five‑container architecture and consists of ~287 UI components that render data from backend services. The task is to move the whole front‑end stack from Angular 18 (LTS) to Angular 19 and to update the shared Pattern Library from 11.3.1 to 12.6.0. This is required now because Angular 18 loses its free security support on 21‑Nov‑2025, leaving the product exposed. Without the upgrade the application would either have to pay for a costly support contract or run on an insecure, unsupported framework.

## Scope Boundary

IN: All Angular front‑end code (presentation layer), the Pattern Library integration, the build pipeline (Angular CLI, Webpack), and the UI‑related npm dependencies listed in the acceptance criteria (Node.js, TypeScript, bnotk/ds‑ng, ng‑bootstrap, ng‑select, ag‑grid). OUT: Backend Java services, database schemas, non‑UI infrastructure, and any components that are not part of the Angular front‑end or the Pattern Library.

## Affected Components

- UVZ UI components (presentation layer)
- Pattern Library integration module (presentation layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 requires TypeScript ≥5.0 and Node.js ≥16. The current stack uses TypeScript 4.9.5 and an unspecified Node version, so these must be upgraded before the framework can be upgraded.
_Sources: tech_versions.json: Angular 18‑lts, tech_versions.json: TypeScript 4.9.5_

**[CAUTION] Dependency Risk**
UI libraries (ng‑bootstrap, ng‑select, ag‑grid) have specific version compatibility matrices with Angular 19. The versions used today are tied to Angular 18; they must be verified and possibly upgraded to versions that support Angular 19.
_Sources: dependencies.json: @angular/* v18‑lts, issue description: ng‑bootstrap (patch required), ng‑select, ag‑grid‑angular, ag‑grid‑community_

**[INFO] Integration Boundary**
The vertical action bar component is deprecated but still used. It remains supported up to Pattern Library 13.2.0, so the upgrade to PL 12.6.0 can keep it, but developers must ensure no leftover code from PL 11.3.1 that is no longer supported is left behind.
_Sources: issue description: vertical action bar still used (deprecated but allowed until PL 13.2.0)_

**[CAUTION] Testing Constraint**
Current test tooling (Karma 6.4.3, Playwright 1.44.1) may need configuration updates to work with Angular 19 and the newer TypeScript compiler. Test suites must be run after the upgrade to catch regressions.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_

**[BLOCKING] Security Boundary**
The primary driver for this upgrade is the loss of free security patches for Angular 18. Upgrading eliminates the security exposure and removes the need for a paid Never‑Ending Support contract.
_Sources: issue description: security support for Angular 18 ends 21.11.2025_


## Architecture Walkthrough

The UVZ system is split into five containers (frontend, backend‑api, authentication, data‑access, infrastructure). The Angular application resides in the frontend container, within the presentation layer comprising ~287 components that consume services from the application layer via REST/GraphQL endpoints. The shared UI component library (Pattern Library bnotk/ds‑ng) is imported into the same layer. Adjacent pieces include:
- Build pipeline: Angular CLI 18‑lts (targeted for upgrade to CLI 19) and Webpack 5.80.0 as the bundler.
- Backend services: unchanged APIs accessed by the UI.
- Testing infrastructure: Karma unit tests and Playwright end‑to‑end tests executed against the compiled bundle.
- Vertical action bar: a deprecated UI component supported up to Pattern Library 13.2.0, present in the presentation layer.
Relevant configuration files such as `package.json` and `angular.json` are located in the frontend container, where version pins for Angular, TypeScript, Node.js, and UI libraries are defined.

## Anticipated Questions

**Q: Which Node.js and TypeScript versions are required for Angular 19?**
A: Angular 19 officially supports Node.js 16 + and TypeScript 5.0 + . The current project uses TypeScript 4.9.5, so both Node and TypeScript will need to be upgraded before the Angular upgrade can succeed.

**Q: Do the UI libraries (ng‑bootstrap, ng‑select, ag‑grid) have compatible releases for Angular 19?**
A: Each of those libraries publishes a compatibility matrix. The versions currently locked to Angular 18 must be checked against their release notes; most have a newer minor/patch that supports Angular 19. The patch for ng‑bootstrap mentioned in the ticket must be applied.

**Q: Will the existing unit and e2e tests still run after the upgrade?**
A: Tests are written with Karma and Playwright. Both tools work with Angular 19, but configuration files may need minor adjustments (e.g., TypeScript compiler options). All tests should be executed after the upgrade to catch regressions.

**Q: Is the vertical action bar going to break after the Pattern Library upgrade?**
A: The vertical action bar is deprecated but remains supported up to Pattern Library 13.2.0. Since the target is PL 12.6.0, it should continue to work, but developers must verify that no leftover code from PL 11.3.1 that is no longer supported remains.

**Q: What is the fallback if we cannot complete the upgrade before the security support deadline?**
A: The fallback is to purchase a Never‑Ending Support contract for Angular 18, which provides paid security patches. This is more expensive and only a temporary solution; the preferred path is to upgrade to Angular 19.


## Linked Tasks

- UVZUSLNVV-5824 (current upgrade ticket)
- BNUVZ-12529 (analysis of how to reach Angular 21 – provides dependency guidance)