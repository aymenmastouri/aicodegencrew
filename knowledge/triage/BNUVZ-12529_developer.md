# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a client‑facing web portal built with Angular. It is used by internal users and external partners to access services provided by the backend (Java 17, Gradle). The portal’s UI lives in the presentation layer of the overall system architecture and consumes REST APIs from the application layer. This task upgrades the front‑end framework from Angular 18 to Angular 19 and updates the shared Pattern Library from 11.3.1 to 12.6.0. The upgrade is required now because Angular 18 loses security support on 21 Nov 2025, and the client wants to stay on a supported stack without paying for a special support contract. If the upgrade is postponed, the portal will become a security liability and may need an emergency migration later.

## Scope Boundary

IN: • Upgrade Angular core, Angular CLI, RxJS, and all Angular packages to the 19 release. • Update Node.js and TypeScript to the versions required by Angular 19. • Upgrade Pattern Library to 12.6.0. • Update all UI‑related third‑party libraries (ng‑bootstrap, ng‑select, ag‑grid‑angular, ag‑grid‑community) to versions compatible with Angular 19, including the custom ng‑bootstrap patch referenced in this ticket. • Verify that the vertical action bar (deprecated but still supported until PL 13.2.0) continues to work. • Remove any code, components, or styles that are only needed for Angular 18/PL 11.3.1 and are not required by the new versions. • Run the full UI test suite (Karma, Playwright) and adjust configurations as needed.
OUT: • Backend Java services, database schema, and infrastructure (Docker, CI pipelines unrelated to the front‑end build). • Non‑UI libraries that are not part of the Angular or Pattern Library stack. • Feature work unrelated to the upgrade (new UI screens, business logic changes).

## Affected Components

- Angular UI components (presentation layer)
- Pattern Library integration module (presentation layer)
- Vertical Action Bar component (presentation layer)
- ng-bootstrap wrapper components (presentation layer)
- ag‑grid wrappers (presentation layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 18 LTS loses security support on 21 Nov 2025, making the current stack non‑compliant. The upgrade to Angular 19 is therefore mandatory to retain regular security patches.
_Sources: tech_versions.json: Angular 18-lts_

**[CAUTION] Dependency Risk**
Several UI libraries (ng‑bootstrap, ng‑select, ag‑grid) must be upgraded to versions that are compatible with Angular 19. The ng‑bootstrap library also requires a custom patch referenced in this ticket; missing the patch will cause runtime errors.
_Sources: Issue description: ng‑bootstrap (Patch von UVZUSLNVV-5824 muss berücksichtigt werden)_

**[INFO] Pattern Library Version**
Pattern Library 11.3.1 is deprecated; moving to 12.6.0 introduces new component APIs and removes old ones. The vertical action bar is deprecated but remains functional until PL 13.2.0, so it can stay for now but should be monitored.
_Sources: Issue acceptance criteria: Upgrade to Pattern Library 12.6.0; vertical action bar still usable until PL 13.2.0_

**[CAUTION] Testing Constraint**
The current test stack (Karma 6.4.3, Playwright 1.44.1) may have compatibility issues with Angular 19 and the updated libraries. Test configuration files and possibly test code will need verification and minor adjustments.
_Sources: tech_versions.json: Karma 6.4.3, tech_versions.json: Playwright 1.44.1_

**[BLOCKING] Technology Constraint**
Angular 19 requires Node.js ≥ 18 and TypeScript ≥ 5.0. The project currently uses Node.js/TS versions aligned with Angular 18 (TS 4.9.5). These must be upgraded before the Angular upgrade can succeed.
_Sources: Analysis Input: Technology Stack – TypeScript 4.9.5, Issue acceptance criteria: node.js, typescript_


## Architecture Walkthrough

The UVZ front‑end lives in the **frontend container** (one of the five system containers). Within that container it belongs to the **presentation layer** (≈287 components). The Angular application is the entry point (main.ts) and loads UI components that are built on top of the **Pattern Library** (shared UI component library). Key neighbours: • Application‑layer services that expose REST endpoints (HTTP client calls). • Infrastructure‑layer configuration (webpack, Angular CLI). • Testing infrastructure (Karma, Playwright) that runs in the CI pipeline. The upgrade will touch the Angular core packages, the Pattern Library module, and all UI components that depend on them, but it does not cross the container boundary into the backend Java services.

## Anticipated Questions

**Q: Which Node.js and TypeScript versions are required for Angular 19?**
A: Angular 19 requires Node.js ≥ 18.x and TypeScript ≥ 5.0. The current project uses TypeScript 4.9.5, so both Node.js and TypeScript will need to be upgraded before the Angular packages can be updated.

**Q: Are there breaking changes in Angular 19 that could affect our existing code?**
A: Angular 19 deprecates several APIs that were still available in 18, such as the vertical action bar component (still usable until PL 13.2.0). Most components will continue to work, but any usage of removed APIs must be refactored. The upgrade checklist in the Angular migration guide should be consulted.

**Q: Do we need to modify the CI/CD pipeline after the upgrade?**
A: Yes. The Angular CLI version will change, which may affect build scripts and webpack configuration. Additionally, Karma and Playwright versions may need to be aligned with Angular 19, so the CI steps that run tests will have to be verified.

**Q: What is the status of the custom ng‑bootstrap patch mentioned in the ticket?**
A: The patch is part of this ticket (UVZUSLNVV‑5824) and must be applied to the ng‑bootstrap library after it is upgraded to a version compatible with Angular 19. Failing to apply it will likely cause runtime errors in components that rely on ng‑bootstrap.

**Q: Will the vertical action bar continue to work after the upgrade?**
A: Yes. The vertical action bar is deprecated but still supported in Pattern Library 12.6.0 and will remain functional until PL 13.2.0, as stated in the acceptance criteria.


## Linked Tasks

- UVZUSLNVV-5824 (custom ng‑bootstrap patch)
- BNUVZ-12529 (analysis of how to reach Angular 21 – provides additional dependency insights)