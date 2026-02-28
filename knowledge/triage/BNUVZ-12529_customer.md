# Issue Summary: BNUVZ-12529

**Impact Level:** HIGH
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The UVZ web application currently runs on Angular 18 and Pattern Library 11.3.1. Security support for Angular 18 ends on 21‑Nov‑2025, after which only paid "Never‑Ending Support" updates are available. To keep the application receiving free security patches and to stay on a supported stack, the UI must be upgraded to Angular 19 together with Pattern Library 12.6.0 and all related dependencies. If the upgrade is not performed, the application will become vulnerable to unpatched security issues and may eventually become incompatible with newer browsers or internal tooling.
