# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The web application is built with Angular 18 and uses SASS for styling. Angular 19 introduces a new built‑in SASS compiler that is only available through the @angular-devkit/build-angular:application builder. To keep the application up‑to‑date, avoid build failures, and stay compliant with the deprecation of the old SASS import mechanism, the front‑end build configuration must be migrated now. If the migration is not performed, the next major Angular upgrade will break the build pipeline, causing delays and possible regressions in the UI.
