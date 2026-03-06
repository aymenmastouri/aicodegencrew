# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The frontend of the application is being upgraded to Angular 19. As part of that upgrade the SASS compiler that Angular uses has been deprecated and must be switched to the new Angular‑Builder implementation (@angular-devkit/build-angular:application). This migration is required now because the old compiler will no longer be supported in Angular 19, which would cause builds to fail and could introduce regressions in the UI styling. If the migration is not performed, the next scheduled Angular upgrade will break the CI build pipeline and users may see broken or unstyled pages.
