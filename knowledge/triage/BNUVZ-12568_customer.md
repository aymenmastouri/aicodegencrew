# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The frontend of the application is being upgraded to Angular 19. As part of that upgrade the SASS compiler that turns our SCSS files into CSS must be switched to the new Angular‑Builder implementation (@angular-devkit/build-angular:application). The current compiler is deprecated and will no longer be supported in Angular 19, so without the migration future builds could fail or produce incorrect styles, breaking the user interface for all customers. Performing the migration now, together with the recommended regression testing, ensures a smooth upgrade path and prevents UI regressions after the Angular version change.
