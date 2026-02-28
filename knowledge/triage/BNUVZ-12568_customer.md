# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The application is being upgraded to Angular 19. Angular 19 removes the legacy SASS compiler and requires the new @angular-devkit/build-angular:application builder. To keep the UI buildable and avoid a broken production pipeline, the SASS compilation step must be migrated now. If we do not migrate, the next build after the Angular upgrade will fail, UI changes will not be compiled, and users could see missing styles or broken pages.

## Workaround

Continue using Angular 18 and postpone the Angular 19 upgrade, but this postpones the overall release schedule.
