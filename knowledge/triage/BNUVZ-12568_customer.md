# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The front‑end of the product is being upgraded to Angular 19. Angular 19 removes the old SASS compilation path and requires the new Angular Builder ( @angular-devkit/build-angular:application ) to compile SCSS files. Without this migration the application will no longer build after the framework upgrade, which would block any further releases and could cause downtime for users. The migration is therefore needed now to keep the build pipeline functional and to avoid future regressions caused by the deprecated SASS import strategy.
