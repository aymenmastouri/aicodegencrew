# Issue Summary: BNUVZ-12529

**Impact Level:** HIGH
**Type:** Enhancement/Task
**Estimated Timeline:** medium

## Summary

The UVZ web application currently runs on Angular 18 and Pattern Library 11.3.1. Security support for Angular 18 ends on 21‑Nov‑2025, after which no patches are provided unless a paid "Never‑Ending Support" contract is taken. To keep the system secure, compliant and maintainable, the UI must be upgraded now to Angular 19 and Pattern Library 12.6.0, together with all required runtime dependencies (Node, TypeScript, ng‑bootstrap, ng‑select, ag‑grid, etc.). If the upgrade is not performed, the application will become vulnerable to security issues and will eventually be unable to receive critical updates, risking compliance failures and potential exploitation.
