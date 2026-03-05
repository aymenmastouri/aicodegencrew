# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The front‑end of the application is built with Angular 18 and uses the legacy SASS compiler that is tied to the old Angular Builder. Angular 19 – which the product roadmap requires – removes that compiler and mandates the new @angular-devkit/build-angular:application builder. Migrating the SASS compilation step now prevents future build failures, keeps the UI styling pipeline supported, and avoids regressions that would appear as soon as the Angular version is upgraded. If the migration is not performed, the next major release will break the CI build and any developer trying to run the app locally will encounter compilation errors, delaying releases and increasing maintenance cost.
