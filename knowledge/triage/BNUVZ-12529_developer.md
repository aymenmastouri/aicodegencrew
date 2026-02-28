# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a client‑facing web portal built with Angular that delivers banking‑related services to internal and external users. The UI lives in the presentation layer of a multi‑container architecture (frontend container) and consumes backend APIs written in Java 17. This task upgrades the UI framework from Angular 18 to Angular 19 and the shared Pattern Library from 11.3.1 to 12.6.0. The upgrade is required now because Angular 18 loses security updates after 21 Nov 2025, forcing the business either to pay for extended support or to move to a supported version. If the upgrade is not performed, the application will become a security liability and may violate compliance requirements.

## Scope Boundary

IN: • Upgrade Angular core, Angular CLI, and all Angular‑related packages to the 19.x line. • Upgrade Pattern Library to 12.6.0. • Update the listed runtime dependencies (node.js, TypeScript, bnotk/ds‑ng, ng‑bootstrap, ng‑select, ag‑grid‑angular, ag‑grid‑community) to versions compatible with Angular 19. • Verify that the vertical action bar (still deprecated) continues to work under PL 12.6.0. • Remove any code, components or styles that belong exclusively to Angular 18/PL 11.3.1 unless they are still required by the new versions. OUT: • Backend Java services, database schema, and any non‑UI infrastructure. • Features unrelated to the UI stack (e.g., reporting jobs, batch processes). • Third‑party libraries not listed in the acceptance criteria.

## Affected Components

- UI components (presentation layer)
- Pattern Library integration module (presentation layer)
- Angular build configuration (infrastructure layer)
- Vertical action bar component (presentation layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 requires TypeScript ≥ 5.2 and Angular CLI ≥ 19. The current stack uses TypeScript 4.9.5 and Angular CLI 18‑lts, so both the compiler and the CLI must be upgraded before any code changes can compile.
_Sources: tech_versions.json: TypeScript 4.9.5, tech_versions.json: Angular CLI 18‑lts_

**[CAUTION] Dependency Risk**
ng‑bootstrap, ng‑select, and ag‑grid have specific version matrices with Angular. Upgrading Angular may break these libraries if incompatible versions are not selected; the patch referenced in UVZUSLNVV‑5824 must be applied to ng‑bootstrap.
_Sources: dependencies.json: @angular/core v18‑lts, dependencies.json: ng-bootstrap (unspecified version)_

**[INFO] Integration Boundary**
The vertical action bar is deprecated but still used. It is only guaranteed to work up to Pattern Library 13.2.0, so the upgrade to PL 12.6.0 must keep this component functional; any removal would be out of scope.
_Sources: issue_context: Acceptance criterion 3_

**[CAUTION] Testing Constraint**
Current test stack (Karma 6.4.3, Playwright 1.44.1) may need updates to work with Angular 19 and the newer TypeScript compiler. Tests must be re‑run after the upgrade to catch regressions.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_


## Architecture Walkthrough

The UVZ system consists of five containers; the UI lives in the **frontend container** (presentation layer, ~287 components). Angular modules and the Pattern Library are loaded here and communicate with backend services via HTTP APIs (application layer). The upgrade touches the **presentation layer** (all UI components) and the **infrastructure layer** where the Angular CLI, Webpack and build scripts reside. Neighboring components include:
- Backend API gateway (application layer) – unchanged.
- Shared design‑system package `bnotk/ds-ng` – will be updated to a version compatible with PL 12.6.0.
- Third‑party UI widgets (ng‑bootstrap, ng‑select, ag‑grid) – located in the same container and must be aligned with Angular 19.
- Test runners (Karma, Playwright) – part of the CI pipeline attached to the frontend container.
Developers should start their work in the `frontend/` directory, adjust `package.json`, `angular.json`, and the Webpack config, then run the full UI test suite to validate the changes.

## Anticipated Questions

**Q: Do we need to upgrade Node.js as part of this task?**
A: Yes. Angular 19 requires Node.js ≥ 18. The current environment should be checked (the exact version is not listed in the provided facts) and upgraded if it is below the required version.

**Q: Will the existing unit and e2e tests still run after the upgrade?**
A: They will need to be re‑executed. Because Angular 19 moves to a newer TypeScript version and may change compiler APIs, some test code (especially type‑heavy unit tests) might need minor adjustments. The test frameworks themselves (Karma, Playwright) may also need version bumps.

**Q: Is the vertical action bar going to be removed in the future?**
A: It is deprecated but still supported up to Pattern Library 13.2.0. This upgrade to PL 12.6.0 must keep it functional; removal is out of scope for this ticket but should be planned for a later refactor.

**Q: What is the impact on the CI/CD pipeline?**
A: The pipeline currently builds with Angular CLI 18 and Node.js versions tied to that stack. After the upgrade, the build step must use Angular CLI 19 and the compatible Node.js version. Pipeline scripts may need to be updated accordingly.

**Q: Are there any licensing costs associated with the upgrade?**
A: No direct licensing costs for Angular 19 or Pattern Library 12.6.0. The upgrade avoids the paid "Never‑Ending Support" that would be required to stay on Angular 18 after its security support ends.


## Linked Tasks

- BNUVZ-12529 (analysis comment "how to get to angular 21")
- UVZUSLNVV-5824 (current ticket)