# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The front‑end of the application is being upgraded to Angular 19. Angular 19 removes the old SASS import mechanism and requires the new Angular Builder ( @angular-devkit/build-angular:application ) to compile SASS. Without this migration the application will no longer build after the framework upgrade, which would block any further releases and could expose users to missing UI fixes. The migration therefore ensures the UI can continue to be built, deployed and maintained safely.
