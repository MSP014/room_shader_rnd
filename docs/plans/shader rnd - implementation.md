# Room Map Shader RnD — Implementation Plan

**Jira Project**: KRM
**Status**: In Progress
**Last Updated**: 2026-02-01

---

## 🧩 EPIC: Analyse Karma Room Map Shader (KRM-61)

**Status**: 🔄 In Progress
**Estimate**: 10h

### 🔄 [KRM-79] Geometry Context Analysis (SOP)

**Status**: 🔄 In Progress
**Estimate**: 2h
**Objective**: Analyse attribute creation and setup in Geometry context. Identify which attributes (UVs, normals, custom primvars) are required by the shader to perform parallax calculations.

**Definition of Done:**

- SOP-level logic for attribute initialisation is documented.
- List of required geometric attributes is compiled.

### 🔄 [KRM-80] Material Context Analysis (Solaris/LOP)

**Status**: 🔄 In Progress
**Estimate**: 2h
**Objective**: Study Material Library setup and parameter exposure in Solaris/LOP context. Understand how MaterialX or VEX shaders are bound to USD primitives.

**Definition of Done:**

- Material binding workflow in Solaris is documented.
- Parameter exposure strategy (how user-facing knobs connect to shader internals) is understood.

### 🔄 [KRM-81] Application Layer: USD Binding

**Status**: 🔄 In Progress
**Estimate**: 2h
**Objective**: Analyse USD material binding and primvar mapping. Focus on how USD 'Primvars' are read by the renderer and passed to the MDL/VEX shader.

**Definition of Done:**

- Diagram or description of USD attribute flow to shader.
- Primvar naming conventions for the project established.

### 🔄 [KRM-82] Shader Internals: VEX/MaterialX Deep Dive

**Status**: 🔄 In Progress
**Estimate**: 2h
**Objective**: Deep dive into VEX and MaterialX shader nodes in both Geometry and Solaris contexts. Reverse-engineer the core Ray-Box intersection or texture slicing logic.

**Definition of Done:**

- Mathematical core of the Room Map logic documented.
- Key shader nodes and their roles identified.

### 🔄 [KRM-83] Documentation & VEX to MDL Strategy

**Status**: 🔄 In Progress
**Estimate**: 2h
**Objective**: Mine Houdini documentation and formulate VEX to MDL translation strategy. Plan the porting of specifically Houdini-centric functions to standard MDL.

**Definition of Done:**

- `docs/research/vex_to_mdl_strategy.md` created.
- Identified potential roadblocks in MDL (e.g., specific texture filtering or sampling requirements).

---

## 🧩 EPIC: MDL API & Mathematics Research (KRM-62)

**Status**: ⏸️ To Do
**Estimate**: 5h
**Objective**: Study NVIDIA MDL texture/state functions, research parallax mathematics, analyse coordinate system differences, and define shader interface.

---

## 🧩 EPIC: MDL Shader Implementation (KRM-63)

**Status**: ⏸️ To Do
**Estimate**: 12h
**Objective**: Port Karma Room Map VEX logic to NVIDIA MDL, implementing parallax offset calculations, texture slicing, and coordinate transforms.

---

## 🧩 EPIC: Performance Optimisation (KRM-64)

**Status**: ⏸️ To Do
**Estimate**: 8h
**Objective**: Profile shader performance, optimise texture lookups and coordinate calculations for use in scenes with thousands of instances (Case 01 windows).

---

## 🧩 EPIC: Testing & Integration (KRM-65)

**Status**: ⏸️ To Do
**Estimate**: 6h
**Objective**: Test shader in Case 01 (Moskovsky av) scene, validate visual quality and performance, integrate into production pipeline.

---

## ⏸️ EPIC: Tutorial: Assets (KRM-6)

**Status**: ⏸️ Postponed (Strategic Pause)
**Estimate**: None
**Objective**: Develop and refine assets specifically for the "How To Houdini" tutorial series, ensuring they demonstrate best practices and procedural techniques.

---

## ⏸️ EPIC: Tutorial: Shots (KRM-7)

**Status**: ⏸️ Postponed (Strategic Pause)
**Estimate**: None
**Objective**: Set up, light, and render the specific instructional "Shots" defined in the VO script.

---

## ⏸️ EPIC: Tutorial: Video Assembly (KRM-8)

**Status**: ⏸️ Postponed
**Estimate**: None
**Objective**: Edit and assemble the final tutorial video, incorporating voiceover and screen recordings.

---

## ⏸️ EPIC: Tutorial: Final Delivery (KRM-9)

**Status**: ⏸️ Postponed
**Estimate**: None
**Objective**: Final export, packaging, and delivery for the SideFX contest or community platforms.

---

## ✅ COMPLETED EPICS (Tutorial Phase 0)

- **[KRM-1] Text**: Research and core text/outline for the tutorial structure.
- **[KRM-5] VO**: Voiceover script and recording preparations (`docs/plans/voiceover_script.md`).

---

## 🔗 Task Dependencies

**Critical Path (Shader RnD)**:

```text
KRM-61 (Analyse Karma) → KRM-62 (MDL Research) → KRM-63 (Implementation) → KRM-64 (Optimisation) → KRM-65 (Testing)
```

**Secondary Path (Tutorial - Postponed)**:

```text
KRM-6 (Assets) → KRM-7 (Shots) → KRM-8 (Assembly) → KRM-9 (Delivery)
```

---

## 📊 Progress Summary

| Project Area | Epic | Status | Completion |
| ------------ | ---- | ------ | ---------- |
| **Shader RnD** | KRM-61 (Analyse Karma) | 🔄 In Progress | 0/5 tasks complete |
| **Shader RnD** | KRM-62 (MDL Research) | ⏸️ To Do | 0% |
| **Shader RnD** | KRM-63 (Implementation) | ⏸️ To Do | 0% |
| **Shader RnD** | KRM-64 (Optimisation) | ⏸️ To Do | 0% |
| **Shader RnD** | KRM-65 (Testing) | ⏸️ To Do | 0% |
| **Tutorial** | KRM-6 (Assets) | ⏸️ Postponed | 0% |
| **Tutorial** | KRM-7 (Shots) | ⏸️ Postponed | 0/20 tasks complete |
| **Tutorial** | KRM-8 (Assembly) | ⏸️ Postponed | 0% |
| **Tutorial** | KRM-9 (Delivery) | ⏸️ Postponed | 0% |
| **Finished** | KRM-1, KRM-5 | ✅ Done | 100% |

**Total Estimated Hours (RnD)**: 41h

---

## 🎯 Next Priorities

1. **KRM-79** (Geometry Context Analysis) — Start reverse-engineering SOP attribute setup.
2. **KRM-80** (Material Context Analysis) — Understand Solaris binding workflow.
3. **KRM-82** (Shader Internals) — Core logic deep dive.
