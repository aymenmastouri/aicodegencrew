# Issue Summary: BNUVZ-12529

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** medium

## Summary

The UVZ web application currently runs on Angular 18 and Pattern Library 11.3.1. Security support for Angular 18 ends on 21‑Nov‑2025, after which no free patches are provided. To keep the system safe and compliant, the client must move to a supported stack. Upgrading to Angular 19 and Pattern Library 12.6.0 restores security updates, aligns with the vendor’s roadmap, and prevents the need for costly “Never‑Ending Support” contracts. If the upgrade is not performed, the application will become vulnerable to unpatched security issues and may eventually violate internal compliance policies.

## Workaround

Continue on Angular 18 only by purchasing Never‑Ending Support from the vendor, which incurs additional cost and does not solve the underlying deprecation of the framework.
