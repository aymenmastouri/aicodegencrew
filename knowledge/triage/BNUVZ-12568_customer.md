# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The front‑end of the application is being upgraded to Angular 19. Angular 19 drops support for the legacy SASS compiler that is currently used via the old Webpack‑based builder. To keep the application buildable, avoid compile‑time failures and stay on a supported, secure build stack, the project must migrate to the new SASS compiler that is bundled with the Angular Builder (`@angular-devkit/build-angular:application`). If this migration is not performed, the next release of the application will fail to compile after the Angular 19 upgrade, leading to blocked releases and possible regressions in styling.
