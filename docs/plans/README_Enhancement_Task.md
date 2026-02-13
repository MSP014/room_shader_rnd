# Task: README Structural Enhancement (RnD - Room Map Shader)

**Assigned to:** Quentin
**Priority:** Medium
**Estimated Effort:** 15 minutes
**Context:** Global README standardisation based on Gilfoyle's (Case 03) gold standard

---

## 🎯 Objective

Enhance the structural presentation of `README.md` by adding a **Technical Stack** section. This is a **structure-only** update — your research narrative and content remain untouched.

---

## 📋 What to Do

### 1. Add "Technical Stack" Section

**Location:** Insert before `## 📜 Changelog` (at the bottom of the file)

**Content:**

```markdown
## 📜 Technical Stack

* **Python**: 3.10
* **NVIDIA MDL**: Core shader language
* **Houdini**: 21.0.596 (Karma, VEX)
* **Omniverse**: 2024.x (MDL runtime)
```

**Why:**

- Creates a **quick compatibility matrix** for collaborators checking requirements
- Highlights your unique focus (MDL + Karma) — the research toolset
- Mirrors Gilfoyle's pattern for consistency across the Estate

---

## 🤔 Why This Matters

**Current state:** Your stack is mentioned only in the top blockquote (line 9). MDL is the core technology but not listed as a hard dependency.

**After enhancement:** Clear, scannable list at the bottom — easy reference for researchers wanting to reproduce your work.

**Special note:** Your MDL + Karma workflow is **unique** to the Estate — this section makes it explicit.

**Gilfoyle's approach (Case 03):**

```markdown
## 📜 Technical Stack

* **Python**: 3.10
* **USD**: 23.11+
* **Houdini FX**: 21.0.596
* **NVIDIA Omniverse / Isaac Sim**: 5.1.0
```

---

## ✅ Success Criteria

- [ ] New section added before Changelog
- [ ] Versions accurate (Python 3.10, Houdini 21.0.596, Omniverse 2024.x)
- [ ] MDL explicitly listed (this is your core research focus!)
- [ ] Karma/VEX mentioned (your Houdini specialisation)
- [ ] Zero changes to Project Overview or any research narrative sections
- [ ] Markdown linting passes (`markdownlint README.md`)

---

## 📚 Reference

See [readme_structural_analysis.md] in Higgins' artifacts for full cross-case comparison.
