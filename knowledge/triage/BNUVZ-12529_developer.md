# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a web‑based application used by internal users of BNOTK (the client) to perform various operational tasks. The front‑end is built with Angular and consumes back‑end services (Java 17, Spring) via REST/GraphQL. This ticket addresses the need to move the front‑end from Angular 18 to Angular 19 and to update the internal Pattern Library from 11.3.1 to 12.6.0. The upgrade is required now because Angular 18 will lose free security updates after 21 Nov 2025, exposing the application to potential vulnerabilities and forcing a costly support contract. Without the upgrade, the product would become insecure, non‑compliant with internal security policies, and future upgrades would be more disruptive.

## Scope Boundary

IN: • Upgrade Angular core, CLI, and related packages to v19. • Upgrade Pattern Library to 12.6.0. • Update all listed runtime dependencies (node.js, TypeScript, bnotk/ds‑ng, ng‑bootstrap with its patch, ng‑select, ng‑option‑highlight, ag‑grid‑angular, ag‑grid‑community). • Adjust code for deprecations (e.g., vertical action bar usage, Karma removal if needed). • Remove any leftover Angular 18/PL 11 code that is not required by the new versions. OUT: • Back‑end Java services, database schema, CI/CD pipeline scripts unrelated to the front‑end build, non‑Angular UI components, and any third‑party libraries not listed in the acceptance criteria.

## Affected Components

- UI Components (presentation layer)
- Pattern Library Integration Module (presentation layer)
- Vertical Action Bar Component (presentation layer)
- Angular Build Configuration (infrastructure layer)
- ng‑bootstrap wrapper components (presentation layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 requires TypeScript 5.x and a newer Node.js runtime than the current project (which uses TypeScript 4.9.5). The build must be updated accordingly, otherwise the compilation will fail.
_Sources: tech_versions.json: Angular 18.2.13, tech_versions.json: TypeScript 4.9.5_

**[CAUTION] Dependency Risk**
Key UI libraries (ng‑bootstrap, ng‑select, ag‑grid) must have versions that are compatible with Angular 19. Some of the current versions may only support Angular 18, so a version bump or patch may be required.
_Sources: issue_context: ng-bootstrap (Patch von UVZUSLNVV-5824) muss berücksichtigt werden, issue_context: ag-grid-angular, issue_context: ng-select/ng-select_

**[CAUTION] Testing Constraint**
Karma 6.4.3, used for unit tests, is deprecated in Angular 19. Tests will need to be migrated to a supported runner (e.g., Jest) or the Karma configuration must be updated to a compatible version.
_Sources: tech_versions.json: Karma 6.4.3_

**[BLOCKING] Security Boundary**
Angular 18 security updates end on 21 Nov 2025. Continuing to run the current version without paid support would leave the application exposed to known vulnerabilities.
_Sources: issue_context: Support for security updates did end on 21.11.2025 for Angular 18_

**[CAUTION] Pattern Library Constraint**
Pattern Library 12.6.0 introduces breaking changes; any custom components that rely on PL 11 APIs must be reviewed and adapted.
_Sources: issue_context: Upgrade to Angular 19 and PL 12.6.0_


## Architecture Walkthrough

The UVZ system consists of five containers. The front‑end lives in the **"frontend-webapp"** container (presentation layer, ~202 components). It sits above the **application layer** (services that expose REST/GraphQL APIs) and below the **domain layer** (business logic). The Angular codebase is the entry point for user interaction and consumes services via HTTP. The Pattern Library is a shared UI component library imported into the frontend container. The vertical action bar component is a UI widget that, while deprecated, is still part of the presentation layer and must remain functional until PL 13.2.0. Upgrading Angular and the Pattern Library will affect all presentation‑layer components that import PL modules or use ng‑bootstrap/ng‑select/ag‑grid. The build pipeline (Webpack 5, Angular CLI) resides in the infrastructure layer of the same container. Neighboring components include the API gateway (application layer) and the shared design system (bnotk/ds‑ng) which also needs a version bump.

## Anticipated Questions

**Q: Do we need to update the test framework (Karma) as part of the upgrade?**
A: Yes. Karma 6.4.3 is not supported by Angular 19. Either upgrade Karma to a compatible version or migrate the unit tests to a supported runner such as Jest. This is required to keep the CI pipeline green.

**Q: Which versions of Node.js and TypeScript are required for Angular 19?**
A: Angular 19 officially supports Node >=16.14 and TypeScript 5.x. The current project uses Node <16 and TypeScript 4.9.5, so both need to be upgraded before the Angular upgrade can succeed.

**Q: Will the vertical action bar still work after the upgrade?**
A: The vertical action bar is deprecated but remains supported up to Pattern Library 13.2.0. As long as the PL version stays ≤13.2.0 (we target 12.6.0), the component should continue to work, but its usage should be verified after the upgrade.

**Q: Are there any breaking changes in the Pattern Library 12.6.0 that could affect our custom components?**
A: Yes. PL 12 introduces several API changes and deprecations. All custom components that import PL modules must be reviewed against the PL migration guide. Only parts still required by Angular 19/PL 12.6.0 may remain.

**Q: Do we need to adjust any CI/CD scripts for the new Angular version?**
A: Potentially. The build scripts reference the Angular CLI version and may pin Node/TypeScript versions. Those references will need to be updated to the new versions, and any caching steps that depend on the old package lock files should be refreshed.


## Linked Tasks

- UVZUSLNVV-5824
- BNUVZ-12529 (analysis comment "how to get to angular 21")