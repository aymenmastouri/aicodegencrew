# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The frontend of the application is being upgraded to Angular 19. Angular 19 removes the legacy SASS import mechanism and requires the new SASS compiler that is bundled with the Angular Builder (`@angular-devkit/build-angular:application`). Migrating to this compiler is mandatory to keep the build process functional after the framework upgrade. Without the migration the application will fail to compile, future Angular updates will be blocked and users could experience broken UI or missing styles, which would increase maintenance cost and risk of regressions.
