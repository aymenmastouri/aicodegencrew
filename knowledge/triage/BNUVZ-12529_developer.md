# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a critical case management system used by notaries in Germany, built with an Angular frontend and Java backend. It supports high-stakes workflows where reliability and security are paramount. This upgrade closes a support gap: Angular 18 is EOL, while Angular 19 (and PL 12.6.0) restores security updates, modern toolchain alignment, and future upgradeability. The task is required NOW because the deadline for free support passed in November 2025, and delaying further pushes risk compliance and incident response capability.

## Scope Boundary

IN: All dependencies listed in AC2 (node.js, TypeScript, ds-ng, ng-bootstrap, ng-select/ng-option-highlight, ng-select/ng-select, ag-grid-angular, ag-grid-community), plus Angular and PL version upgrades. Also includes preserving deprecated Vertical Action Bar usage (allowed until PL 13.2.0). OUT: Migration to Angular 20/21 (explicitly deferred), backend changes, PL upgrades beyond 12.6.0, removal of deprecated Angular 18 features unless they remain supported.

## Affected Components

- UVZ Frontend (frontend)
- Pattern Library integration (frontend)
- Dependency management (build/tooling)
- Component library overrides (frontend)
- Ag-Grid and ng-select integrations (frontend)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular upgrades are strictly sequential per official guidance (Angular 18 → 19 → 20 → 21); direct jumps to 20/21 are not supported (as confirmed in FRM minutes 14.01.26 and angular.dev reference). This forces a 19-first path, even if 21 is the eventual goal.
_Sources: src: ORIGINAL ISSUE — 'FRM am 14.01.26 besprochen, das wir nicht direkt auf 20 oder 21 gehen können'; angular.dev reference URL_

**[CAUTION] Dependency Risk**
All listed third-party libraries must be upgraded in lockstep with Angular 19 — e.g., ng-bootstrap requires a patch from UVZUSLNVV-5824, and ag-grid packages must be version-pinned for compatibility. Mismatched versions risk runtime breakage or silent regressions.
_Sources: src: dependencies.json — @angular/* v18-lts, src: AC2 list, src: ORIGINAL ISSUE — ng-bootstrap patch must be considered_

**[CAUTION] Integration Boundary**
The ds-ng library (bnotk/ds-ng) is the internal pattern library wrapper — upgrading from PL 11.3.1 → 12.6.0 may change component APIs or CSS scoping. The Vertical Action Bar, while deprecated, is still supported until PL 13.2.0 and must be preserved — meaning backward-compatibility layers or overrides may be needed.
_Sources: src: AC3 — 'vertikale Aktionsleiste verwendet (deprecated aber noch bis PL 13.2.0)'; ds-ng reference in AC2_

**[BLOCKING] Infrastructure Constraint**
The project uses TypeScript 4.9.5 (per tech_versions.json) — a version no longer compatible with Angular 19, which requires ≥ TypeScript 5.4. This mandates a simultaneous TypeScript upgrade, affecting type-checking behavior, build times, and potential strictness-related breakage.
_Sources: src: ANALYSIS INPUTS — TypeScript 4.9.5, src: Angular 19 TypeScript requirement (implied by Angular ecosystem docs)_

**[INFO] Testing Constraint**
Playwright 1.44.1 is current, but its compatibility with Angular 19’s changed hydration/SSR behavior or change detection timing must be verified — especially for e2e tests covering workflows using ag-grid or ng-select components.
_Sources: src: ANALYSIS INPUTS — playwright 1.44.1, src: dependencies.json_

**[INFO] Pattern Constraint**
The frontend uses RxJS 7.8.2 — this is compatible with Angular 19, but deprecated operators (e.g., from RxJS 6.x compatibility layer) may surface new warnings or deprecations. No breaking change expected, but refactor opportunities may arise.
_Sources: src: ANALYSIS INPUTS — RxJS 7.8.2_


## Architecture Walkthrough

This task sits entirely in the *frontend container*, specifically the Angular layer (UI shell + application components). The upgrade starts at `package.json` (Angular Core, CDK, Common, Compiler, etc. all at v18-lts per dependencies.json) and cascades to: (1) build toolchain (Angular CLI, Webpack 5.x, TypeScript 5.4+), (2) UI dependencies (ds-ng → PL 12.6.0, ng-bootstrap, ag-grid, ng-select), (3) runtime libraries (RxJS, Playwright, etc.). Neighboring components include backend services (Java/Gradle), but the change is UI-layer only — no backend modifications expected. The workflow services layer (e.g., task-module.service.ts) remains unaffected, but component bindings to those services must be verified for API stability post-upgrade.

## Anticipated Questions

**Q: Do we need to update the backend (Java/Gradle)?**
A: No — Java 17 and Gradle 8.2.1 remain unchanged. The upgrade is strictly frontend, though version compatibility of REST API clients (e.g., if using deprecated HTTP features) should be verified.

**Q: Where do I find the ng-bootstrap patch mentioned in UVZUSLNVV-5824?**
A: The patch is referenced in the issue title — consult JIRA ticket UVZUSLNVV-5824 directly. The patch likely modifies ng-bootstrap usage or adds an override for a known compatibility issue with PL 12.x.

**Q: What happens to the Vertical Action Bar after the upgrade?**
A: It remains supported until PL 13.2.0. Its continued use is explicitly allowed per AC3 — no forced removal, but it should be documented as deprecated and flagged for future migration.


## Linked Tasks

- UVZUSLNVV-5824 (ng-bootstrap patch)
- BNUVZ-12529 (how to get to Angular 21 analysis)