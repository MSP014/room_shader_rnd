# Single-Room Cross-Atlas Parallax Contract

## Purpose

This document establishes the first visible Room Map vertical slice: one window,
one cross-atlas, and five virtual room faces. It deliberately excludes depth
slices, UDIM variation, and production glass integration.

The validation scene is `tests/test_room_map_single.usda`. It defines a
one-by-one window in the YZ plane, facing positive X, and binds
`src/mdl/room_map_single.mdl` to that window.

## Coordinate convention

The shader uses a normalised room coordinate system:

- Window coordinates come from `primvars:st`, with `U, V` in `[0, 1]`.
- The window plane is `Z = 0`.
- The virtual room box is `[0, 1] x [0, 1] x [-room_depth, 0]`.
- `room_depth = 1.0` produces the unit-cube diagnostic case.

The USD vertex primvars `roomP`, `tangentu`, and `tangentv` construct the
world-space frame. `tangentu x tangentv` defines the window normal. The
active camera position and the current surface position are rebased against
`roomP`, transformed into this frame, and subtracted to produce the ray from
the camera through the window and into the virtual room.

The material therefore requires the three frame primvars to be in world space. The
single-window test scene has no object transform, so its authored frame is
also world space. Supporting object-space frames is a later compatibility
extension, not an implicit fallback.

## Ray and atlas mapping

The ray begins at `(U, V, 0)`. The shader intersects it with the back, left,
right, ceiling, and floor planes, then selects the nearest positive distance.
One `tex::lookup_float4` call samples the corresponding region of the debug
atlas.

| Virtual face | Cross-atlas tile | Local coordinate convention |
| --- | --- | --- |
| Back | Centre | `U, V` |
| Left | Middle left | depth, `V` |
| Right | Middle right | reverse depth, `V` |
| Ceiling | Top centre | `U`, reverse depth |
| Floor | Bottom centre | `U`, depth |

`assets/_external/tex/roommap_debug.1001.png` supplies the labelled reference
atlas. The labels make mirror, rotation, and wrong-face errors immediately
visible during the renderer check.

## Runtime validation boundary

Open `tests/test_room_map_single.usda` in USD Composer. In the Script Editor,
run:

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

Then move the active camera.

In RTX Real-Time and RTX Interactive (Path Tracing), the virtual room must
show the correct labelled face as the camera moves. The result is accepted
only when neither orientation nor face assignment is mirrored or rotated.

## Recorded result

Visual validation was completed on 23 August 2026 in USD Composer. The
material resolved and produced the expected view-dependent room in both RTX
Real-Time and RTX Interactive (Path Tracing).

The labelled debug atlas confirmed the final orientation of all five virtual
faces: Back, Left, Right, Ceiling, and Floor. The ceiling label is intentionally
oriented with its base against the Back face, matching the source cross-atlas;
the floor follows the complementary bottom-atlas orientation. No mirrored face
assignment or unintended rotation remained in either renderer.
