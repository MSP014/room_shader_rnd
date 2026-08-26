# Architecture Decision Record: 007 - MDL Parallax Interior Mapping (PIM) Strategy

## Context

The SideFX Karma Room Map workflow, including the locked `kma_roommap` VOP, is
an important reference implementation for Case 01. Its internal VEX code is
not the target of this work. Parallax Interior Mapping is an established
rendering technique, so the project implements a clean, mathematically defined
PIM algorithm natively in NVIDIA MDL rather than copying or directly
translating the Karma shader.

This custom implementation must satisfy the following constraints:

1. Accept the current `Room Map Frame SOP` attribute contract (`roomP`, `tangentu`, `tangentv` as Vertex primvars), while keeping the core maths separable from its Houdini source.
2. Project a cross-shaped interior texture correctly onto the proxy geometry.
3. Support layered depth slices with alpha blending.

## Decision

We will build a custom **Parallax Interior Mapping (PIM)** function in MDL.

### 1. Spatial Transformation (World to Local)

Instead of operating in World Space, the shader will construct a **Local Tangent Space** for the room interior using the incoming USD Primvars:

* Local $X$-axis = `tangentu`
* Local $Y$-axis = `tangentv`
* Local $Z$-axis = `roomN` (computed via cross product of U and V, or read from primvar).
* Center of the room = `roomP`

The runtime bridge supplies `camera_position_world`; the material derives the
view ray from the camera and surface positions, then transforms it into this
local space to perform intersection tests against a normalised "virtual room
box" (for example, coordinates from -1 to 1).

### 2. Ray-Box Intersection (The Parallax Effect)

We will use an optimized AABB (Axis-Aligned Bounding Box) intersection algorithm inside the fragment shader:

1. Calculate the intersection of the local view ray with the internal walls of the virtual box.
2. Determine which wall (Back, Left, Right, Top, Bottom) the ray hits based on the shortest positive distance.
3. The intersection coordinates (in the range [-1, 1]) will then be mapped to the UV coordinates of that specific wall.

### 3. Texture Mapping (The Cross Layout)

The reference workflow uses a cross-shaped room atlas. The native MDL material
implements a UV remapping function that translates the local intersection
point on the virtual 3D box into the correct 2D UV tile within that layout:

* `[1/3, 1/3]` to `[2/3, 2/3]` -> Back Wall
* `[0, 1/3]` to `[1/3, 2/3]` -> Left Wall
* `[2/3, 1/3]` to `[1, 2/3]` -> Right Wall
* `[1/3, 2/3]` to `[2/3, 1]` -> Ceiling
* `[1/3, 0]` to `[2/3, 1/3]` -> Floor

### 4. Slices (Depth Layers)

To support depth layers (like curtains or furniture):

1. We define arbitrary Z-depth planes between the window plane ($Z=1$) and the back wall ($Z=-1$).
2. The ray equation is solved for these Z-planes.
3. If an intersection occurs within the X and Y bounds of the room, we sample the respective slice's texture (located in the corners of the cross layout).
4. Standard alpha blending `mix(room_color, slice_color, slice_alpha)` is applied.

### 5. Instance Variation (UDIM Offset)

In the SideFX reference setup, UDIM tile variation is driven by a `Voronoi Noise 3D` node. The `roomP` (or `roomID`) attribute acts as the seed or position for the noise, and the result is remapped via `mtlxrange_rooms` into an integer `offset` for the `kma_roommap` node.
The native MDL material will instead provide a stable per-window variation path:

1. We expose a `room_offset` integer parameter on the main Material.
2. In the DCC (or via Omniverse OmniGraph/MaterialX graph), the user will generate a pseudo-random integer based on the `roomID` primvar (using a noise or hash function).
3. This integer is passed to our MDL shader, which shifts the UV lookup to the corresponding texture sequence/UDIM tile, guaranteeing that windows with different `roomIDs` get different interiors.

### 6. Surface Material Integration

The Karma network (`kma_roommap1` feeding into `mtlxstandard_surface`) is a
useful reference for material integration. The native PIM logic acts solely as
a sophisticated colour and normal generator.
In the final MDL implementation, the Parallax Module will output a Struct containing `base_color` and `normal`. These outputs will then be fed into a standard Physically Based Rendering (PBR) material definition (such as `OmniSurface` or a standard `material` construct), mapping:

* `out` -> `base_color`
* `normal` -> `geometry.normal`

## Consequences

* **Performance**: The native MDL implementation keeps the mathematical path explicit and bounds texture lookups. Its performance at Case 01 scale requires the planned benchmark; it is not yet a measured advantage over the reference workflow.
* **Maintenance**: We own the code. If the cross-layout format changes or we need to add 8 slices instead of 4, we modify our own MDL module.
* **Portability**: While the current prototype uses `Room Map Frame SOP` primvars, the core PIM maths is designed to be separable from that source and could accept standard UVs and tangents for non-Houdini users. That compatibility path remains to be validated.
