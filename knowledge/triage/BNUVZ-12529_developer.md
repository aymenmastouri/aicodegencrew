# Developer Context: BNUVZ-12529

## Big Picture

UVZ is the front‑end of an internal (or public‑sector) portal that delivers business functionality to end‑users via a browser. The UI is built as a single‑page Angular application (presentation layer) that consumes back‑end services (application/domain layers) through REST/GraphQL APIs. The task is to move the UI from Angular 18 (which is already out of security support) to Angular 19 and to bring the shared Pattern Library from 11.3.1 to 12.6.0. This upgrade restores security patch coverage, aligns the stack with the vendor’s supported LTS roadmap, and prevents the need for costly “Never‑Ending‑Support” licences. Doing it now avoids a security gap that would appear after 21 Nov 2025.

## Scope Boundary

IN: • Upgrade Angular core, CLI and all @angular packages from v18‑lts to v19. • Upgrade Pattern Library to 12.6.0. • Update Node.js, TypeScript, bnotk/ds‑ng, ng‑bootstrap (including the specific patch referenced in UVZUSLNVV‑5824), ng‑select/ng‑option‑highlight, ng‑select, ag‑grid‑angular and ag‑grid‑community to versions compatible with Angular 19. • Verify that the vertical action bar continues to work (it is deprecated but still supported up to PL 13.2.0). • Remove any code, components or styles that belong exclusively to Angular 18 or PL 11.3.1 unless they are still required by the new versions. OUT: • Any back‑end Java services, database schema changes, or infrastructure (servers, CI pipelines) that are not directly tied to the front‑end build. • Non‑UI related libraries not listed above. • New feature development unrelated to the upgrade.

## Affected Components

- UVZAppComponent (presentation)
- VerticalActionBarComponent (presentation)
- PatternLibraryService (presentation)
- NgBootstrapWrapper (presentation)
- AgGridWrapper (presentation)

## Context Boundaries

**[CAUTION] Technology Constraint**
Angular 19 requires at least TypeScript 5.x and Node >= 18. The current stack uses TypeScript 4.9.5 and an unspecified Node version, so the upgrade will force a TypeScript and Node version bump before the Angular packages can be upgraded.
_Sources: tech_versions.json: TypeScript 4.9.5, tech_versions.json: Angular 18‑lts_

**[BLOCKING] Dependency Risk**
Several UI libraries (ng‑bootstrap, ng‑select, ag‑grid) have version matrices tied to specific Angular major versions. Upgrading Angular without first confirming compatible releases may cause compile‑time or runtime errors.
_Sources: dependencies.json: @angular/* v18‑lts, issue description: list of libraries that must be updated_

**[INFO] Integration Boundary**
The vertical action bar component is deprecated but still functional up to Pattern Library 13.2.0. The upgrade must keep this component alive; any removal would break UI functionality that downstream teams rely on.
_Sources: issue description: vertical action bar still used (deprecated but allowed until PL 13.2.0)_

**[BLOCKING] Security Boundary**
Angular 18 security patches end on 21 Nov 2025. Continuing to run on this version after that date would leave the application exposed to unpatched vulnerabilities.
_Sources: issue description: security support for Angular 18 ends 21.11.2025_

**[CAUTION] Testing Constraint**
The project uses Karma 6.4.3 and Playwright 1.44.1 for unit and e2e tests. Both test runners have compatibility requirements with the Angular compiler version; test configuration may need adjustments after the Angular upgrade.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_


## Architecture Walkthrough

The UVZ front‑end lives in its own container (e.g., `uvz-frontend`) which belongs to the **presentation** layer of the overall system. Inside this container, the Angular application is composed of many UI components (≈287 presentation components). The upgrade touches the core Angular module (`@angular/core` etc.) and the shared Pattern Library module (`bnotk/ds-ng`). These modules are imported by most UI components, including the vertical action bar and grid wrappers. Downstream, the UI calls back‑end services located in the **application** layer (≈184 components) via HTTP. Upstream, the UI receives data models defined in the **domain** layer (≈411 components). The upgrade therefore sits at the top of the dependency graph: changing the Angular version propagates to all presentation components, but does not directly affect the application or domain layers. The main neighboring modules are:
- **Pattern Library (ds‑ng)** – provides UI primitives and styling.
- **ng‑bootstrap / ng‑select / ag‑grid** – third‑party UI widgets that depend on Angular version.
- **VerticalActionBarComponent** – a deprecated UI feature that must remain functional.
Developers should start from the `package.json`/`angular.json` files in the `uvz-frontend` container, update the versions, then run the full build and test suite to verify that all presentation components still compile and render correctly.

## Anticipated Questions

**Q: Which Node.js and TypeScript versions are required for Angular 19?**
A: Angular 19 LTS expects Node >= 18 and TypeScript 5.x. The current project uses TypeScript 4.9.5, so both the TypeScript compiler and the Node runtime will need to be upgraded before the Angular packages can be moved to v19.

**Q: Are the listed third‑party libraries (ng‑bootstrap, ng‑select, ag‑grid) already compatible with Angular 19, or do we need to wait for newer releases?**
A: Compatibility must be verified against each library’s release notes. The issue explicitly lists them as items to update, indicating that compatible versions exist but have not yet been adopted. The upgrade should target the latest versions that declare support for Angular 19.

**Q: Will the vertical action bar continue to work after the upgrade, or do we need to replace it?**
A: The vertical action bar is deprecated but still supported up to Pattern Library 13.2.0. Since the target PL version is 12.6.0, the component should remain functional, but its usage must be confirmed after the upgrade.

**Q: Do we need to adjust the test configuration (Karma, Playwright) because of the Angular version bump?**
A: Both Karma and Playwright have version constraints tied to the Angular compiler. After upgrading Angular, run the test suite; if failures appear, update the Karma configuration (e.g., `karma.conf.js`) and/or Playwright test scripts to align with the new Angular build output.

**Q: Is there any impact on the back‑end services or API contracts?**
A: No. The upgrade only touches the front‑end stack. API contracts remain unchanged because the UI continues to call the same back‑end endpoints. However, any changes to request payload shapes introduced by updated UI components should be reviewed against the back‑end specifications.


## Linked Tasks

- UVZUSLNVV-5824 (patch for ng‑bootstrap)
- BNUVZ-12529 (analysis of upgrade path to Angular 21 – provides context for dependencies)