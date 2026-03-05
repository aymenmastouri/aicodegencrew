# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The web‑frontend of the product is currently built with Angular 18 and uses the legacy SASS compiler. Angular 19, which we are planning to adopt, removes support for that compiler and requires the new @angular-devkit/build-angular:application builder. Migrating the SASS compilation step now prevents future build failures, keeps the application on a supported stack, and ensures we continue to receive security patches and performance improvements. If we postpone the migration, the next build after the Angular 19 upgrade will break, delaying releases and increasing the risk of regressions in the UI.
