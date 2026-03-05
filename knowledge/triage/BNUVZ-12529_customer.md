# Issue Summary: BNUVZ-12529

**Impact Level:** HIGH
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The UVZ web application currently runs on Angular 18 and Pattern Library 11.3.1. Security support for Angular 18 ends on 21‑Nov‑2025, after which only paid "Never‑Ending Support" is available. To keep the product secure, compliant and avoid additional licensing costs, the front‑end must be upgraded to Angular 19 together with Pattern Library 12.6.0 and all related npm dependencies. If the upgrade is not performed, the application will no longer receive free security patches, exposing it to vulnerabilities and potentially breaching internal security policies.

## Workaround

Continue using Angular 18 with paid Never‑Ending Support, but this incurs extra cost and does not solve the underlying security risk.
