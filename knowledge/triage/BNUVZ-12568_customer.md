# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The front‑end of the product is being upgraded to Angular 19. Angular 19 removes the legacy SASS import mechanism and requires the new SASS compiler that is bundled with the Angular Builder (`@angular-devkit/build-angular:application`). Migrating the build configuration now prevents future build failures, keeps the UI styling pipeline supported, and ensures we stay on a version that receives security and performance updates. If we postpone the migration, the next Angular upgrade will break the CI build and could introduce regressions in the UI appearance.
