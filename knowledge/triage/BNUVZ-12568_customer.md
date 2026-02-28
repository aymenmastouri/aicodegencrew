# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The frontend of the product is built with Angular 18 and uses the legacy SASS compiler that is tied to the old Angular Builder. With the upcoming upgrade to Angular 19, the old SASS import mechanism is deprecated and the new builder @angular-devkit/build-angular:application must be used. Migrating now prevents the build from breaking after the Angular version bump, keeps the UI styling pipeline functional, and avoids regressions that could affect the look‑and‑feel of the application for end‑users. If the migration is postponed, the next release will fail to compile, delaying delivery and potentially exposing the product to unsupported tooling.
