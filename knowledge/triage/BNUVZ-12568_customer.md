# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** medium

## Summary

The frontend of the product is built with Angular 18 and uses the legacy SASS compiler that is no longer supported in Angular 19. As part of the scheduled Angular 19 upgrade we must switch the build configuration to the new Angular Builder (`@angular-devkit/build-angular:application`) which ships with the updated SASS compiler. Without this migration the application will fail to compile after the framework upgrade, and hidden regressions in styling could appear, breaking the user interface for all customers. Performing the migration now, together with a focused test run, ensures a smooth upgrade path and avoids future build‑breakage.
