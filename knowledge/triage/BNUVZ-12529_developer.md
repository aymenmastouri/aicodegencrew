# Developer Context: BNUVZ-12529

## Big Picture

(1) UVZ is a core legal/clinical workflow platform used by German notaries and legal professionals to manage official case workflows. (2) It serves government-authorized users in high-stakes environments where reliability, auditability, and security are non-negotiable. (3) This task resolves an urgent security and compatibility gap caused by Angular 18’s end-of-life — the system cannot safely or sustainably remain on this version. (4) It is needed NOW because the security support deadline has already passed (21.11.2025), and the next upgrade path (to Angular 20/21) is blocked until Angular 19 is adopted. (5) If not done, the system faces unpatched security vulnerabilities, loss of vendor support, inability to integrate with newer tooling or dependencies, and potential regulatory or compliance failures.

## Scope Boundary

IN scope: All Angular 18 → 19 migration activities, including PL 11.3.1 → 12.6.0 upgrade, dependency updates (Node.js, TypeScript, ds-ng, ng-bootstrap, ng-select, ag-grid), and removal of deprecated Angular 18 / PL 11.x artifacts that are not supported in Angular 19 / PL 12.6.0. OUT of scope: Upgrading beyond Angular 19 (e.g., to 20/21), refactoring business logic, changing UI behavior beyond what’s required for compatibility, and non-Angular backend changes.

## Affected Components

- UVZ Frontend (frontend)
- Pattern Library integration layer (frontend)
- Dependency management (npm package.json)
- Vertical action bar component (frontend, deprecated but still used)
- Build pipeline (webpack, TypeScript config)

## Context Boundaries

**[BLOCKING] Technology Constraint**
The project uses TypeScript 4.9.5, which is incompatible with Angular 19’s minimum requirement of TypeScript 5.2+. This forces a mandatory TypeScript upgrade as part of the Angular 19 migration — skipping it will break compilation or cause runtime type errors.
_Sources: tech_versions.json: TypeScript 4.9.5_

**[BLOCKING] Dependency Risk**
Multiple core libraries — @angular/* packages (v18-lts), ng-bootstrap, ng-select, ag-grid — are currently pinned to Angular 18. Upgrading to Angular 19 requires verifying version compatibility with each, especially ng-bootstrap (requires applying patch from UVZUSLNVV-5824) and ag-grid (both community and angular integrations must align with Angular 19’s public API). Incompatibility may cause runtime failures or silent regressions.
_Sources: dependencies.json: @angular/animations v18-lts, dependencies.json: @angular/cdk v18-lts_

**[CAUTION] Pattern Constraint**
The vertical action bar is deprecated in PL 11.3.1 but still supported up to PL 13.2.0. The team must confirm it remains functional under PL 12.6.0 and Angular 19 — if deprecated APIs were removed in PL 12.x, this component may break and require migration before PL 13.x. This is a risk to functionality, not just aesthetics.
_Sources: Acceptance criterion 3: 'Vertical action bar is still being used (deprecated but still possible to use till PL 13.2.0)'_

**[CAUTION] Integration Boundary**
The project uses RxJS 7.8.2, which is compatible with Angular 19, but the team must verify no deprecated RxJS operators (e.g., from RxJS 5/6) remain in use — Angular 19 enforces stricter imports and may reject legacy syntax (e.g., `import { Observable } from 'rxjs';` vs `import { Observable } from 'rxjs/internal/Observable';`). Legacy usage would break compilation.
_Sources: tech_versions.json: RxJS 7.8.2_

**[INFO] Infrastructure Constraint**
The project uses Webpack 5.80.0 and Karma 6.4.3. While both support Angular 19, minor configuration adjustments may be required (e.g., for ES2022 target, zone.js changes, or test runner compatibility). These are not blocking but may cause test failures or build regressions if not validated.
_Sources: tech_versions.json: Webpack 5.80.0, tech_versions.json: Karma 6.4.3_


## Architecture Walkthrough

This task resides entirely in the **frontend container** of the UVZ monorepo. Specifically, it operates at the **UI framework layer** (Angular + Pattern Library integration), above the **business logic layer** (Angular services/components) and below the **infrastructure layer** (build tools, CI/CD). The upgrade touches the root `package.json`, `angular.json`, and `tsconfig.json`, and requires coordinated updates across several peer dependencies (e.g., `ng-select`, `ag-grid`). The vertical action bar component — while deprecated — lives in a shared UI component library (likely `bnotk/ds-ng`) and must be validated for continued use. No backend changes are involved, but any API contracts used by the frontend (e.g., REST endpoints) must remain stable during the frontend rebuild. The build toolchain (Webpack, Karma, Playwright) must also be validated post-upgrade.

## Anticipated Questions

**Q: Do I need to update Angular CLI? How do I know which CLI version matches Angular 19?**
A: Yes — Angular CLI version must match the Angular core version (or be at least compatible). Angular 19 requires Angular CLI ≥ 19.0.0. Check `@angular/cli` in `package.json` and ensure it is upgraded alongside `@angular/core`. The Angular team guarantees CLI compatibility within the same major version family, and Angular 19 CLI is backward compatible with Angular 18 projects during migration.

**Q: What exactly does ‘Patch from UVZUSLNVV-5824’ for ng-bootstrap mean — is it a PR, a local fork, or a version bump?**
A: Based on the description, it refers to a specific patch applied to ng-bootstrap to maintain compatibility with the project’s current usage (likely a custom patch or cherry-picked commit). You must locate the patch (in the Jira issue or related git commit) and ensure it is applied or upstreamed before upgrading ng-bootstrap to the version compatible with Angular 19. Failure to apply it may cause regressions in modal/dialog or form behavior.

**Q: How do I verify that deprecated Angular 18 / PL 11.x code is truly gone after migration?**
A: Use `ngcc --properties es2020` post-install to validate compatibility, run `npm outdated` to catch stale peer deps, and use Angular’s `ng update` diagnostics (`ng update --all --dry-run`). Additionally, search for deprecation warnings in the build log and run Storybook (if available) to verify component compatibility. The acceptance criterion explicitly requires removal of *unused* legacy artifacts — e.g., removed modules or exports in PL 12.6.0 that were present in 11.3.1.


## Linked Tasks

- UVZUSLNVV-5824
- BNUVZ-12529