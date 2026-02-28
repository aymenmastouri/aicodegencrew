# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a client‑facing web portal built with Angular and the BNOTK design system (Pattern Library). It is used by internal and external users to perform business processes. The front‑end lives in the *presentation* container of a multi‑container architecture (Java‑based backend, Angular front‑end, etc.). This task upgrades the front‑end framework from Angular 18 to Angular 19 and the design system from PL 11.3.1 to PL 12.6.0. The upgrade is required now because free security updates for Angular 18 stop on 21 Nov 2025, and the business wants to avoid paying for extended support while keeping the UI modern and secure. If the upgrade is not done, the product will become vulnerable and may breach security policies.

## Scope Boundary

IN: • Upgrade Angular core, CLI, and all @angular/* packages to v19. • Upgrade Pattern Library (bnotk/ds-ng) to 12.6.0. • Update Node.js, TypeScript, and related build tools to versions required by Angular 19. • Update dependent UI libraries (ng‑bootstrap, ng‑select, ag‑grid) to versions compatible with Angular 19, applying the patch mentioned in the ticket. • Verify the vertical action bar continues to work (still supported until PL 13.2.0). • Run and, if needed, adapt unit‑test (Karma) and e2e‑test (Playwright) suites. OUT: • Any backend Java services, database schemas, or infrastructure components unrelated to the front‑end. • Non‑Angular parts of the application (e.g., native mobile clients). • Feature development unrelated to the upgrade.

## Affected Components

- All Angular components (presentation layer – ~287 components)
- Pattern Library integration (bnotk/ds-ng) – design‑system components
- Vertical Action Bar component (UI, deprecated but still used)
- Build configuration (Webpack, Angular CLI) and test runners (Karma, Playwright)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 requires TypeScript >=5.0 and Node.js >=18. The current codebase uses TypeScript 4.9.5 and an unspecified older Node version, so both must be upgraded before the framework can be upgraded.
_Sources: tech_versions.json: TypeScript 4.9.5, tech_versions.json: Angular 18‑lts_

**[CAUTION] Dependency Risk**
ng‑bootstrap, ng‑select and ag‑grid versions that work with Angular 18 may not be compatible with Angular 19. The ticket references a specific patch for ng‑bootstrap that must be applied; similar compatibility checks are needed for the other UI libraries.
_Sources: Issue description: ng‑bootstrap (Patch von UVZUSLNVV‑5824) muss berücksichtigt werden_

**[INFO] Integration Boundary**
The vertical action bar is deprecated but still used. It remains supported up to Pattern Library 13.2.0, so after the upgrade to PL 12.6.0 it should continue to function, but verification is required.
_Sources: Acceptance Criteria: Vertical action bar still being used (deprecated but still possible to use till PL 13.2.0)_

**[CAUTION] Testing Constraint**
Karma 6.4.3 and Playwright 1.44.1 are currently used. Angular 19 introduces changes to the testing utilities; the existing test setup must be validated and possibly updated to avoid failing builds.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_

**[INFO] Infrastructure Constraint**
The front‑end build pipeline uses Webpack 5.80.0 and Gradle 8.2.1 for the overall project. While Webpack is likely compatible, the pipeline must be checked for any Angular‑19‑specific loader or plugin requirements.
_Sources: tech_versions.json: Webpack 5.80.0, tech_versions.json: Gradle 8.2.1_


## Architecture Walkthrough

The UVZ system consists of 5 containers. The front‑end lives in the **Presentation** container (layer "presentation", ~287 components). Within this container the Angular application is the core component, built with Angular CLI and bundled by Webpack. It consumes the **Pattern Library** (bnotk/ds-ng) which provides UI primitives such as the vertical action bar. Downstream, the presentation layer talks to the **Application** layer via REST/GraphQL services (Java 17, Gradle). Upstream, the UI components interact with each other through Angular modules and shared services (RxJS). The upgrade will touch the Angular core component, its module definitions, the design‑system integration, and the build configuration. All other containers (backend, infrastructure) remain untouched. Think of the map as: **Container: Presentation → Layer: Presentation → Component: Angular App (core) → Neighbors: Pattern Library, ng‑bootstrap, ng‑select, ag‑grid, Test Runners**.

## Anticipated Questions

**Q: Do we need to upgrade TypeScript and Node.js as part of this task?**
A: Yes. Angular 19 requires TypeScript >=5.0 and Node.js >=18. The current project uses TypeScript 4.9.5 and an older Node version, so both must be upgraded before the Angular packages can be moved to v19.

**Q: Which third‑party libraries are most likely to break after the upgrade?**
A: ng‑bootstrap (requires the patch mentioned in the ticket), ng‑select, ng‑option‑highlight, and ag‑grid‑angular/ag‑grid‑community have known compatibility matrices with Angular versions. Verify each against the Angular 19 release notes and apply the necessary updates.

**Q: Will the existing unit‑ and e2e‑tests still run after the upgrade?**
A: Karma and Playwright versions are currently compatible, but Angular 19 changes its testing utilities (TestBed, component harnesses). Run the full test suite after the upgrade; be prepared to adjust test configurations or update test libraries if failures appear.

**Q: Is the vertical action bar still usable after moving to Pattern Library 12.6.0?**
A: Yes, the vertical action bar is deprecated but remains supported until PL 13.2.0. After upgrading to PL 12.6.0 it should continue to work, but functional verification is required.

**Q: Do we need to touch any backend Java code?**
A: No. This ticket only concerns the front‑end Angular application and its design‑system dependencies. Backend services, database schemas, and infrastructure containers are out of scope.


## Linked Tasks

- UVZUSLNVV-5824 (this upgrade ticket)
- BNUVZ-12529 (analysis comment "how to get to angular 21")