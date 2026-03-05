# Issue Summary: BNUVZ-12529

**Impact Level:** HIGH
**Type:** Enhancement/Task
**Estimated Timeline:** medium

## Summary

The UVZ front‑end currently runs on Angular 18 and Pattern Library 11.3.1. Security support for Angular 18 ends on 21 Nov 2025, after which only paid “Never‑Ending Support” is available. To keep the application secure, compliant and maintainable without extra cost, the front‑end must be upgraded to Angular 19 together with Pattern Library 12.6.0 and all related npm packages. If the upgrade is not performed, the system will no longer receive security patches, exposing it to vulnerabilities and potentially violating internal security policies.

## Workaround

Continue paying for the vendor’s Never‑Ending Support for Angular 18, but this incurs additional cost and does not solve the underlying security risk.
