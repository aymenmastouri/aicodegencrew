# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The application is being upgraded to Angular 19. Angular 19 removes the old SASS compiler that was used through the legacy Webpack builder and requires the new Angular‑Builder (`@angular-devkit/build-angular:application`). Migrating to this compiler is mandatory because the old compiler will no longer be supported, causing the build to fail and preventing future Angular updates. Performing the migration now avoids a broken build pipeline, keeps the UI styling pipeline functional, and reduces the risk of regressions after the major framework upgrade. If the migration is not done, the CI/CD build will break, developers will be unable to compile the UI, and the project will be stuck on an unsupported Angular version.
