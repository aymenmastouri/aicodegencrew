# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The front‑end of the application is being upgraded to Angular 19. Angular 19 removes the old SASS import mechanism and requires the new Angular Builder (`@angular-devkit/build-angular:application`) to compile SASS. Migrating the build configuration now prevents the application from breaking after the framework upgrade and avoids future deprecation warnings. If the migration is not performed, the build will fail or produce incorrect styles, leading to a broken user interface and potential release delays.
