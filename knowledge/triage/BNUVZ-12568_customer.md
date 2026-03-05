# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The frontend application is being upgraded to Angular 19. As part of that upgrade the old SASS compiler (the legacy @angular-devkit/build-angular:browser builder) is deprecated and must be replaced with the new SASS compiler provided by @angular-devkit/build-angular:application. Without this migration the build will fail or produce regressions, breaking the UI that customers and internal users rely on. Performing the migration now ensures the application stays buildable, receives future security patches, and avoids unexpected downtime after the Angular 19 release.
