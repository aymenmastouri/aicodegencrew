# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** medium

## Summary

The frontend application is being upgraded to Angular 19. Angular 19 removes the old SASS compiler that was used by the previous Angular Builder and requires the new builder @angular-devkit/build-angular:application. Migrating to this compiler is necessary to keep the build process working after the framework upgrade, to avoid compilation errors and to stay on a supported, security‑patched toolchain. If the migration is not performed, the application will fail to build once Angular 19 is released, blocking any further releases and potentially exposing the project to unpatched SASS tooling.
