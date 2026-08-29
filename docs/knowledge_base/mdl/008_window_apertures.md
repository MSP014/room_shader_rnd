# Window Aperture Scale and Offset Contract

## Record

| Field | Value |
| --- | --- |
| Jira | KRM-94 — Window Aperture Scale and Offset Controls |
| Implementation | `src/mdl/room_map.mdl` |
| Automated evidence | `tests/test_room_map_apertures.py`, `tests/test_room_map_apertures_houdini.py` |
| Validation scenes | `tests/test_room_map_apertures.usda`, `tests/test_room_map_apertures_houdini.usda` |
| Evidence state | Renderer-validated on Omniverse- and Houdini-authored geometry |
| Last validated | 26 August 2026 |

## Purpose

The Room Map material represents a physical window aperture separately from
the virtual room dimensions. Landscape and portrait windows reveal different
portions of one proportionate room rather than stretching a square atlas to
their aspect ratio.

## Accepted contract

### Geometry

The magnitudes of the accepted frame vectors carry physical dimensions:

- `length(tangentu)` is physical window width;
- `length(tangentv)` is physical window height.

Their normalised values define orientation. `roomUV` remains a face-varying
`texCoord3f` in `[0, 1]` and does not encode aspect ratio.

| Primvar | Type | Interpolation | Purpose |
| --- | --- | --- | --- |
| `roomP` | `float3[]` | `vertex` | Room-frame origin. |
| `tangentu` | `float3[]` | `vertex` | Horizontal direction and physical width. |
| `tangentv` | `float3[]` | `vertex` | Vertical direction and physical height. |
| `roomUV` | `texCoord3f[]` | `faceVarying` | Normalised aperture coordinate. |
| `roomID` | `int[]` | `uniform` | Stable room-variant identity. |

The KRM-90 Houdini Vertex Wrangle remains the accepted way to derive `roomUV`;
it is reproduced in [007 — Room Variants](007_room_variants.md).

### Material controls

| Input | Default | Contract |
| --- | --- | --- |
| `room_uniform_scale` | `1` | Common X/Y virtual-room extent. |
| `window_aperture_scale` | `(1, 1)` | Independent aperture scale about its centre. |
| `window_aperture_offset` | `(0, 0)` | Independent aperture offset in normalised room space. |
| `window_shift` | `(0, 0)` | Legacy offset added after aperture scale and offset. |

The material calculates:

```text
room_extent = room_uniform_scale
aperture_extent = (physical_width, physical_height) * safe_scale
aperture_uv =
    (roomUV.xy - 0.5) * aperture_extent
    + 0.5 * room_extent
    + (window_aperture_offset + window_shift) * room_extent
```

The camera-to-surface direction remains physical; aperture controls change
only the ray origin. Side planes remain at zero and `room_extent`, and depth is
`room_depth × room_extent`. Room-face and slice coordinates are normalised by
the same extent, retaining the existing five texture lookups.

With room scale `2`, a square 1:1 opening maps to `.5…1.5` on both axes, a
landscape 2:1 opening maps to `0…2` horizontally and `.5…1.5` vertically, and
a portrait 1:2 opening does the converse.

Zero or negative scale is limited to the material epsilon. Offsets may
intentionally place part of an aperture beyond the virtual front plane.
Degenerate frame magnitudes use the fallback-colour path.

## Evidence

The isolated stage contains square 1:1, landscape 2:1, and portrait 1:2
windows plus dedicated control instances. Automated checks retain physical
dimensions, inputs, fixed virtual volume, primvars, and lookup budget.

The DCC proof retains:

- `hip/room map test 005.hiplc`;
- `assets/_external/usd/test_grid_wins_diff/test_grid_wins_diff.usd` and its
  payload, geometry, and material layers;
- `tests/test_room_map_apertures_houdini.usda`, which overrides only the
  exported window material.

Its 15 windows preserve three physical dimension classes in `tangentu` and
`tangentv`, while the facade keeps its Houdini material.

## Reproduction

Open either validation stage and run:

```python
from pathlib import Path
import importlib
import sys

import omni.usd

root_layer = omni.usd.get_context().get_stage().GetRootLayer()
repository_root = Path(root_layer.realPath).parents[1]
sys.path.append(str(repository_root / "tools" / "omniverse"))

import camera_position_bridge

camera_position_bridge.stop()
camera_position_bridge = importlib.reload(camera_position_bridge)
camera_position_bridge.start()
```

Inspect head-on and obliquely in RTX Real-Time and RTX Interactive (Path
Tracing). The Back label must retain one aspect and room scale. Landscape and
portrait windows should reveal different portions without stretching; room
faces, slices, and variants must remain stable.

## Validation record

On 26 August 2026, both renderer modes confirmed a common centred virtual-room
scale on square, landscape, and portrait openings. The Houdini wrapper
reproduced the result across all 15 exported windows, with stable room faces,
slices, variants, and facade material during oblique camera motion.

## Boundary

This record covers flat physical apertures and one material-defined room
extent. It does not group adjacent windows, construct shared room volumes,
parameterise curved individual window surfaces, integrate production glass,
or measure performance.
