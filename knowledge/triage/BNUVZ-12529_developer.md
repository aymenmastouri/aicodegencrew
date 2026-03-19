# Developer Context: BNUVZ-12529

## Big Picture

UVZ (Universeller Verwaltungszugang) is a German federal eGovernment platform used by notaries and public administration to access and manage legal workflows. It relies on Angular for its frontend UI and a custom Pattern Library (ds-ng) for standardized components. This task addresses an urgent need to modernize the core framework stack: Angular 18 is no longer supported for security fixes, and the team must upgrade to Angular 19 (and PL 12.6.0) as the next feasible step before considering Angular 20/21. Without this upgrade, UVZ cannot safely evolve, integrate new features, or meet compliance requirements for long-term maintenance.

## Scope Boundary

{
  "in": [
    "Upgrade Angular from 18 to 19",
    "Upgrade Pattern Library (ds-ng) from 11.3.1 to 12.6.0",
    "Update all listed transitive dependencies (Node.js, TypeScript, ng-bootstrap, ng-select, ag-grid, etc.) as specified in AC2",
    "Ensure vertical action bar continues to function (per AC3)",
    "Remove deprecated Angular 18 / PL 11.3.1 artifacts not supported in target versions (per AC4)",
    "Apply patch for ng-bootstrap referenced in UVZUSLNVV-5824"
  ],
  "out": [
    "Direct upgrade to Angular 20 or 21 (explicitly ruled out per FRM notes)",
    "Backend changes (Java/Gradle stack remains unchanged per issue)",
    "Full regression testing suite (assumed covered by existing CI/CD, but not in scope)",
    "Design/system architecture changes beyond component version alignment"
  ]
}

## Affected Components

- UVZ Frontend (layer: presentation)
- Pattern Library (ds-ng) integration (layer: shared UI library)
- Dependency resolution layer (layer: build tooling)
- ng-bootstrap & ng-select wrappers (layer: third-party integration)
- ag-grid integration (layer: data grid component)
- Angular CLI & build pipeline (layer: tooling)

## Context Boundaries

**[BLOCKING] Technology Constraint**
TypeScript 4.9.5 (current) must be upgraded to a version compatible with Angular 19. Angular 19 requires TypeScript ≥5.4, so this is a hard dependency constraint — the existing TS version cannot remain.
_Sources: Current TypeScript version is 4.9.5_

**[CAUTION] Dependency Risk**
@angular/* packages v18-lts must be upgraded to v19-compatible versions. Since Angular 18 LTS ended 21.11.2025, delaying this upgrade risks dependency drift where newer ng-bootstrap or ag-grid versions may drop v18 support, breaking future upgrades.
_Sources: Current @angular/core version is v18-lts_

**[BLOCKING] Integration Boundary**
The ng-bootstrap patch referenced in UVZUSLNVV-5824 must be applied *during* this upgrade — it is not optional. This indicates a known incompatibility between current ng-bootstrap and Angular 19, so the patch is a prerequisite for AC1.
_Sources: Issue context: ng-bootstrap patch must be considered_

**[CAUTION] Pattern Constraint**
Vertical action bar is deprecated but still usable until PL 13.2.0. Since target is PL 12.6.0, it *must* remain functional. However, any usage of deprecated APIs in PL 11.3.1 that are removed in 12.6.0 would cause runtime breakage — this requires auditing component usage.
_Sources: Issue context: vertical action bar still used; PL 12.6.0 supports it_

**[CAUTION] Infrastructure Constraint**
Node.js version must be upgraded to match Angular 19’s requirements (likely Node 18.x or 20.x). Current Node.js version is not stated, but Angular 18 used Node 16–18; Angular 19 likely requires Node ≥18. Mismatch could break `ng build` or `ng serve`.
_Sources: Issue context: node.js must be updated per AC2_


## Architecture Walkthrough

This task sits at the *foundation layer* of the frontend architecture — it’s a framework migration affecting the entire UI container. UVZ’s frontend is a monolithic Angular app (no micro-frontends yet), built with Webpack 5 and served via Java backend. The upgrade touches the entire dependency tree: all modules (workflow, task, document, etc.) depend on Angular core, CDK, animations, and the custom ds-ng Pattern Library. The build pipeline (CLI/Webpack/Karma/Playwright) must be validated for compatibility. Neighboring components include: (1) backend REST APIs (Java/Gradle), (2) identity providers (PKI auth), and (3) testing infrastructure (Playwright end-to-end tests). The change is *non-functional* but has high ripple potential — every component using Angular APIs, directives, or PL components may need verification.

## Anticipated Questions

**Q: Do I need to update the backend (Java/Gradle)?**
A: No — this is strictly a frontend upgrade. The backend remains on Java 17 and Gradle 8.2.1 per current configuration and issue scope. However, ensure API contracts (e.g., task-module.service.ts) remain compatible with Angular 19’s HttpClient changes (e.g., response type defaults).

**Q: Where is the ng-bootstrap patch referenced in UVZUSLNVV-5824, and how do I apply it?**
A: The patch is referenced as part of the same Jira ticket (UVZUSLNVV-5824). Since the issue explicitly states it 'must be considered', it is likely a temporary workaround (e.g., custom ng-bootstrap fork or patch-package). You should check the ticket comments or ask Filip Misiorek (assigned in BNUVZ-12529) for the exact patch source — it is not in the current codebase by default.

**Q: How do I verify the vertical action bar still works after upgrade?**
A: Verify that the vertical action bar component is used in workflows (e.g., task completion flows). Since it’s deprecated but supported until PL 13.2.0, ensure ds-ng 12.6.0 includes the necessary exports/directives. Run e2e tests covering workflows that use this component.

**Q: Is there a migration path documented for Angular 18 → 19?**
A: Yes — follow the official Angular update guide (https://update.angular.io/). Since Angular upgrades are incremental, go 18 → 19 first (per FRM decision), then later 19 → 20. Use `ng update @angular/core @angular/cli --migrate-only --migrate=18-19` to auto-fix breaking changes where possible.


## Linked Tasks

- BNUVZ-12529
- UVZUSLNVV-5824