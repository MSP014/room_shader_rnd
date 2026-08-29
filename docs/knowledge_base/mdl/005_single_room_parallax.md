# Single-Room Cross-Atlas Parallax Contract

## Record

| Field | Value |
| --- | --- |
| Jira | KRM-88 — Single Debug Room: Cross-Atlas Parallax |
| Implementation | `src/mdl/room_map_single.mdl` |
| Automated evidence | `tests/test_room_map_single.py` |
| Validation scene | `tests/test_room_map_single.usda` |
| Evidence state | Renderer-validated |
| Last validated | 23 August 2026 |

## Purpose

This record establishes the first visible Room Map slice: one planar window,
one cross-atlas, and five analytic virtual room faces. It excludes depth
slices, UDIM variation, and production glass.

## Accepted contract

### Coordinate system

- The validation window is in the YZ plane and faces positive X.
- Window coordinates are normalised to `[0, 1]`.
- The virtual window plane is `Z = 0`.
- The room box is `[0, 1] × [0, 1] × [-room_depth, 0]`.
- `room_depth = 1` is the unit-cube diagnostic case.

The vertex primvars `roomP`, `tangentu`, and `tangentv` construct the room
frame. `tangentu × tangentv` defines the window normal. The active camera and
shaded surface positions are rebased against `roomP` and transformed into that
frame before the camera-to-window ray is constructed.

The accepted input frame is world-space. The validation mesh has no object
transform, so its authored and world-space frames are identical.

### Ray and atlas mapping

The ray begins at `(U, V, 0)`. The shader intersects it with the back, left,
right, ceiling, and floor planes and selects the nearest positive hit.

| Virtual face | Cross-atlas region | Local convention |
| --- | --- | --- |
| Back | Centre | `U, V` |
| Left | Middle left | depth, `V` |
| Right | Middle right | reverse depth, `V` |
| Ceiling | Top centre | `U`, reverse depth |
| Floor | Bottom centre | `U`, depth |

One `tex::lookup_float4` samples the selected labelled face.

## Evidence

`tests/test_room_map_single.usda` binds the implementation to a one-by-one
window. `assets/_external/tex/room_map_debug/room_map_debug.1001.png` is the
labelled reference atlas; its text exposes mirror, rotation, and wrong-face
errors directly.

## Reproduction

Open `tests/test_room_map_single.usda` in USD Composer, then run:

```python
from pathlib import Path
import sys
import omni.usd

root_layer = omni.usd.get_context().get_stage().GetRootLayer()
repository_root = Path(root_layer.realPath).parents[1]
sys.path.append(str(repository_root / "tools" / "omniverse"))

import camera_position_bridge

camera_position_bridge.start(
    "/World/Looks/RoomMapSingle/Shader.inputs:camera_position_world"
)
```

Move the active camera and inspect all labelled faces in RTX Real-Time and RTX
Interactive (Path Tracing). Neither face assignment nor text orientation may
be mirrored or rotated.

## Validation record

On 23 August 2026, both renderer modes produced the expected view-dependent
room. Back, Left, Right, Ceiling, and Floor labels retained their accepted
orientation. The ceiling label's base meets the Back face as authored in the
source cross-atlas; the floor uses the complementary orientation.

## Boundary

This is a one-window, five-face, world-space-frame proof. Object-space frame
transport, depth slices, variants, arbitrary apertures, shared rooms, and
production glass are outside this record.
