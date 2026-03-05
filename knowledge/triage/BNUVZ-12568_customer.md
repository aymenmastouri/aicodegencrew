# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The frontend of the application is being upgraded to Angular 19. Angular 19 removes the old SASS import mechanism and requires the new SASS compiler that is built into @angular-devkit/build-angular:application. Migrating to this compiler is necessary so that the UI can continue to be built and deployed after the Angular version bump. If the migration is not performed, the build will fail, developers will be unable to ship UI changes, and hidden regressions could appear in the styling of the application.

## Workaround

Continue using Angular 18 LTS and the current SASS compiler until the migration is completed. This postpones the build break but does not allow the Angular 19 upgrade.
