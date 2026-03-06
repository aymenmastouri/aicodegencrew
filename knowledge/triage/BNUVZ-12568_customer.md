# Issue Summary: BNUVZ-12568

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The frontend of the application is being upgraded to Angular 19. As part of this upgrade the build system must switch to the new SASS compiler that is bundled with the Angular Builder (@angular-devkit/build-angular:application). The current SASS compiler (node‑sass) is deprecated and will no longer be supported, so without the migration future builds would fail and styling could break. Updating now prevents build breakage, keeps the UI looking correct, and avoids regressions after the Angular version bump.
