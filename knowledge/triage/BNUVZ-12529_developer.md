# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a web‑based client application used by internal users to interact with the Capgemini‑hosted services. It is built as a single‑page Angular application (presentation container) that consumes back‑end APIs written in Java 17. The task is to move the front‑end from Angular 18 (and Pattern Library 11.3.1) to Angular 19 and Pattern Library 12.6.0. This upgrade is required now because Angular 18 loses its free security updates on 21 Nov 2025, and the organization wants to stay on a supported stack without paying for a special support contract. If the upgrade is postponed, the application will run on an unsupported framework, creating security and compliance risks.

## Scope Boundary

IN: All Angular packages (core, common, compiler, forms, animations, CLI), TypeScript and Node.js versions, the internal design‑system package bnotk/ds‑ng, ng‑bootstrap (including the specific patch mentioned), ng‑select, ng‑option‑highlight, ag‑grid‑angular, ag‑grid‑community, and the Pattern Library 12.6.0 assets. Verify that the vertical action bar continues to work (it is deprecated but still supported until PL 13.2.0) and remove any leftover code that only belongs to Angular 18/PL 11.3.1. OUT: Back‑end Java services, database schemas, non‑UI infrastructure, unrelated containers, and any feature flags that are not part of the UI stack.

## Affected Components

- UI Root Module (presentation)
- Shared Component Library (presentation)
- Feature Modules (presentation)
- Design‑System Integration (presentation)
- Pattern Library Assets (presentation)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 18.2.13 is out of free security support after 21 Nov 2025; the upgrade to Angular 19 is mandatory to stay on a supported framework.
_Sources: tech_versions.json: Angular 18.2.13_

**[CAUTION] Dependency Risk**
ng‑bootstrap requires a custom patch for the upgrade; the patch must be applied and verified, otherwise UI components may break.
_Sources: Issue description: ng‑bootstrap (Patch von UVZUSLNVV‑5824 muss berücksichtigt werden)_

**[INFO] Pattern Library Constraint**
Pattern Library must be moved from 11.3.1 to 12.6.0; the vertical action bar is deprecated but still functional until PL 13.2.0, so its usage must be confirmed and documented.
_Sources: Issue description: Upgrade to Angular 19 and PL 12.6.0_

**[CAUTION] Technology Constraint**
Node.js and TypeScript versions must be compatible with Angular 19; the current TypeScript 4.9.5 may need to be upgraded to the version required by Angular 19.
_Sources: tech_versions.json: TypeScript 4.9.5_

**[INFO] Testing Constraint**
Existing test runners (Karma, Cypress, Playwright) may need configuration updates to work with Angular 19’s build pipeline.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Cypress 14.0.3, tech_versions.json: Playwright 1.43.1_


## Architecture Walkthrough

The UVZ front‑end lives in the **Presentation container** (one of five containers). Within this container the code is organized into the **presentation layer** (≈202 components) that consume services from the **application layer**. The Angular framework and the Pattern Library are core parts of the presentation layer. The upgrade will touch the **UI Root Module** and all **feature modules** that import Angular core packages, as well as the **shared component library** that wraps the design‑system (bnotk/ds‑ng). Neighboring components include the **application services** (HTTP clients) that remain unchanged, and the **design‑system assets** that must be rebuilt against PL 12.6.0. The vertical action bar is a UI component residing in the shared library; it is deprecated but still allowed until PL 13.2.0, so its module must stay present but can be flagged for future removal.

## Anticipated Questions

**Q: Which Node.js and TypeScript versions are required for Angular 19?**
A: Angular 19 officially supports Node ≥ 18 and TypeScript ~5.2. The current project uses TypeScript 4.9.5, so it will need to be upgraded to the version specified in Angular 19’s release notes. The exact Node version should be aligned with the CI environment and the Angular CLI requirements.

**Q: Are there breaking changes in Angular 19 that could affect our existing code?**
A: Angular 19 introduces several deprecations (e.g., the ViewEngine removal, stricter type checking, and changes to the router lifecycle). All code that still relies on deprecated APIs must be refactored. The vertical action bar is already deprecated but still functional; other components using removed APIs will need updates.

**Q: Do we need to modify the CI/CD pipeline for the new Angular version?**
A: Yes. The Angular CLI version will be updated, which may require changes to the build scripts (e.g., webpack configuration) and to the test runners (Karma, Cypress, Playwright) to ensure they work with the new build output.

**Q: What is the impact of the ng‑bootstrap patch mentioned in the ticket?**
A: The patch contains compatibility fixes for ng‑bootstrap with Angular 19. It must be merged before running the upgrade, and the resulting UI components should be manually tested to confirm that the patch resolves any regressions.

**Q: Is the vertical action bar still allowed after the upgrade?**
A: Yes, the vertical action bar is deprecated but remains supported until Pattern Library 13.2.0. It can stay in the codebase for now, but its usage should be documented and a plan for eventual removal should be created.


## Linked Tasks

- UVZUSLNVV-5824 (current upgrade ticket)
- BNUVZ-12529 (analysis of how to reach Angular 21, referenced for dependency guidance)