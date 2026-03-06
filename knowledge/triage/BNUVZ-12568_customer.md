# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** medium

## Summary

The front‑end application is being upgraded to Angular 19. As part of that upgrade the SASS compilation process must switch from the legacy compiler to the new Angular Builder compiler (@angular-devkit/build-angular:application). This change is required because the old compiler is deprecated in Angular 19 and will no longer be supported, which would break the build pipeline and prevent future releases. Performing the migration now avoids a sudden breakage after the Angular version bump and gives the team time to run additional tests to catch any regressions caused by the new compiler’s handling of SASS imports.
