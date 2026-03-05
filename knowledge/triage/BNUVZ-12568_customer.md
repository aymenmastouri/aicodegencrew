# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** medium

## Summary

The frontend of the application is being upgraded to Angular 19. As part of this upgrade the SASS compiler that is used by the Angular build process must be switched to the new Angular‑Builder implementation (@angular-devkit/build-angular:application). The current compiler is deprecated and will no longer be supported in Angular 19, so without the migration future builds could fail or produce incorrect CSS, leading to visual regressions for end‑users. Performing the migration now, together with the recommended extra testing, ensures a smooth upgrade path and avoids regressions after the Angular version bump.
