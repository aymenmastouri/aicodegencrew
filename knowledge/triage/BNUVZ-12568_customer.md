# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

This task migrates the project’s SASS compilation pipeline from the legacy Angular SASS builder to the new `@angular-devkit/build-angular:application` builder introduced in Angular 19. This change is required to align with the upcoming Angular 19 upgrade and follows a documented architectural decision (ADR UVZ-09-ADR-003). Without this migration, the project will not be compatible with Angular 19, potentially blocking the upgrade and exposing the team to build-time failures or inconsistent styling behavior. Additional testing is explicitly required to catch regressions in styling or build output.
