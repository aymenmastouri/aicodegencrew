# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The front‑end application is being upgraded to Angular 19. Angular 19 removes the old SASS import mechanism and requires the new SASS compiler that is provided by the Angular Builder (`@angular-devkit/build-angular:application`). If we keep the old compiler the build will fail and future Angular updates will be blocked, which could cause production outages and prevent us from receiving security patches. Migrating now avoids a broken build pipeline, reduces the risk of regressions, and keeps the UI styling pipeline compatible with the next major framework version.

## Workaround

Continue to run the application on Angular 18 with the existing SASS compiler, but this will prevent the planned Angular 19 upgrade and may cause build failures when the old compiler is finally removed.
