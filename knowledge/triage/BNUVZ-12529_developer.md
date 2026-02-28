# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a web‑based application used by internal users of BNOTK to process and view notarial and registration data. The frontend is a single‑page Angular application that lives in the presentation container and communicates with backend services (application and domain layers) via REST APIs. This task upgrades the frontend framework from Angular 18 to Angular 19 and updates the shared Pattern Library from 11.3.1 to 12.6.0. The upgrade is required because Angular 18 will lose security support in November 2025, leaving the system vulnerable unless we either pay for a support contract or move to a supported version. If we do not upgrade, the application will no longer receive security patches, increasing compliance risk and potential exposure to attacks.

## Scope Boundary

IN: All Angular source code (components, modules, services) in the presentation container, the Pattern Library assets, build configuration (Angular CLI, Webpack), and UI third‑party libraries listed in the acceptance criteria (ng‑bootstrap, ng‑select, ag‑grid, etc.). OUT: Backend Java services, database schemas, non‑UI infrastructure, and any features that are not part of the Angular UI stack.


## Affected Components

- AppModule (presentation)
- SharedModule (presentation)
- All UI components under src/app (presentation)
- Pattern Library integration module (presentation)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 requires TypeScript >=5.0 and Node.js >=16. The current stack uses TypeScript 4.9.5 (tech_versions.json) and an unspecified Node version, so both must be upgraded before the framework can be upgraded.
_Sources: tech_versions.json: TypeScript 4.9.5, tech_versions.json: Angular 18‑lts_

**[CAUTION] Dependency Risk**
UI libraries such as ng‑bootstrap, ng‑select, and ag‑grid have specific version compatibility matrices with Angular. The current versions (listed in the issue) are built for Angular 18; they must be upgraded to versions that support Angular 19, otherwise runtime errors or broken UI will occur.
_Sources: issue description: ng‑bootstrap patch required, dependencies.json: @angular/* v18‑lts_

**[INFO] Integration Boundary**
The vertical action bar component is deprecated but still usable up to Pattern Library 13.2.0. After upgrading to PL 12.6.0 it must be verified that the component still renders and that no breaking changes have been introduced.
_Sources: issue description: vertical action bar still used (deprecated)_

**[CAUTION] Testing Constraint**
The test suite uses Karma 6.4.3 and Angular testing utilities tied to Angular 18. Upgrading to Angular 19 may require newer versions of Karma, Jasmine, and @angular/* testing packages to keep tests passing.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Angular 18‑lts_


## Architecture Walkthrough

The UVZ system consists of 5 containers. The frontend lives in the **Presentation Container** (layer = presentation, ~287 components). This container is built with Angular CLI and bundled by Webpack. It consumes services from the **Application Container** via HTTP APIs. The Pattern Library (PL) is a shared UI component library also loaded in the presentation layer. All Angular components, modules, and services belong to this container. Upgrading Angular and PL will affect:
- The **build pipeline** (Angular CLI, Webpack configuration) in the presentation container.
- Every **UI component** that imports Angular core modules or Pattern Library components.
- **Third‑party UI libraries** (ng‑bootstrap, ng‑select, ag‑grid) that are dependencies of the presentation components.
- The **test harness** (Karma/Jasmine) that runs in the same container.
Neighbouring containers (application, domain) remain untouched; they communicate via REST endpoints, which are not affected by the frontend framework version.

**YOU ARE HERE**: Inside the Presentation Container, focusing on the Angular source tree and its build configuration. All changes will be confined to this container and will not ripple into backend code.

## Anticipated Questions

**Q: Which Node.js version do we need for Angular 19?**
A: Angular 19 officially supports Node.js 16 LTS and newer. Verify the CI/CD pipeline and local development environments are upgraded to at least Node 16 (preferably Node 18) before starting the framework upgrade.

**Q: Do we have to update the test suite (Karma, Jasmine) as part of this upgrade?**
A: Yes. Angular 19 brings changes to the testing utilities. The existing Karma 6.4.3 version may still work, but you should upgrade Karma and related plugins to the latest versions that declare compatibility with Angular 19 to avoid test failures.

**Q: Are there known breaking changes in ng‑bootstrap or ag‑grid that could affect our UI?**
A: Both libraries release major versions aligned with Angular releases. Check the release notes for the versions that support Angular 19; they may introduce API changes or deprecations. The issue already mentions a required patch for ng‑bootstrap, so that patch must be applied after the library version is updated.

**Q: Can we keep using the vertical action bar after the upgrade?**
A: The vertical action bar is deprecated but remains supported up to Pattern Library 13.2.0. After moving to PL 12.6.0 it should continue to work, but you must verify its rendering and interaction in the upgraded UI and watch for any deprecation warnings.

**Q: Will the upgrade cause downtime for users?**
A: The upgrade is limited to the frontend container. If the deployment pipeline uses blue‑green or rolling deployments, user impact can be minimized. However, a brief window may be needed for the new bundle to be served after the build completes.


## Linked Tasks

- UVZUSLNVV-5824 (current upgrade ticket)
- BNUVZ-12529 (analysis comment "how to get to angular 21")