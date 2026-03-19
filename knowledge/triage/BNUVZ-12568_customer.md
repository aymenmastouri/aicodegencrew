# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** medium

## Summary

This task initiates the migration of the SASS compiler used in the Angular build pipeline from the legacy `sass` (node-sass) or `sass-loader`-based tooling to the new Angular-native builder-based compiler integrated via `@angular-devkit/build-angular:application`. This change is required as part of the Angular 19 upgrade, which deprecates older SASS compilation strategies. Without this migration, the project will either fail to build after Angular 19 is applied or may produce incorrect styles due to incompatibilities with modern Angular CLI tooling.
