# Architecture Decision Record: 006 - Hybrid Coordinate Basis Strategy for MDL Parallax Shader

## Status

Accepted

> **Superseding evidence note — 28 August 2026:** The performance language below
> records the original design hypothesis. It has not yet been validated at
> Building 150 scale. Current public claims are limited to the intent to reduce
> physical interior geometry and scene complexity until the planned benchmark
> is complete. Later renderer evidence also established named primvar lookup as
> the validated frame-data path; the dynamic-frame path remains unproven.

## Context

The SideFX Karma Room Map reference workflow uses local vector attributes
(`tangentu`, `tangentv`, `roomP`, `roomN`) baked onto geometry primitives via
the `Room Map Frame SOP`. These vectors define the local coordinate system
(tangent space) required to correctly project the 3D parallax illusion onto 2D
polygons. A native PIM implementation needs the same coordinate information,
not a copy of the Karma shader.

For the native PIM material in NVIDIA MDL, a critical architectural decision is
how the shader acquires this local basis:

**Approach A: USD Primvars (Pre-computed)**
Calculate the basis vectors in Houdini, another DCC, or USD preprocessing and
export them as USD primvars. The current reference export uses **Point
(Vertex) Attributes**, not Primitive attributes. The MDL shader reads these
values via vertex interpolation.

* *Pros*: Optimal GPU performance. Offloads linear algebra to the CPU preprocessing stage. Scales efficiently for scenes with tens of thousands of windows. Supports complex clustered geometry (e.g. cylindrical buildings) via `roomID` stitching.
* *Cons*: Requires a compatible preprocessing step and USD primvar contract.
  Without one, the optimised path is unavailable to general Omniverse users who
  want to apply the shader to standard DCC planes (Maya, Blender, etc.).

**Approach B: Dynamic MDL Calculation (Compute-on-the-fly)**
Derive the basis vectors inside the MDL shader using built-in state functions (`state::texture_tangent_u()`, `state::normal()`, etc.).

* *Pros*: 100% DCC-agnostic. Highly portable. Works "out of the box" for community users.
* *Cons*: Incurs a performance penalty on the GPU by calculating cross-products and tangent derivations per-pixel (or per-vertex, depending on MDL compilation). Sub-optimal for massive urban scenes.

## Decision

We will implement a **Hybrid Strategy**.

The MDL material will expose a boolean parameter: `Use Pre-computed Frame Attributes` (defaulting to `false`).

* **If `false` (Community/Agnostic Mode)**: The shader uses `state::` functions to dynamically construct the coordinate basis. This ensures the shader functions independently as a plug-and-play asset for the broader Omniverse ecosystem.
* **If `true` (Production/Optimized Mode)**: The shader bypasses dynamic calculations and attempts to read `tangentu`, `tangentv`, `roomP`, `roomN` from USD primvars via `state::texture_coordinate(N)`. This mode is designed for heavy Digital Twin pipelines such as Case 01, where compatible geometry preprocessing and a stable primvar contract are available.

## Consequences

* **Positive**: We satisfy both strategic goals of the RnD project: it remains a highly optimized, production-ready tool for the NVIDIA Showreel (Case 01), whilst simultaneously serving as a valuable, standalone contribution to the general Omniverse community.
* **Negative**: Increases the branching complexity within the MDL shader code. Requires careful documenting of the required USD primvar schema for users who wish to utilize the optimized path.
