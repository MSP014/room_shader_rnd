# Parallax Interior Mapping for NVIDIA Omniverse

> Bringing Houdini's Room Map Shader to NVIDIA MDL for scalable Urban Digital Twins

**Status**: Research phase complete • Translation strategy in progress

---

## The Problem

Urban Digital Twins face a fundamental challenge: **realistic building interiors at scale**.

A single city block contains hundreds of windows. Each window reveals an interior — furniture, wall art, lighting fixtures. Modeling these geometrically is untenable:

- ❌ **Full geometry approach**: 50+ objects per room × 200 windows = 10,000+ meshes → Performance collapse
- ❌ **Black windows**: Unrealistic, breaks immersion in high-fidelity Digital Twins
- ❌ **Reflective/curtain fallback**: Works for distant views, fails at street level

**The solution exists** — but in the wrong ecosystem.

---

## The Solution: Parallax Interior Mapping

Houdini's **Room Map Shader** solves this elegantly: render interiors into specialized textures, then use shader math to create a convincing 3D illusion. The technique is called **parallax mapping** — view-dependent depth perception from 2D data.

**How it works:**

1. Bake interior scenes into a cross-shaped texture atlas (walls, ceiling, floor + depth slices)
2. Geometry preprocessing computes per-window tangent space
3. Fragment shader uses view direction to sample correct texture region, creating parallax effect

**The result**: Thousands of unique, depth-accurate interiors at the cost of texture lookups, not geometry.

