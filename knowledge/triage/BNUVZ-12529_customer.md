# Issue Summary: BNUVZ-12529

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The UVZ web application currently runs on Angular 18 and Pattern Library 11.3.1. Security support for Angular 18 ends on 21 Nov 2025, after which the product will no longer receive free security patches. To keep the application safe and compliant, the front‑end must be upgraded to Angular 19 together with Pattern Library 12.6.0, and all related UI libraries must be aligned to the new versions. If the upgrade is not performed, the system will become vulnerable, may require costly "Never‑Ending Support" contracts, and could eventually break when newer browsers or third‑party components drop support for the old stack.

## Workaround

Continue paying for Never‑Ending Support from the vendor, but this incurs additional cost and does not solve the underlying obsolescence.
