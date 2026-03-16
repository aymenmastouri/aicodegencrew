# Issue Summary: BNUVZ-12568

**Impact Level:** HIGH
**Type:** Enhancement/Task
**Estimated Timeline:** medium

## Summary

This task is part of the Angular 19 upgrade effort and involves migrating the SASS compilation pipeline from the legacy Angular builder to the new `@angular-devkit/build-angular:application` builder. This migration is required because Angular 19 deprecates the old SASS compiler behavior (e.g., `@import` handling changes), and continued use of the old setup may cause build failures or incorrect styling after upgrading. Without this change, the frontend could render incorrectly or fail to build, impacting all user-facing UI components. The team also explicitly warns that additional testing is needed — indicating this is not just a version bump, but a behavioral change with potential side effects.
