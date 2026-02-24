# Issue Summary: VVZ-2998

**Impact Level:** HIGH
**Type:** Bug
**Estimated Timeline:** unknown

## Summary

When a JSON file is imported, the system initially shows the imported organisation (e.g., "Sparkasse") correctly. However, after opening the record for editing and saving it, the organisation disappears from the participants list and from the related booking fields. The system also incorrectly allows a custody‑mass (VM) that is marked as faulty to be saved, which should be blocked.
