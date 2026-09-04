# Parallax Interior Mapping in OpenUSD and NVIDIA MDL

## What & Why

**Parallax Interior Mapping (PIM)** renders realistic building interiors without
the geometry overhead of modelling every table, chair, or wall decoration. It
uses specialised textures and shader mathematics to create a view-dependent
"window box" illusion.

**The Challenge**: A production PIM material must receive stable room-frame and
camera data through OpenUSD, then evaluate the illusion efficiently in NVIDIA
MDL.

**This Research**: Document a native PIM implementation in NVIDIA MDL and
OpenUSD, enabling Omniverse Digital Twins to benefit from lightweight interior
rendering. The SideFX Karma Room Map workflow is an important reference
implementation for this research.

**Why It Matters for Digital Twins**:

- **Urban scale**: Apparent interiors can reduce the amount of physical room
  geometry and asset management required for exterior-facing scenes.
- **Visual fidelity**: View-dependent apparent depth improves flat or repetitive
  glazing without asserting that every visible room is physical geometry.
- **Procedural variation**: Deterministic UDIM selection reduces repetitive
  "copy-paste" treatment without creating per-window materials.

---

## How It Works (High Level)

The delivered ORMS system has four components:

1. **Geometry Setup** — A geometry preprocessing tool analyzes window geometry and computes per-primitive tangent space
2. **Texture Baking** — Interior scenes are rendered into a special cross-shaped layout (back wall, left/right walls, ceiling, floor + depth slices)
3. **Shader Math** — The shader uses view-dependent parallax to sample the correct part of the texture, creating 3D illusion
4. **Runtime and Artist Workflow** — One scene classifier assigns compatible
   mesh prim paths to Interior Sets before room grouping, then authors per-Set
   x1-x4 materials and bindings as reversible Session Layer state

The SideFX workflow below is a useful reference for one production-oriented
implementation of these components.

---

## Key Insights for MDL and OpenUSD Implementation

These are the **conceptual takeaways** for a native implementation. The SideFX
workflow informed the initial contracts; it is not copied or directly
translated.

### 1. **Geometry Preprocessing is Non-Negotiable**

The SideFX reference workflow generates critical frame attributes
(`tangentu`, `tangentv`, `roomN`, `roomP`) that define the local coordinate
system. The Houdini bridge also authors a dedicated `roomUV` channel without
repacking the model's ordinary texture coordinates. A compatible OpenUSD
preprocessing step can author the same data independently of Houdini.

**Implementation Strategy**: The accepted pipeline pre-computes the data in a
DCC or USD preprocessing step and stores it as **USD primvars**. The MDL shader
uses named primvar lookups for the production contract and retains standard
texture coordinates only as a compatibility fallback for earlier
hand-authored tests.

### 2. **Cross-Shaped UV Layout is Algorithm-Agnostic**

The texture layout (center = back wall, left/right = side walls, etc.) is just a convention. The math for mapping view direction → UV coordinates is portable to any shading language.

**Implementation Strategy**: The UV indexing logic is implemented natively in
MDL. No Houdini-specific code is required at runtime.

### 3. **Parallax Projection is a Standard Technique**

Room-box projection and layered depth representations exist in game engines,
OSL, GLSL, and other rendering environments. SideFX did not invent the
underlying technique; their workflow is a useful implementation reference.
The current ORMS depth-slice baseline uses analytic plane intersection and
alpha compositing, not ray marching.

**Implementation Strategy**: ORMS applies the parallax-interior mathematics in
MDL. The key engineering boundary is the **data plumbing**: primvars, texture
lookups, runtime camera data, and reversible USD authoring.

### 4. **UDIM Variation Uses Explicit Room Identity**

The SideFX reference workflow uses UDIM tiles for texture variation. MDL's
`tex::lookup_*()` functions support UDIM resources.

**Implementation Strategy**: The current material maps an integer `roomID`
primvar and a material-level seed to one tile of an MDL tiled texture. ORMS
creates runtime materials per `(interior_set_id, room_size)`, not per window;
every room in that family shares the binding and deterministic variant logic.
The isolated stage and the Houdini-authored component have both been accepted
in RTX Real-Time and RTX Interactive, with a dedicated `roomUV` channel
preserving the model's ordinary texture layout.

---

## Official Documentation

### SideFX Houdini (Version 21.0) — Reference Implementation

**Reference workflow**: [Karma Room Map Shader — Workflow Guide](https://www.sidefx.com/docs/houdini/solaris/support/karma_room_map.html)

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

## Current Implementation Contracts

The [MDL research-record index](mdl/README.md) documents the validated primvar
access, camera-position bridge, five-face parallax baseline, depth slices,
deterministic room variants, aperture controls, shared multi-window rooms, and
the completed Interior Set artist workflow. The accepted runtime uses one
scene classifier, resolves `interior_set_id` before grouping, and creates
x1-x4 material families per stable Set ID. Structural Set edits are staged
through `Apply Interior Sets`; material controls remain live and Set-scoped.
Generated identifiers, materials, subsets, and bindings remain ORMS-owned
Session Layer state. The native implementation is not presented as a VEX
translation.

---

**Part of [Omniverse Showreel](https://github.com/MSP014/dt-omniverse-showreel-case01-msk) | Research by Max Spell**
