# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The frontend of the application is being upgraded to Angular 19. As part of that upgrade the SASS compilation must be switched to the new Angular Builder (`@angular-devkit/build-angular:application`). The current build uses the old SASS compiler that will be deprecated in Angular 19, so without this migration the application could fail to build or produce broken styles after the framework upgrade, leading to regressions in the UI. Performing the migration now prevents build breakage and ensures the UI continues to render correctly after the Angular version bump.
