# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The front‑end of the product is built with Angular. With the upcoming Angular 19 release the old SASS compiler that is currently used by the Angular Builder is deprecated and will no longer be supported. Migrating to the new SASS compiler (@angular-devkit/build-angular:application) is required so that the application can continue to be built and deployed after the Angular upgrade. If the migration is not performed, the build will fail on Angular 19, preventing releases and potentially exposing the team to security and maintenance risks because the old compiler will not receive patches.

## Workaround

Stay on Angular 18 LTS until the migration can be performed, but this postpones the Angular 19 upgrade and blocks future releases.
