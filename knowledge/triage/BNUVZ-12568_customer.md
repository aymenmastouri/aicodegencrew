# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** medium

## Summary

This task tracks the mandatory migration of the SASS compiler used by the Angular build pipeline, required as part of the upcoming Angular 19 upgrade. The migration replaces the legacy SASS compiler with the new `@angular-devkit/build-angular:application` builder, which uses Dart Sass as the default engine. This change is driven by Angular’s evolution toward a unified build system and deprecation of legacy tooling. Without completing this migration, the project cannot successfully upgrade to Angular 19, risking compatibility failures, missing future performance or security fixes, and technical debt accumulation. Although low-risk in isolation, incomplete validation may cause visual regressions due to subtle differences in SASS compilation behavior (e.g., path resolution, variable precedence, or CSS output differences).
