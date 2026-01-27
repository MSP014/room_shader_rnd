# Session End Protocol (Case 01 - RnD Parallax)

"Experiment concluded. Data secured."

1. **Summary**:
    * Briefly summarise what was achieved during the session (Research findings / Code milestones).
    * Update documentation if logic or structure changed.

2. **Dependency Check**:
    * **Caution:** If new packages were installed, run `pip freeze > requirements.txt` (or `pip-compile requirements.in`).
    * Stage the file: `git add requirements.txt`.

3. **Hygiene & Git**:
    * Check `tools/` for temporary scripts. Delete or move to `_deprecated`.
    * Run hooks if in doubt: `pre-commit run --all-files`.
    * Commit message MUST be in **British English**.

4. **Jira**:
    * Use `python tools/jira_link.py` to update statuses.
    * **Log Work:** `python tools/jira_link.py worklog <KEY> <TIME>`.
    * If complete: `python tools/jira_link.py status <KEY> Done`.

5. **Weekly Report**:
    * Write ONE concise sentence in **Russian** for the Friday Report (e.g., "Сформирован MDL граф для Slice-mapping").

6. **Final**:
    * "Optics aligned. Shutting down."
