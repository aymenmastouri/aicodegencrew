# Developer Context: BNUVZ-12529

## Big Picture

UVZ (Unabhängiger Vertreter für das Notarwesen — a German federal notary service platform) is a critical government-facing web application used by notaries and legal authorities for high-stakes, compliance-sensitive workflows. It relies on Angular (frontend) and Java/Gradle (backend). The current tech stack (Angular 18 + PL 11.3.1) is outdated and losing security support. This task is a mandatory mid-cycle upgrade to Angular 19 and Pattern Library 12.6.0 to preserve supportability, security, and interoperability with newer tooling — and to avoid being locked into an unsupported baseline. Without it, the system risks security gaps, loss of vendor support, and an unsustainable upgrade path toward Angular 20/21 later.

## Scope Boundary

IN scope: Upgrade to Angular 19 and PL 12.6.0, including all listed direct/indirect dependencies (node.js, TypeScript, ds-ng, ng-bootstrap, ng-select/*, ag-grid-*); preserve use of deprecated vertical action bar (still supported up to PL 13.2.0); remove obsolete Angular 18 / PL 11.3.1 artifacts unless retained in PL 12.6.0. OUT of scope: Direct upgrade to Angular 20/21 (explicitly excluded by requirement); backend changes (Java/Gradle); full regression test suite creation; redesign of UI or components.

## Affected Components

- Package.json dependencies (frontend)
- Angular CLI / build configuration (frontend)
- Pattern Library integration (frontend)
- Dependency resolution logic (frontend)
- Vertical action bar component usage (frontend)

## Context Boundaries

**[BLOCKING] Technology Constraint**
The current TypeScript version (4.9.5) in tech_versions.json is incompatible with Angular 19, which requires TypeScript ≥ 5.5 (per Angular release notes). A manual upgrade path must be planned — e.g., TypeScript 5.4 → 5.5 in locksteps — to avoid build/test breakage. This is not a one-click change.
_Sources: tech_versions.json: TypeScript 4.9.5_

**[BLOCKING] Dependency Risk**
All listed dependencies (e.g., @angular/* v18-lts, ng-select, ag-grid-angular, bnotk/ds-ng) must be verified for Angular 19 compatibility. ds-ng (bnotk/ds-ng) is a proprietary Pattern Library wrapper — its version must match PL 12.6.0 exactly. Failure to align these will cause runtime failures or visual regressions.
_Sources: dependencies.json: @angular/* v18-lts, dependencies.json: bnotk/ds-ng_

**[CAUTION] Pattern Constraint**
The vertical action bar is deprecated but still used and required to remain functional until PL 13.2.0. Angular 19/PL 12.6.0 must still expose the necessary directives/HTML structure to render it — if the component has been fully removed or its API changed in breaking ways, a migration workaround or replacement must be pre-validated.
_Sources: AS-IS description: vertical action bar still used, Acceptance criterion: still needed_

**[CAUTION] Integration Boundary**
ng-bootstrap must incorporate a specific patch from UVZUSLNVV-5824. If that patch modifies internal services or templates, it must be reapplied or ported to be compatible with PL 12.6.0 — otherwise it may break modals, date pickers, or other ng-bootstrap-based features.
_Sources: ng-bootstrap patch from UVZUSLNVV-5824 must be considered_

**[CAUTION] Infrastructure Constraint**
Angular 19 requires Node.js ≥ 18 (LTS). If current CI/CD or local dev environments use older Node versions (e.g., Node 16), they must be upgraded — otherwise builds will fail with 'Unsupported Node.js' errors.
_Sources: node.js listed as required dependency, Angular version requirements_


## Architecture Walkthrough

The upgrade sits entirely in the frontend application container (UVZ frontend, probably a single-page Angular app under /frontend). It starts with package.json (dependency declarations), propagates through angular.json (CLI config, build settings, and schematics), and touches all Angular modules (e.g., core, common, compiler, animations, etc.). The pattern library (ds-ng) wraps Angular-based UI primitives — so any internal ds-ng version bumps will affect the component catalog and theming. The vertical action bar is a UI component in the presentation layer (likely shared or layout-level), so its continued rendering depends on how PL 12.6.0 supports legacy APIs. Since this is a front-end-only task, backend services, API contracts, and Gradle build logic (Java layer) remain untouched — but any mismatched versioning could cause integration test failures if the backend expects older client behavior.

## Anticipated Questions

**Q: Do we upgrade Node.js and TypeScript manually, or does Angular’s update script handle it?**
A: Manual — Angular’s update schematic (e.g., ng update @angular/core @angular/cli) updates Angular packages and tries to infer compatible dependencies, but it cannot force Node.js (environment-wide) or TypeScript (if pinned strictly) upgrades. You’ll need to bump Node.js to ≥18 and TypeScript to ≥5.5 (ideally incrementally: 5.4 → 5.5), then run ng update again. Verify via `node --version`, `tsc --version`, and `package.json`.

**Q: Where is ds-ng (Pattern Library wrapper) configured — do we just update its version?**
A: It’s a npm dependency listed in package.json (e.g., bnotk/ds-ng). You’ll need to upgrade to the version matching PL 12.6.0 (likely published as `@bnotk/ds-ng@12.6.0`). Its installation will bring in new Angular modules/directives, but no code changes are expected unless its API changed (e.g., deprecated inputs). Check ds-ng release notes for PL 12.x.

**Q: Is the vertical action bar something we need to actively migrate?**
A: No — but only if PL 12.6.0 still exposes the deprecated API. If ds-ng or PL 12.6.0 removes the component entirely or changes its rendering signature (e.g., selector, inputs), you’ll see runtime errors (e.g., 'ng-activity-bar' is not a known element). Validate this via Storybook or ds-ng docs for PL 12.6.0 before proceeding.

**Q: What about the ng-bootstrap patch from UVZUSLNVV-5824 — do we apply it after the upgrade?**
A: Yes — the patch must be reapplied or ported. If the patch modifies ng-bootstrap internals (e.g., modal overlay handling), it won’t survive a clean dependency reinstall. Keep the patch file(s) in source control, or create a custom fork/patch package. Do not assume ng-bootstrap@latest + patch applies cleanly without manual merge.


## Linked Tasks

- UVZUSLNVV-5824 (patch for ng-bootstrap)
- BNUVZ-12529 (‘how to get to angular 21’ comment by Filip Misiorek)