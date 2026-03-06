# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** medium

## Summary

The frontend of the application is being upgraded to Angular 19. As part of that upgrade the SASS compiler must be switched to the new Angular‑Builder implementation (@angular-devkit/build-angular:application). The current compiler is deprecated and will no longer be supported in Angular 19, so keeping it would break the build after the framework upgrade. Migrating now avoids a broken build pipeline and prevents downstream regressions in the UI styling. If the migration is not performed, the next scheduled Angular 19 release will fail to compile the project, halting deployments and forcing an emergency fix later.
