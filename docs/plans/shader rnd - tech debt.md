# Technical Debt: Shader RnD

## Active Issues

### 2. Missing Pre-commit Hooks Configuration

**Status**: Active (Detected 2026-02-26) вљ пёЏ
**Severity**: High
**Detected**: 2026-02

**Current State:**

- The `.flake8` linter configuration file has been copied to the root directory to enforce the NVIDIA Showreel Standard.
- Pre-commit hooks are currently unverified.

**Issue:**
Code committed in the RnD folder might bypass the global Showreel linting and formatting standards if `pre-commit` is not installed and configured properly in the `shader_rnd` environment.

**Action Required:**

1. **Verify Installation:** Ensure `pre-commit` is installed in the `shader_rnd` environment (`pip show pre-commit`).
2. **Install Hooks:** Run `pre-commit install` in the repository root to bind the hooks to the local git operations.
3. **Verify Configuration:** Ensure `.pre-commit-config.yaml` is present and correctly configured to use at least:
   - `flake8`
   - `black` (or equivalent formatter)
   - `isort`
4. **Test Run:** Execute `pre-commit run --all-files` to format existing code and verify the hooks are operational.

**Resolution Timeline:**
Immediate action required before the next code submission.

---

### 1. Pip Version Lock (pip-tools compatibility)

**Status**: Active (Verified 2026-02-13) вњ…
**Severity**: Medium
**Detected**: 2026-02

**Current State:**

- pip version: **25.2** вњ… (within safe range)
- pip-tools version: **7.3.0** вњ… (working)
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
Expected fix by end of Feb 2026 вЂ” **monitor for updates**

**Last Verified:** 2026-02-13

---

## Resolved Issues

None yet
