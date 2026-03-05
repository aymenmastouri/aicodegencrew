# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

Our web application is built with Angular and uses SASS for styling. The upcoming Angular 19 release removes support for the old SASS compiler that is currently used via the Angular Builder. To keep the application buildable and to avoid future break‑age, we must migrate the build configuration to the new SASS compiler (@angular-devkit/build-angular:application). This migration is required now because the old compiler will be deprecated in Angular 19, which would cause build failures and potentially visual regressions for end‑users. If we postpone the migration, the next major upgrade will be blocked and the UI could stop rendering correctly, leading to a degraded user experience.

## Workaround

Continue building with Angular 18‑lts and the current SASS compiler, but accept that future Angular upgrades will be blocked and the build may eventually fail when Angular 19 is required.
