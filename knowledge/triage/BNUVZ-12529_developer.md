# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a client‑facing web portal built with Angular and the internal BNOTK Design System (Pattern Library). It lives in the presentation container of a multi‑container, multi‑layer enterprise platform used by internal employees and external partners to access notarisation services. The task is to move the front‑end from Angular 18 (now out of security support) to Angular 19 together with the matching Pattern Library version. This restores security updates, ensures compatibility with upcoming backend releases, and keeps the UI aligned with the design system roadmap. The upgrade is required now because the support window for Angular 18 closes in November 2025; delaying would force the team to purchase expensive extended‑support licences or risk operating an insecure, unsupported UI.

## Scope Boundary

IN: All front‑end code in the presentation container that depends on Angular, the Angular CLI, TypeScript, Node.js, the Pattern Library (PL) and the listed third‑party UI libraries (ng‑bootstrap, ng‑select, ag‑grid). Update of related build scripts, configuration files (webpack, karma), and removal of any leftover Angular 18/PL 11 artefacts. Verify that the vertical action bar component continues to work (it is deprecated but still allowed until PL 13.2.0). 
OUT: Backend services, database schemas, infrastructure provisioning, any non‑UI micro‑services, and any UI components that are explicitly excluded from the upgrade (e.g., custom widgets that are already compatible with Angular 19 and will not be touched).

## Affected Components

- UVZ Front‑End (presentation layer)
- Pattern Library components (presentation layer)
- Vertical Action Bar component (presentation layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 requires a newer TypeScript (≥5.0) and a recent Node.js runtime. The current stack lists TypeScript 4.9.5 and an unspecified Node version, so both must be upgraded before the Angular packages can be upgraded, otherwise the build will fail.
_Sources: tech_versions.json: TypeScript 4.9.5, tech_versions.json: Angular 18‑lts, tech_versions.json: Angular CLI 18‑lts_

**[CAUTION] Dependency Risk**
Third‑party UI libraries (ng‑bootstrap, ng‑select, ag‑grid‑angular, ag‑grid‑community) have specific compatibility matrices with Angular versions. The existing versions are locked to Angular 18; they must be checked for Angular 19 compatibility and possibly upgraded, otherwise runtime errors or compilation failures will occur.
_Sources: dependencies.json: @angular/* v18‑lts, issue description: ng‑bootstrap (Patch von UVZUSLNVV‑5824 muss berücksichtigt werden), issue description: ng‑select/ng‑option‑highlight, ng‑select/ng‑select, ag‑grid‑angular, ag‑grid‑community_

**[INFO] Pattern Constraint**
The vertical action bar component is deprecated but still supported up to Pattern Library 13.2.0. The upgrade to PL 12.6.0 must retain this component; removing it would break existing UI flows.
_Sources: issue description: Vertical action bar is still used (deprecated but possible until PL 13.2.0)_

**[INFO] Testing Constraint**
Current test tooling (Karma 6.4.3, Playwright 1.44.1) may need configuration updates to work with Angular 19’s new compiler output and test harness. Tests must be re‑run after the upgrade to ensure no regressions.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_


## Architecture Walkthrough

The UVZ system is split into 5 containers (e.g., Front‑End, API‑Gateway, Business‑Logic, Data‑Access, Infrastructure). The Angular application lives in the **Front‑End container**, specifically in the **presentation layer** (≈287 components). Within this layer, the UI components consume services from the application layer via well‑defined interfaces. The Pattern Library (PL) is a shared UI component library also consumed by the presentation layer. The vertical action bar is a UI component that interacts with the navigation service in the application layer. Upgrading Angular and PL will affect:
- All presentation components that import `@angular/*` modules.
- Build configuration (webpack, Angular CLI) located in the Front‑End container.
- UI‑only third‑party libraries (ng‑bootstrap, ng‑select, ag‑grid) that are dependencies of presentation components.
- Test suites (Karma, Playwright) that run against the Front‑End bundle.
Neighbouring layers (application, domain) remain untouched, but any API contracts used by the UI must stay stable.
Thus, the developer’s “you are here” map is: **Container: Front‑End → Layer: Presentation → Components: all UI modules + Pattern Library components**, with external dependencies listed above.

## Anticipated Questions

**Q: Which Node.js and TypeScript versions are required for Angular 19?**
A: Angular 19 officially supports Node >=18 LTS and TypeScript 5.0+. The current project uses TypeScript 4.9.5, so both Node.js and TypeScript will need to be upgraded before the Angular packages can be upgraded.

**Q: Are the listed third‑party libraries (ng‑bootstrap, ng‑select, ag‑grid) compatible with Angular 19 out of the box?**
A: Compatibility must be verified against each library’s release notes. Most have released Angular 19‑compatible versions, but the custom ng‑bootstrap patch referenced in the ticket may need to be re‑applied or updated to the new version.

**Q: Do we need to modify the vertical action bar component after the upgrade?**
A: No functional change is required; the component is deprecated but still supported up to PL 13.2.0. Ensure it continues to compile with the new Pattern Library version and that no removed APIs are used.

**Q: Will the existing unit and e2e tests run after the upgrade?**
A: Tests will need to be re‑executed. Karma and Playwright configurations may require minor adjustments for Angular 19’s new compilation output, but the test code itself should remain valid if the UI APIs stay unchanged.

**Q: Is there any impact on backend services or data models?**
A: No. The upgrade only touches the front‑end presentation container and its UI libraries. Backend contracts remain unchanged.


## Linked Tasks

- UVZUSLNVV-5824 (this upgrade ticket)
- BNUVZ-12529 (analysis comment "how to get to angular 21")