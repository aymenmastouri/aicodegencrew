# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The front‑end of the application is built with Angular 18 and uses the legacy SASS compiler that will be removed in Angular 19. To keep the application buildable after the scheduled Angular 19 upgrade, the SASS compilation must be migrated to the new Angular Builder (`@angular-devkit/build-angular:application`). If we do not perform this migration, the build will fail as soon as Angular 19 is upgraded, causing a production‑blocking outage. The migration also requires a round of regression testing to ensure that no visual or functional regressions are introduced by the new compiler.
