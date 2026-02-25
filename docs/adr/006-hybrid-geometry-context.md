# Architecture Decision Record: 006 - Hybrid Coordinate Basis Strategy for MDL Parallax Shader

## Status

Accepted

## Context

The Karma Room Map Shader relies on local vector attributes (`tangentu`, `tangentv`, `roomP`, `roomN`) baked onto geometry primitives via the `Room Map Frame SOP`. These vectors define the local coordinate system (tangent space) required to correctly project the 3D parallax illusion onto 2D polygons.

In porting this logic to NVIDIA MDL, a critical architectural decision arises regarding how the shader acquires this local basis:

**Approach A: USD Primvars (Pre-computed)**
Calculate the basis vectors in Houdini (SOPs) and export them as USD primvars. Crucially, screenshot analysis confirms these must be exported as **Point (Vertex) Attributes**, not Primitive attributes. The MDL shader simply reads these variables via vertex interpolation.

* *Pros*: Optimal GPU performance. Offloads linear algebra to the CPU preprocessing stage. Scales efficiently for scenes with tens of thousands of windows. Supports complex clustered geometry (e.g. cylindrical buildings) via `roomID` stitching.
* *Cons*: Tightly couples the shader to a specific Houdini preprocessing pipeline. Useless for general Omniverse users who just want to apply the shader to standard DCC planes (Maya, Blender, etc.).

**Approach B: Dynamic MDL Calculation (Compute-on-the-fly)**
Derive the basis vectors inside the MDL shader using built-in state functions (`state::texture_tangent_u()`, `state::normal()`, etc.).

* *Pros*: 100% DCC-agnostic. Highly portable. Works "out of the box" for community users.
* *Cons*: Incurs a performance penalty on the GPU by calculating cross-products and tangent derivations per-pixel (or per-vertex, depending on MDL compilation). Sub-optimal for massive urban scenes.

## Decision

We will implement a **Hybrid Strategy**.

The MDL material will expose a boolean parameter: `Use Pre-computed Frame Attributes` (defaulting to `false`).

* **If `false` (Community/Agnostic Mode)**: The shader uses `state::` functions to dynamically construct the coordinate basis. This ensures the shader functions independently as a plug-and-play asset for the broader Omniverse ecosystem.
* **If `true` (Production/Optimized Mode)**: The shader bypasses dynamic calculations and attempts to read `tangentu`, `tangentv`, `roomP`, `roomN` from USD primvars via `state::texture_coordinate(N)`. This mode is designed specifically for heavy Digital Twin pipelines (like Case 01), where geometrical preprocessing in Houdini is standard and performance at scale is paramount.

## Consequences

* **Positive**: We satisfy both strategic goals of the RnD project: it remains a highly optimized, production-ready tool for the NVIDIA Showreel (Case 01), whilst simultaneously serving as a valuable, standalone contribution to the general Omniverse community.
* **Negative**: Increases the branching complexity within the MDL shader code. Requires careful documenting of the required USD primvar schema for users who wish to utilize the optimized path.
