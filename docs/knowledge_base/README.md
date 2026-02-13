# Parallax Interior Mapping: Houdini to Omniverse

## What & Why

The **Karma Room Map Shader** is Houdini's solution for rendering realistic building interiors without the geometry overhead — a clever "window box" illusion using parallax mapping. Instead of modeling every room interior (tables, chairs, wall decorations), you bake them into special textures and use shader math to create depth perception.

**The Challenge**: This technique is implemented in VEX (Houdini's shading language) and tightly integrated with Karma renderer. NVIDIA Omniverse uses MDL (Material Definition Language). There's no direct translation path.

**This Research**: Document how to adapt Houdini's Room Map approach to NVIDIA MDL, enabling Omniverse Digital Twins to benefit from this lightweight interior rendering technique.

**Why It Matters for Digital Twins**:

- **Urban scale**: A city block has thousands of windows. Traditional geometry = performance death.
- **Visual fidelity**: Parallax interiors maintain realism without polygon cost.
- **Procedural variation**: UDIM randomization prevents repetitive "copy-paste" look.

---

## How It Works (High Level)

The technique has three components:

1. **Geometry Setup** — A SOP node (`Room Map Frame`) analyzes window geometry and computes per-primitive tangent space
2. **Texture Baking** — Interior scenes are rendered into a special cross-shaped layout (back wall, left/right walls, ceiling, floor + depth slices)
3. **Shader Math** — The VOP node (`kma_roommap`) uses view-dependent parallax to sample the correct part of the texture, creating 3D illusion

For full workflow details, see the official SideFX guide below.

---

## Key Insights for MDL Translation

These are the **conceptual takeaways** from studying Houdini's implementation, not a copy-paste of technical specs:

### 1. **Geometry Preprocessing is Non-Negotiable**

The Room Map Frame SOP generates critical per-primitive attributes (`tangentu`, `tangentv`, `roomN`, `roomP`) that define the local coordinate system. **MDL has no equivalent to VEX primitive attributes.**

**Translation Strategy**: Pre-compute these in Houdini (or USD preprocessing) and store as **USD primvars**. The MDL shader reads them via `state::texture_coordinate()` or primvar lookups.

### 2. **Cross-Shaped UV Layout is Algorithm-Agnostic**

The texture layout (center = back wall, left/right = side walls, etc.) is just a convention. The math for mapping view direction → UV coordinates is portable to any shading language.

**Translation Strategy**: Implement the same UV indexing logic in MDL. No Houdini-specific code required.

### 3. **Parallax Projection is a Standard Technique**

The core algorithm (ray marching through depth slices) exists in game engines, OSL, GLSL, etc. Houdini didn't invent it — they just packaged it nicely.

**Translation Strategy**: Adapt existing parallax algorithms to MDL. The challenge is not the math, but the **data plumbing** (primvars, texture lookups).

### 4. **UDIM Randomization is Trivial in MDL**

Houdini uses UDIM tiles for texture variation. MDL's `tex::lookup_*()` functions support UDIM natively.

**Translation Strategy**: Direct 1:1 mapping. No work needed.

---

## Official Documentation

### SideFX Houdini (Version 21.0)

**Start Here**: [Karma Room Map Shader — Workflow Guide](https://www.sidefx.com/docs/houdini/solaris/support/karma_room_map.html)

- Complete tutorial with setup instructions
- Examples: single window, multi-window, curved surfaces
- MaterialX integration notes

**Technical References**:

- [Karma Room Map VOP](https://www.sidefx.com/docs/houdini/nodes/vop/kma_roommap.html) — Shader node parameters
- [Room Map Frame SOP](https://www.sidefx.com/docs/houdini/nodes/sop/roommapframe.html) — Geometry setup (critical!)
- [Karma Room Lens VOP](https://www.sidefx.com/docs/houdini/nodes/vop/kma_roomlens.html) — Texture baking tool

> **Note**: Full documentation copies are maintained locally in `houdini/` directory (gitignored) for offline research. Public repository contains only these references.

---

## NVIDIA MDL Resources

- [MDL Language Specification](https://raytracing-docs.nvidia.com/mdl/introduction/index.html)
- [USD Primvars Specification](https://graphics.pixar.com/usd/release/api/class_usd_geom_primvar.html) — How to store custom attributes
- [MaterialX Standard Surface](https://materialx.org) — Interoperability reference

---

## Next Steps

The detailed **VEX → MDL translation strategy** will be documented in:

**[`../vex_to_mdl_strategy.md`](../vex_to_mdl_strategy.md)** (To be created)

This document will map specific VEX functions to MDL equivalents, provide pseudocode, and outline implementation risks.

---

**Part of [Omniverse Showreel](https://github.com/MSP014/dt-omniverse-showreel-case01-msk) | Research by Max Spell**
