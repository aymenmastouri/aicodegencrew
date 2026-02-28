# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The frontend of the application is built with Angular and currently uses the legacy SASS compiler that Angular 19 no longer supports. To keep the build pipeline functional and to be able to upgrade to Angular 19 – which brings security patches, performance improvements and new features – the project must migrate to the new SASS compiler provided by the Angular Builder (@angular-devkit/build-angular:application). If the migration is not performed, future Angular upgrades will break the build, deployments will fail and the team will be forced to stay on an outdated Angular version that no longer receives security updates.
