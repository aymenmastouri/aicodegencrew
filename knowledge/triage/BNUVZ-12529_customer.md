# Issue Summary: BNUVZ-12529

**Impact Level:** HIGH
**Type:** Enhancement/Task
**Estimated Timeline:** medium

## Summary

The UVZ web‑application currently runs on Angular 18 and Pattern Library 11.3.1. Angular 18 will stop receiving free security updates on 21 Nov 2025, leaving the system exposed unless the customer pays for a Never‑Ending Support contract. Upgrading to Angular 19 together with Pattern Library 12.6.0 restores regular security patches, aligns the UI stack with the supported versions of its third‑party libraries, and prevents future compliance and maintenance problems. If the upgrade is not performed, the application will become vulnerable to known security issues and may eventually require costly paid support or a forced emergency migration.

## Workaround

Continue to pay for the Never‑Ending Support contract for Angular 18, but this incurs additional cost and does not solve the underlying obsolescence of the UI stack.
