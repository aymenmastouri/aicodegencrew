# Issue Summary: BNUVZ-12529

**Impact Level:** HIGH
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The UVZ web application currently runs on Angular 18 and Pattern Library 11.3.1. Security support for Angular 18 ends on 21‑Nov‑2025, after which no free patches are provided. To keep the system secure and maintainable, the frontend must be upgraded to Angular 19 and Pattern Library 12.6.0, together with all required runtime dependencies. If the upgrade is not performed, the application will become vulnerable to unpatched security issues and may eventually be forced into a costly Never‑Ending Support contract.
