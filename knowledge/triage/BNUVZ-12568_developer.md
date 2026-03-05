# Developer Context: BNUVZ-12568

## Big Picture

Our product is a large Angular‑based web portal used by internal employees and external partners to perform daily business tasks. The portal lives in the *frontend* container (presentation layer) and is built with Angular 18, TypeScript 4.9, Webpack 5 and a custom CI pipeline. The upcoming Angular 19 release deprecates the old SASS import strategy and forces the use of the new Angular Builder SASS compiler. This ticket prepares the build system for that change, ensuring the portal can continue to be released without build breakage. The migration is required now because the Angular 19 upgrade is scheduled for the next release cycle; postponing it would mean the next release cannot be built, causing a hard stop for new features and bug fixes.

## Scope Boundary

IN: All Angular frontend source code, SASS/SCSS files, the angular.json build configuration, CI/CD build scripts, and related unit/e2e test suites that compile styles. OUT: Backend Java services, database schemas, non‑Angular micro‑frontends, and any unrelated libraries that do not participate in style compilation.


## Affected Components

- Angular Build System (presentation)
- Shared Style Library (presentation)
- CI/CD Build Pipeline (infrastructure)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 no longer supports the legacy SASS compiler; the project must switch to the new builder @angular-devkit/build-angular:application or builds will fail.
_Sources: ADR: UVZ-09-ADR-003+-+Frontend+Build+Strategy+SASS+Import+Deprecation_

**[CAUTION] Dependency Risk**
All @angular/* packages are currently pinned to v18‑lts. Upgrading the compiler will require bumping these packages to v19, which may introduce breaking API changes that need verification.
_Sources: tech_versions.json: Angular 18-lts, tech_versions.json: Angular CLI 18-lts_

**[CAUTION] Testing Constraint**
The migration can change the generated CSS output (e.g., @import vs @use semantics). Comprehensive regression testing of UI components is required to catch visual regressions.
_Sources: Issue description: "additional testing may be necessary to minimize the risk of potential regressions"_

**[INFO] Build Tool Constraint**
The project currently uses Gradle 8.2.1 for backend builds and Webpack 5.80.0 for frontend bundling. The new Angular Builder may still rely on Webpack, but its configuration format changes; CI scripts must be reviewed for compatibility.
_Sources: tech_versions.json: Gradle 8.2.1, tech_versions.json: Webpack 5.80.0_


## Architecture Walkthrough

The frontend lives in the **frontend-webapp** container (one of the five system containers). Within that container it belongs to the **presentation** layer, which contains ~287 components including UI modules, shared style libraries, and the Angular build configuration (angular.json). The SASS compiler is invoked by the **Angular Build System** component, which interacts with the **CI/CD pipeline** (infrastructure) to produce bundled assets that are served to users. Neighboring components are:
- **UI Component Library** (consumes the compiled CSS),
- **Shared Styles Module** (provides SCSS files),
- **Test Runner** (Karma/Playwright) that validates rendered UI. 
The migration will touch only the build system and style assets; it does not affect backend services (dataaccess, domain layers).

## Anticipated Questions

**Q: Do we need to update other Angular packages (CDK, Material, etc.) as part of this migration?**
A: Yes. The SASS compiler change is tied to the core Angular packages. All @angular/* dependencies should be upgraded to the matching v19 versions to avoid version mismatches.

**Q: Will existing SASS files need to be rewritten (e.g., @import → @use)?**
A: Potentially. The new compiler enforces the modern Sass module system. Files that still use the deprecated @import syntax may compile but will emit warnings; it is recommended to migrate to @use/@forward to guarantee future compatibility.

**Q: How extensive should regression testing be?**
A: Run the full suite of unit tests (Karma) and end‑to‑end tests (Playwright). Pay special attention to visual regression tests or snapshot tests that compare rendered CSS, as style output may change.

**Q: Is there a fallback to the old compiler if we hit blockers?**
A: The old compiler is no longer supported in Angular 19. A temporary fallback would be to stay on Angular 18 until the issues are resolved, but that would block the overall framework upgrade.

**Q: Do CI build environments (Docker images, Node version) need changes?**
A: Verify that the Node version used in CI satisfies the requirements of the new Angular Builder (Node >=18). The Docker image should be updated if it pins an older Node version.


## Linked Tasks

- UVZ-09-ADR-003 Frontend Build Strategy SASS Import Deprecation