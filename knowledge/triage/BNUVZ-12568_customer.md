# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The front‑end of the product is built with Angular 18 and uses the legacy SASS compiler that is tied to the old Angular Builder. Angular 19, which we are scheduled to upgrade to, has removed support for that compiler and requires the new @angular-devkit/build-angular:application builder. Migrating the SASS compilation step is therefore mandatory to keep the application buildable after the Angular version bump, to avoid broken CI pipelines, and to stay on a supported, maintained toolchain. If we skip this migration the next release will fail to compile, developers will be blocked, and future security patches for the build tooling cannot be applied.
