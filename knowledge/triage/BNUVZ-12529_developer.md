# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a client‑facing web portal built with Angular (presentation layer) that consumes backend services written in Java 17. End users are internal staff and external partners who use the portal for document handling and workflow management. This task upgrades the UI framework from Angular 18 to Angular 19 and updates the shared Pattern Library to version 12.6.0. The upgrade is required now because Angular 18 loses security support on 21‑Nov‑2025, leaving the portal exposed to vulnerabilities and forcing a paid support contract. Without the upgrade, the portal would gradually become insecure and could be forced out of compliance with corporate security policies.

## Scope Boundary

IN: All Angular packages (core, common, compiler, etc.), Angular CLI, TypeScript, Node.js version, Pattern Library 12.6.0, third‑party UI libs (ng‑bootstrap, ng‑select, ag‑grid), removal of any code that only works with Angular 18/PL 11.3.1, verification that the vertical action bar still functions. OUT: Backend Java services, database schema, non‑UI infrastructure, unrelated third‑party libraries not listed, new feature development, extensive test‑suite rewrites beyond compatibility adjustments.

## Affected Components

- UVZ Frontend Application (presentation)
- Pattern Library Integration (presentation)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 requires Node.js ≥ 18 and TypeScript ≥ 5.0. The current stack lists Node.js (unspecified) and TypeScript 4.9.5, so both must be upgraded before the framework can be compiled.
_Sources: tech_versions.json: Angular 18-lts, tech_versions.json: TypeScript 4.9.5_

**[CAUTION] Dependency Risk**
Third‑party UI libraries (ng‑bootstrap, ng‑select, ag‑grid) have specific compatibility matrices with Angular versions. The ticket explicitly mentions a patch for ng‑bootstrap that must be retained, indicating that the current version may not be compatible with Angular 19 out‑of‑the‑box.
_Sources: issue_context: ng-bootstrap (Patch von UVZUSLNVV-5824 muss berücksichtigt werden), issue_context: ng-select/ng-option-highlight, ng-select/ng-select, ag-grid-angular, ag-grid-community_

**[INFO] Pattern Constraint**
The vertical action bar component is deprecated but still supported up to Pattern Library 13.2.0. After the upgrade to PL 12.6.0 it must continue to work, but any removal before PL 13.2.0 would break existing UI flows.
_Sources: issue_context: Vertical action bar is still used (deprecated but possible until PL 13.2.0)_

**[CAUTION] Testing Constraint**
Current test tooling (Karma 6.4.3, Playwright 1.44.1) may need configuration updates for Angular 19, especially for Angular TestBed APIs that changed between v18 and v19.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_


## Architecture Walkthrough

The UVZ system consists of 5 containers. The frontend lives in the **Presentation** container (≈287 components) and communicates with the backend via HTTP APIs. Within this container, the Angular application is the core component, built with Angular CLI and bundled by Webpack. The Pattern Library (PL) is a shared UI component library also consumed by the presentation layer. Upgrading Angular touches the core Angular component, all Angular‑specific services, and any UI components that depend on the PL. Neighboring components include: • Backend API services (application layer) – unchanged; • Shared utility libraries (infrastructure layer) – may need TypeScript version alignment; • Test harnesses (Karma, Playwright) – located in the same container but separate testing layer. The developer’s work will be confined to the presentation container, updating the Angular core, its CLI, the PL version, and the listed third‑party UI libs, while ensuring the vertical action bar continues to render.

## Anticipated Questions

**Q: Which Node.js version do we need for Angular 19?**
A: Angular 19 officially supports Node.js 18 LTS and newer. Verify the CI/CD pipeline uses at least Node.js 18; upgrade the local development environment accordingly.

**Q: Do we have to upgrade TypeScript as part of this upgrade?**
A: Yes. Angular 19 requires TypeScript 5.0 or higher. The current project uses TypeScript 4.9.5, so the tsconfig and any type‑dependent code must be updated to the newer compiler.

**Q: Are there breaking API changes in Angular 19 that could affect our code?**
A: Angular 19 deprecates several APIs that were still present in 18 (e.g., certain lifecycle hooks and deprecated router methods). Review the Angular migration guide for v19 and run the Angular update schematic; it will flag usages that need refactoring.

**Q: What is the status of the vertical action bar after the upgrade?**
A: The vertical action bar is deprecated but remains supported until PL 13.2.0. After moving to PL 12.6.0 it must still function; no removal is required now, but future upgrades should plan for its replacement.

**Q: Will our current versions of ng‑bootstrap, ng‑select, and ag‑grid work with Angular 19?**
A: Compatibility must be verified against each library’s release notes. The ticket notes a specific patch for ng‑bootstrap that must be kept, indicating that the out‑of‑the‑box version may not be compatible. Check the latest versions of ng‑bootstrap, ng‑select, and ag‑grid that declare Angular 19 support and apply the required patch.


## Linked Tasks

- BNUVZ-12529 (analysis comment "how to get to angular 21")
- UVZUSLNVV-5824 (current ticket)