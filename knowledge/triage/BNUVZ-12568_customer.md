# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The frontend of the application is being upgraded to Angular 19. As part of that upgrade the old SASS compiler that is wired through the legacy Angular Builder must be replaced with the new SASS compiler provided by @angular-devkit/build-angular:application. Without this migration the build will fail as Angular 19 no longer supports the previous compiler, which would block the scheduled release and prevent users (internal employees) from receiving the latest features and security patches. The migration is therefore required now to keep the delivery pipeline healthy and to avoid a release delay.
