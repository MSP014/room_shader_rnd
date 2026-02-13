# Technical Debt: Shader RnD

## Active Issues

### 1. Pip Version Lock (pip-tools compatibility)

**Status**: Active (Verified 2026-02-13) ✅
**Severity**: Medium
**Detected**: 2026-02

**Current State:**

- pip version: **25.2** ✅ (within safe range)
- pip-tools version: **7.3.0** ✅ (working)
- Constraint: **pip <= 25.3**

**Issue:**
`pip 26.0+` breaks `pip-tools` (dependency management tool used for `requirements.txt` compilation).

**Action Required:**

1. **DO NOT upgrade pip to 26.0+** until pip-tools compatibility is confirmed
2. Monitor pip-tools GitHub for 26.x compatibility updates
3. Safe to upgrade within 25.x range (currently on 25.2)

**Mitigation:**

- Current pip version is safe (25.2 < 25.3)
- Document constraint in setup instructions
- Check <https://github.com/jazzband/pip-tools> for pip 26.x support

**Resolution Timeline:**
Expected fix by end of Feb 2026 — **monitor for updates**

**Last Verified:** 2026-02-13

---

## Resolved Issues

None yet
