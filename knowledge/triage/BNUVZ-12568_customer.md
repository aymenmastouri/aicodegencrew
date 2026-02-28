# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** medium

## Summary

The frontend of the application is being upgraded to Angular 19. As part of that upgrade the SASS compiler that is used by the Angular build system has been replaced by the new Angular‑Builder implementation (@angular-devkit/build-angular:application). The existing build configuration (Angular 18‑LTS) relies on the old compiler, which will no longer be supported once the framework is moved to version 19. Migrating the SASS compiler now prevents future build failures, keeps the UI styling pipeline up‑to‑date, and avoids hidden regressions that could surface after the framework upgrade. If the migration is postponed, the next CI run after the Angular upgrade will fail, delaying releases and potentially exposing the product to security‑related deprecations of the old tooling.

## Workaround

Continue building the application with Angular 18‑LTS until the migration is completed; however, no new features or bug‑fixes should be released with the old compiler because the next framework upgrade will break the build.
