# Developer Context: BNUVZ-12529

## Big Picture

UVZ is a web‑based application whose user interface is built with Angular and a shared Pattern Library (PL) that provides UI components. The front‑end is consumed by internal users and external customers who interact with the system through browsers. This task upgrades the UI stack from Angular 18 / PL 11.3.1 to Angular 19 / PL 12.6.0 so that the product remains under vendor security support, can receive future bug‑fixes, and stays aligned with the roadmap that forbids a direct jump to Angular 20/21. Without the upgrade the application would lose free security updates after November 2025, exposing it to potential vulnerabilities and forcing the team into an expensive support contract.

## Scope Boundary

IN: • Upgrade Angular core, Angular CLI, RxJS, Webpack, Karma to versions compatible with Angular 19. • Update Node.js and TypeScript to the minimum versions required by Angular 19. • Upgrade Pattern Library to 12.6.0 and adjust any PL‑specific imports. • Update runtime dependencies listed in the acceptance criteria (bnotk/ds‑ng, ng‑bootstrap with its patch, ng‑select, ag‑grid‑angular, ag‑grid‑community). • Verify that the vertical action bar continues to function (it is deprecated but still supported up to PL 13.2.0). • Remove code that is only needed for Angular 18 / PL 11.3.1, unless still required by the new versions.
OUT: • Any backend Java services, database schema, or infrastructure components. • Non‑UI related libraries not mentioned in the acceptance criteria. • Feature work unrelated to the upgrade (e.g., new UI screens).

## Affected Components

- All Angular UI components (presentation layer)
- Pattern Library integration module (presentation layer)
- VerticalActionBarComponent (presentation layer)

## Context Boundaries

**[BLOCKING] Technology Constraint**
Angular 19 requires Node.js ≥ 18 and TypeScript ≥ 5.2. The current stack uses Node.js (unspecified) and TypeScript 4.9.5, so the runtime environment must be upgraded before the Angular packages can be installed.
_Sources: tech_versions.json: TypeScript 4.9.5, tech_versions.json: Angular 18-lts_

**[CAUTION] Dependency Risk**
ng-bootstrap has a custom patch referenced in the ticket; that patch was created for Angular 18 and may not be compatible with Angular 19, requiring verification or a new patch.
_Sources: Issue description: ng-bootstrap (Patch von UVZUSLNVV-5824 muss berücksichtigt werden)_

**[INFO] Dependency Risk**
Pattern Library 12.6.0 deprecates the vertical action bar after PL 13.2.0. The upgrade must ensure the component still works and that no hidden breaking changes are introduced.
_Sources: Issue description: Vertical action bar is still being used (deprecated but still possible to use till PL 13.2.0)_

**[CAUTION] Technology Constraint**
Angular 19 upgrades RxJS to a newer major version; existing code that relies on RxJS 7.8.2 APIs must be checked for compatibility, especially any custom operators or pipe usage.
_Sources: tech_versions.json: RxJS 7.8.2, tech_versions.json: Angular 18-lts_


## Architecture Walkthrough

The UVZ system is split into five containers. The front‑end container hosts the presentation layer (≈287 components) built with Angular. Within this container, the Angular application imports the Pattern Library (shared UI component library) and communicates with backend services via HTTP/REST (application layer). The upgrade work is confined to the front‑end container, specifically the presentation layer components that depend on Angular core, Angular CLI, Webpack, Karma, and the Pattern Library. Neighboring components include:
- Service proxies in the application layer (unchanged). 
- Shared UI components from bnotk/ds‑ng and the Pattern Library (must be updated to the new PL version). 
- Third‑party UI widgets (ng‑bootstrap, ng‑select, ag‑grid) that sit alongside the Angular core. 
The developer will be "here": inside the front‑end container, updating the Angular version and all listed dependencies, then rebuilding the bundle with Webpack and re‑running the Karma test suite. No changes are required in the Java backend container or the infrastructure container.

## Anticipated Questions

**Q: What Node.js and TypeScript versions are required for Angular 19?**
A: Angular 19 officially supports Node.js 18 LTS (or newer) and TypeScript 5.2+. The current project uses TypeScript 4.9.5, so both Node.js and TypeScript must be upgraded before the Angular packages can be installed.

**Q: Is the existing ng‑bootstrap patch compatible with Angular 19?**
A: The patch was created for Angular 18. Compatibility must be verified; if it breaks, a new patch or an upgrade to a newer ng‑bootstrap version that supports Angular 19 will be required.

**Q: Do we need to adjust the build pipeline (Webpack, Karma) for the new Angular version?**
A: Yes. Angular 19 may introduce changes to the Angular CLI build process and to the test runner configuration. Webpack and Karma versions should be reviewed and updated if they are not compatible with the new CLI.

**Q: How can we confirm that the vertical action bar still works after the upgrade?**
A: Run the existing UI test suite that covers the vertical action bar, and manually verify the component in the Storybook (which still includes it up to PL 13.2.0). Any deprecation warnings should be logged but are not blockers until PL 13.2.0.

**Q: Will RxJS updates cause breaking changes in our code?**
A: Angular 19 may upgrade RxJS to a newer minor version. Review the RxJS changelog for any removed operators or changed typings. Focus on custom pipe implementations and ensure they still compile with the upgraded RxJS version.


## Linked Tasks

- BNUVZ-12529 (analysis comment "how to get to angular 21")
- UVZUSLNVV-5824 (this ticket itself)