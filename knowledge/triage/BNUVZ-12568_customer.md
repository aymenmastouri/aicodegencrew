# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The web application is being upgraded to Angular 19. Angular 19 removes the legacy SASS compiler that the current build uses (via Webpack) and requires the new Angular Builder (@angular-devkit/build-angular:application) which ships with the Dart‑Sass compiler. Migrating the SASS compilation step is necessary so the application can be built and released after the Angular upgrade. If the migration is not performed, the build will fail, preventing the release of new features and security patches, and could introduce regressions in the UI styling.

## Workaround

Continue building with Angular 18 until the migration is completed; however the project cannot be upgraded to Angular 19 without fixing the SASS compiler configuration.
