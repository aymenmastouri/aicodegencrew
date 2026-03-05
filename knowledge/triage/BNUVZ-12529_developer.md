# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a Bnotk‑owned web application that provides a user‑facing interface for internal or external customers. It lives in the presentation container of a five‑container architecture and consists of ~287 presentation‑layer components that rely on Angular and the Bnotk Design System (Pattern Library). The task is to move the front‑end from Angular 18 (LTS) and PL 11.3.1 to Angular 19 and PL 12.6.0, updating all dependent libraries. This upgrade is required now because Angular 18 loses free security support on 21 Nov 2025, exposing the product to vulnerabilities and forcing a costly support contract. Without the upgrade, the system will become insecure and may violate compliance requirements.

## Scope Boundary

IN: All front‑end source code, Angular configuration (angular.json, tsconfig.json), package.json, build pipeline (Angular CLI, Webpack), the Bnotk Design System (bnotk/ds-ng), ng‑bootstrap (including the custom patch), ng‑select, ag‑grid, Node.js version, TypeScript version, and any UI components that reference deprecated Angular 18 or PL 11 APIs (e.g., vertical action bar). OUT: Back‑end Java services, database schemas, infrastructure provisioning, unrelated micro‑services, and any UI modules that are already compatible with Angular 19/PL 12 and need no changes.

## Affected Components

- AppModule (presentation)
- VerticalActionBarComponent (presentation)
- PatternLibraryService (application)
- NgBootstrapWrapperComponent (presentation)
- AgGridComponent (presentation)
- NgSelectComponent (presentation)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 requires a newer Node.js runtime (>=16) and TypeScript 5.x. The current stack uses Node.js (unspecified version) and TypeScript 4.9.5, so both must be upgraded before the Angular upgrade can succeed. This is a blocking constraint because the build will fail otherwise.
_Sources: tech_versions.json: Angular 18‑lts, tech_versions.json: TypeScript 4.9.5_

**[CAUTION] Dependency Risk**
The custom ng‑bootstrap patch referenced in the ticket must be verified against Angular 19. ng‑bootstrap versions prior to the patch may not be compatible, so the patch may need adaptation or replacement. This is a cautionary risk that could cause runtime errors or broken UI components.
_Sources: issue description: ng-bootstrap (Patch von UVZUSLNVV-5824 muss berücksichtigt werden)_

**[BLOCKING] Integration Boundary**
bnotk/ds-ng (the Design System library) must support Angular 19 and Pattern Library 12.6.0. If the library version used today is tied to Angular 18, it must be upgraded or a compatible version selected. This is a blocking integration point because UI components depend on it.
_Sources: issue description: bnotk/ds-ng_

**[INFO] Pattern Library Constraint**
Pattern Library 12.6.0 still provides the vertical action bar but marks it deprecated, with removal planned after PL 13.2.0. The upgrade must ensure the component continues to work and that no old PL 11 artifacts remain. This is informational but should be tracked for future refactoring.
_Sources: issue acceptance criteria: vertical action bar is still being used (deprecated but still possible to use till PL 13.2.0)_


## Architecture Walkthrough

The UVZ front‑end lives in the **presentation container** (one of five containers). Within that container, the code is organized into the **presentation layer** (≈287 components) that directly consume Angular core and the Bnotk Design System. The **application layer** (≈184 components) provides services such as PatternLibraryService that wrap PL components. The **vertical action bar** is a UI component in the presentation layer that currently depends on PL 11 APIs. Upgrading to Angular 19 and PL 12.6.0 will affect:
- **AppModule** (root module) – Angular version bump, imports, and providers.
- **PatternLibraryService** – may need to reference new PL modules.
- **UI components** (VerticalActionBarComponent, NgBootstrapWrapperComponent, AgGridComponent, NgSelectComponent) – will need to compile against Angular 19 and updated third‑party libs.
- **Build pipeline** – Angular CLI 19, Webpack config, and possibly Karma/Jasmine test runners.
Neighbors include the **backend API** (Java services) accessed via HTTP; those remain unchanged but must continue to expose the same contracts. The **design system repository** (bnotk/ds-ng) is a sibling library that is versioned separately but consumed here. All changes stay within the front‑end container; no cross‑container impact is expected.

## Anticipated Questions

**Q: Which Node.js and TypeScript versions are required for Angular 19?**
A: Angular 19 needs Node.js >=16 (preferably 18) and TypeScript 5.2+. The current project uses TypeScript 4.9.5, so both Node.js and TypeScript must be upgraded before the Angular upgrade.

**Q: Will the existing unit and e2e tests run after the upgrade?**
A: Tests use Karma and Playwright, which are compatible with Angular 19, but they may need configuration updates (e.g., tsconfig changes, Angular testing utilities). Verify the test suite after the upgrade.

**Q: Is the custom ng‑bootstrap patch still applicable to Angular 19?**
A: The patch was created for Angular 18. It must be reviewed against the Angular 19 version of ng‑bootstrap; if the API changed, the patch will need adjustment or a newer ng‑bootstrap version should be used.

**Q: Do we need to change any backend contracts because of the UI upgrade?**
A: No. The upgrade only affects the front‑end stack. Backend APIs remain unchanged, but ensure that any data models used in the UI are still compatible with the existing API contracts.

**Q: What happens to the vertical action bar after the upgrade?**
A: The component will continue to work because PL 12.6.0 still ships it (deprecated but supported until PL 13.2.0). No functional change is required, but the code should be audited to remove any PL 11‑specific imports.


## Linked Tasks

- UVZUSLNVV-5824 (ng‑bootstrap patch)
- BNUVZ-12529 (analysis of how to reach Angular 21 – provides dependency list)