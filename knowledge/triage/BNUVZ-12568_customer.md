# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The frontend of the application is built with Angular 18 and uses the legacy SASS compiler that will be removed in Angular 19. To keep the product buildable and to stay on a supported stack, the build configuration must be migrated to the new Angular Builder (@angular-devkit/build-angular:application) that ships the updated SASS compiler. Doing this now prevents a future breaking change that would stop the application from compiling after the planned Angular 19 upgrade, avoids release delays, and reduces the risk of regressions caused by an outdated toolchain. If the migration is postponed, the next major version upgrade will fail, forcing an emergency fix and potentially impacting customers who rely on timely releases.