**The catch**: This technique is written in **VEX** (Houdini's procedural language), tightly coupled to Houdini's production renderer. NVIDIA Omniverse uses **MDL** (Material Definition Language).

---

## This Research: VEX → MDL Translation

**Goal**: Adapt Houdini's Room Map approach to NVIDIA MDL, enabling Omniverse-based Digital Twins to benefit from lightweight interior rendering.

**Why this matters:**

- **For Digital Twins**: Scalable urban environments without performance compromises
- **For NVIDIA**: Demonstrates MDL's capability to handle advanced procedural techniques from other ecosystems
- **For the industry**: Cross-DCC interoperability — workflows shouldn't be siloed by renderer choice

> [!NOTE]
> **On Technique vs. Implementation**
>
> **Parallax interior mapping** is a well-established rendering technique used across game engines (Unreal, Unity), shading languages (OSL, GLSL), and DCC tools. SideFX's contribution is their specific **VEX implementation** for Karma, not the invention of the underlying algorithm.
>
> This research focuses on **adapting the concept** to NVIDIA MDL — studying how to achieve similar results using MDL's architecture, not copying proprietary code. The goal is cross-ecosystem knowledge transfer, enabling Omniverse users to benefit from proven techniques regardless of their origin.
>
> Credit to SideFX for their excellent documentation and implementation, which serves as the reference for this translation work.

---

## Visual Baseline and Transformation Path

This RnD begins with a digital replica of Building 150 on Moskovsky Avenue in
Saint Petersburg, prepared as a USD asset for Omniverse. The work will evolve
its flat glazing into a scalable parallax-interior system for the Case 01 Urban
Digital Twin.

![Starting asset — Building 150 on Moskovsky Avenue in Omniverse](docs/img/msk_150_omniverse.jpg)

*Starting asset: the Omniverse USD building before Room Map geometry context,
MDL parallax mapping, and interior variation are introduced.*

### First MDL Parallax Proof

The first functional MDL vertical slice uses a one-by-one test window to sample
a labelled cross-atlas and form a view-dependent virtual room. The baseline and
diagnostic texture establish the test contract; the applied material views then
show the changing visible faces in USD Composer with RTX Interactive (Path
Tracing).

| Baseline test plane | Diagnostic cross-atlas |
| --- | --- |
| <img src="docs/img/krm88/krm88_01.png" alt="Unshaded one-by-one test window plane in USD Composer" height="320"> | <img src="docs/img/krm88/roommap_debug.1001.png" alt="Labelled Room Map debug cross-atlas" height="320"> |

*The diagnostic cross-atlas defines the five virtual room faces. S1–S4 are
reserved depth-slice markers and are not sampled by this first vertical slice.*

| Head-on room view | Oblique room view |
| --- | --- |
| ![Head-on view of the labelled virtual room](docs/img/krm88/krm88_02.png) | ![Oblique view of the labelled virtual room](docs/img/krm88/krm88_03.png) |

*The changing visible faces demonstrate the parallax response while the
labelled atlas exposes any incorrect face assignment or orientation.*

---

## Technical Challenge: No Direct Translation Path

Houdini's implementation relies on three VEX-specific mechanisms:

### 1. **Primitive Attributes** (No MDL Equivalent)

Houdini's **geometry preprocessing tool** generates per-primitive data for each window:

```c
vector tangentu  // Local U tangent
vector tangentv  // Local V tangent
vector roomN     // Surface normal
vector roomP     // Reference position
```

**MDL Problem**: No concept of "primitive attributes." Shaders access geometry via `state::` module, which provides positions, normals, UVs — but not arbitrary custom data.

**Translation Strategy**: We are implementing a **Hybrid Geometry Context Strategy** (Detailed in [ADR 006](docs/adr/006-hybrid-geometry-context.md)) to support two distinct pipelines:

- **Production Mode (Option 1)**: Pre-compute these attributes in Houdini and store them as **USD primvars**. The MDL shader bypasses heavy math and simply reads these variables via `state::texture_coordinate(N)`. This is the optimized path required to render the thousands of instances in **Case 01**.
- **Community Mode (Option 2)**: For DCC-Agnostic usage (Blender, Maya, base Omniverse), an exposed boolean (`Use Pre-computed Frame Attributes = False`) forces the shader to dynamically compute the basis using `state::texture_tangent_u()` and `state::normal()`. This incurs a performance penalty but guarantees the shader works "out-of-the-box" for the community.

**Risk**: The dynamic computation in Option 2 requires careful profiling to understand the exact GPU overhead per pixel.

---

### 2. **Cross-Shaped UV Layout** (Portable)

The texture atlas uses a specific layout:

```text
      [Ceiling]
[Left] [Back] [Right]
       [Floor]
    [4 depth slices]
```

**Good news**: This is algorithm-agnostic. The math for "view direction → UV region" is standard coordinate transformation.

**Translation Strategy**: Direct port of VEX logic to MDL. Implementation straightforward.

---

### 3. **Parallax Ray Marching** (Adaptation Required)

Houdini's shader uses depth slices to simulate volumetric interiors. The algorithm:

1. Compute view ray in local tangent space
2. March through depth layers, sampling back-to-front
3. Blend samples based on depth intersection

**MDL Considerations**:

- `tex::lookup_*()` functions support UDIM (for randomization) ✅
- Manual ray marching in fragment shader (performance-sensitive) ⚠️
- MDL's distilled function model may require different optimization approach

**Translation Strategy**:

- Start with simple parallax offset (single depth layer)
- Validate performance before adding multi-layer complexity
- Compare with OSL implementations (similar constraints)

---

## Research Progress

### Phase 1: Documentation & Analysis ✅ COMPLETE

Comprehensive study of Houdini's Room Map Shader:

- **[Knowledge Base](docs/knowledge_base/)** — Narrative documentation with key insights for MDL translation
- Analyzed 4 core SideFX documentation pages
- Identified critical dependencies (geometry preprocessing, texture layout, shader math)
- Documented translation challenges and proposed strategies

### Phase 2: VEX → MDL Strategy 🔵 IN PROGRESS

Detailed technical mapping currently being documented in:

**[`docs/vex_to_mdl_strategy.md`](docs/vex_to_mdl_strategy.md)** (to be created)

Focus areas:

- VEX (Houdini's procedural language) → MDL equivalent mappings
- USD primvar schema design
- Shader architecture (monolithic vs. modular)
- Performance considerations (texture lookups, ray marching cost)

### Phase 3: Prototype Implementation ⚪ PLANNED

- MDL shader module with basic parallax offset
- Houdini → USD export pipeline (primvar generation)
- Omniverse validation scenes
- Performance benchmarking vs. geometry baseline

---

## Repository Structure

```text
docs/
├── knowledge_base/     # Analysis of Houdini's approach
├── adr/                # Architecture Decision Records
│   ├── 006-hybrid-geometry-context.md
│   └── 007-vop-to-mdl-parallax-logic.md
└── vex_to_mdl_strategy.md (planned)

src/                    # MDL shaders (TBD)
tests/                  # USD validation scenes (TBD)
```

**Key Documentation**:

- [Knowledge Base](docs/knowledge_base/) — Start here for context
- [ADRs](docs/adr/) — Design decisions and trade-offs

---

## For NVIDIA Recruiters

This project demonstrates:

✅ **Cross-ecosystem thinking** — Bridging Houdini ↔ Omniverse workflows
✅ **Technical depth** — MDL internals, USD primvars, shader optimization
✅ **Problem-solving focus** — Digital Twin use case drives technical choices
✅ **Research methodology** — Documentation-first, validate assumptions, iterate

**Current skills showcased**:

- NVIDIA MDL shader development
- USD/Omniverse pipeline integration
- Cross-DCC workflows (Houdini ↔ Omniverse)
- Technical documentation and knowledge synthesis

---

## Getting Started

**For developers**: See [Knowledge Base](docs/knowledge_base/) for technical deep dive

**For researchers**: Check `docs/adr/` for design rationale

**Setup**: Standard Omniverse/USD development environment (details TBD once implementation begins)

---

## 📜 Technical Stack

- **Python**: 3.10
- **NVIDIA MDL**: Core shader language
- **USD**: 23.11+ (primvars, stage composition)
- **Houdini**: 21.0 (VEX reference implementation)
- **NVIDIA Omniverse**: 2024.x (MDL runtime, validation)

**Development Tools**:

- Pre-commit hooks (markdown linting, Python formatting)
- pytest (validation framework)
- Git LFS (for binary assets, if needed)

---

## 💖 Support This Research

If you find this work valuable:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/maxspell)

Your support funds:

- Continued VEX → MDL translation research
- Prototype shader development and testing
- Quality documentation and tutorials

---

## 📜 Changelog

* **Week of 17 August, 2026:** Re-inventoried the RnD workspace with Omniverse MCP reference helpers, updated validation and dependency configuration, and renewed the MDL and USD research baseline.
* **Week of 2 March, 2026:** Defined the hybrid USD primvar and dynamic-frame strategy, then formalised native MDL parallax-interior mapping, cross-layout projection, depth slices, instance variation, and surface integration.
* **Week of 16 February, 2026:** Refined the public project narrative, knowledge base, technical stack, support information, and privacy boundary for a clearer recruiter and engineer reading path.
* **Week of 9 February, 2026:** Added safer Jira-plan synchronisation and consolidated repository naming conventions for repeatable research delivery.
* **Week of 2 February, 2026:** Established the Room Map Shader RnD foundation with public research documentation, architecture decisions, isolated Python tooling, security guardrails, a test baseline, and reusable asset-hydration structure.


---

**Part of [NVIDIA Omniverse Showreel](https://github.com/MSP014/dt-omniverse-showreel-case01-msk) | Research by Max Spell**
