# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** medium

## Summary

This task migrates the frontend build pipeline from the legacy SASS compiler to the new Angular-native SASS compiler bundled with @angular-devkit/build-angular:application, required as part of the upcoming Angular 19 upgrade. The change affects how SCSS styles are compiled and imported — particularly deprecating legacy `@import`-based SASS imports in favor of modern `@use`/`@forward` syntax. If not done, the project will be incompatible with Angular 19 and may face runtime styling issues or build failures post-upgrade. Additionally, regression risk exists due to subtle differences in SASS resolution behavior between compilers.
