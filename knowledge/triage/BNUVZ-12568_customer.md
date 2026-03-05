# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The front‑end of the product is built with Angular 18 and the legacy SASS compiler that is part of the old Webpack‑based build chain. Angular 19, which we are scheduled to adopt, drops support for that compiler and requires the new @angular-devkit/build-angular:application builder. Migrating now prevents the build from breaking after the framework upgrade and avoids hidden regressions caused by the deprecated SASS import syntax described in the ADR. If we postpone the migration, the next release will fail to compile, delaying delivery and increasing the risk of runtime style issues for all users of the web application.
