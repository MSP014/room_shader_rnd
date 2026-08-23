# Depth-Slice Cross-Atlas Material Contract

## Purpose

`src/mdl/room_map.mdl` is the public Room Map material baseline with a
single normalised test window, five virtual room faces, and up to four
alpha-composited depth slices. It extends `room_map_single.mdl` without
altering that accepted five-face reference implementation.

The validation scene is `tests/test_room_map_slices.usda`. It uses the green
diagnostic atlas `assets/_external/tex/roommap_debug.1002.png` so slice work
is visually distinct from the red five-face baseline.

## Material inputs

| Input | Default | Contract |
| --- | --- | --- |
| `room_atlas` | empty texture | Cross-atlas containing the five room faces and S1–S4 slice regions. |
| `room_depth` | `1.0` | Normalised room depth; the window is at depth zero and the back plane is at `room_depth`. |
| `window_shift` | `(0, 0)` | Adds a normalised U/V offset before the view ray is constructed. Coordinates at the window boundary are clamped. |
| `enable_slice_1` … `enable_slice_4` | `true` | Enables sampling and compositing of the matching S1–S4 region. |
| `slice_N_depth_percent` | `20`, `40`, `60`, `80` | Position from the window plane (`0`) to the back plane (`100`). Values are clamped to this range. |
| `slice_N_offset` | `(0, 0)` | Adds a local U/V offset inside slice N's cross-atlas tile. |
| `slice_N_scale` | `(1, 1)` | Multiplies local U/V coordinates inside slice N's cross-atlas tile. |
| `fallback_colour` | magenta | Diagnostic colour used only when the USD room frame is invalid. |
| `camera_position_world` | `(0, 0, 0)` | Runtime input maintained by `tools/omniverse/camera_position_bridge.py`; it is not authored as camera animation in the source scene. |
| `emission_strength` | `1.0` | Diagnostic visibility control shared with the accepted five-face baseline. |

For a slice, the shader calculates local coordinates as
`hit_uv * slice_N_scale + slice_N_offset`. Coordinates outside that slice's
unit tile are discarded before sampling, and `tex::wrap_clip` prevents any
sampling outside the atlas boundary.

## Cross-atlas and compositing

The five virtual room faces retain the accepted mapping contract:

| Face | Cross-atlas tile |
| --- | --- |
| Back | Centre |
| Left | Middle left |
| Right | Middle right |
| Ceiling | Top centre |
| Floor | Bottom centre |

The four remaining atlas corners are the alpha-capable depth-slice regions:

| Slice | Cross-atlas tile | Default depth |
| --- | --- | --- |
| S1 | Bottom left | 20% |
| S2 | Top left | 40% |
| S3 | Top right | 60% |
| S4 | Bottom right | 80% |

For every shaded point, the material first traces the same analytic ray used
by the five-face baseline. It then intersects that ray with each enabled
slice plane, clips hits outside the virtual room, samples the corresponding
corner tile, and composites its alpha over the room-face result.

Slice contribution is evaluated geometrically: a closer slice attenuates the
contribution of every farther slice and the room faces behind it. This remains
correct when artists change the four depth values; the default values are only
the readable near-to-far starting order. Equal depths use a deterministic
S4-to-S1 tie order.

This is analytic plane intersection and alpha compositing. It is not ray
marching, and it does not yet implement a production multi-room or UDIM
variation system.

## Runtime validation procedure

Open `tests/test_room_map_slices.usda` in USD Composer. In the Script Editor,
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
    "/World/Looks/RoomMap/Shader.inputs:camera_position_world"
)
```

Check the following in RTX Real-Time and RTX Interactive (Path Tracing):

1. Disable all four slices to confirm the green five-face room baseline.
2. Enable one slice at a time to confirm its corner-tile assignment and alpha.
3. Enable all slices using the default 20/40/60/80% depths.
4. Reorder at least two depth values and confirm that the closer slice stays
   visually in front.
5. Change a slice offset and scale to confirm that the public controls affect
   only that slice tile.

The Python test validates the static USD and material contract. Renderer
compilation and the visual checks above remain the acceptance evidence for
this MDL vertical slice.

## Recorded result

Visual validation was completed on 23 August 2026 in USD Composer. The public
`room_map` material resolved as an MDL node in Material Graph and rendered in
both RTX Real-Time and RTX Interactive (Path Tracing).

The green diagnostic atlas confirmed all five room faces and the four
alpha-composited S1–S4 corner regions. Enable flags, depth percentages,
per-slice offsets, and per-slice scales all changed the rendered result.
The default 20/40/60/80% ordering was visible from near to far. A second
check used S1 = 99%, S2 = 72%, S3 = 24%, and S4 = 9%; it confirmed that slice
ordering follows the edited geometric depths rather than the fixed S1–S4
numbers.

## Current boundary

Validated scope for this material is intentionally limited to one `1 × 1`
normalised test window, five room faces, and four alpha-composited slice
planes. It does not yet provide production façade integration, arbitrary
window aspect handling, multi-room variation, or a geometry-versus-Room-Map
performance measurement.
