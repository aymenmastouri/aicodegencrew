# Issue Summary: BNUVZ-12529

**Impact Level:** HIGH
**Type:** Enhancement/Task
**Estimated Timeline:** medium

## Summary

The UVZ web application is currently built with Angular 18, which will stop receiving security updates after November 2025. The task is to upgrade the front‑end to Angular 19 and to move the shared Pattern Library from version 11.3.1 to 12.6.0. This also requires updating a set of related npm packages (Node.js, TypeScript, ng‑bootstrap, ng‑select, ag‑grid, etc.) while keeping the vertical action bar that is still supported for now. It is a planned refactor, not a defect.
