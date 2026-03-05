# Issue Summary: BNUVZ-12529

**Impact Level:** MEDIUM
**Type:** Enhancement/Task
**Estimated Timeline:** short

## Summary

The UVZ web application currently runs on Angular 18 and Pattern Library 11.3.1. Security support for Angular 18 ends on 21 Nov 2025, after which no free patches are provided. To keep the system safe, compliant and maintainable, we must upgrade the front‑end stack to Angular 19 and Pattern Library 12.6.0 and bring all related libraries (Node.js, TypeScript, ng‑bootstrap, ng‑select, ag‑grid, etc.) up to compatible versions. If we do not upgrade, the application will become vulnerable to unpatched security issues and will eventually require paid “Never‑Ending Support” to stay secure, which is costly and undesirable.

## Workaround

Continue using Angular 18 with paid Never‑Ending Support or accept the security risk, but both are undesirable long‑term solutions.
