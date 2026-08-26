# Window Aperture Scale and Offset Contract

## Purpose

The Room Map material represents a physical window aperture separately from
the virtual room dimensions. This prevents a landscape or portrait window from
being treated as a square front plane while retaining one room atlas and the
existing five-lookup sampling budget.

The implementation retains the magnitudes of the accepted Room Map Frame
vectors as physical geometry evidence:

- *length(tangentu)* is the physical window width;
- *length(tangentv)* is the physical window height.

The vectors are normalised for the room-frame orientation. Their raw
magnitudes define only the physical aperture extent. The material's
*room_uniform_scale* defines the common X/Y virtual-room extent, and
*room_depth* multiplies that extent along depth. Every material instance can
therefore keep one proportionate room size across differently shaped windows.

## Geometry contract

*roomUV* remains a face-varying *texCoord3f* in the normalised range [0, 1]
on every planar window. It locates a point inside the aperture but does not
encode the physical aspect ratio.

The required USD primvars are:

| Primvar | Type | Interpolation | Purpose |
| --- | --- | --- | --- |
| roomP | float3[] | vertex | Room-frame origin. |
| tangentu | float3[] | vertex | Horizontal frame direction and physical width. |
| tangentv | float3[] | vertex | Vertical frame direction and physical height. |
| roomUV | texCoord3f[] | faceVarying | Normalised aperture coordinate. |
| roomID | int[] | uniform | Stable room-variant identity when variation is enabled. |

The retained Houdini Vertex Wrangle from the KRM-90 validation remains valid:

    int point_number = vertexpoint(0, @vtxnum);

    vector position = point(0, "P", point_number);
    vector room_position = point(0, "roomP", point_number);
    vector axis_u = point(0, "tangentu", point_number);
    vector axis_v = point(0, "tangentv", point_number);

    vector delta_p = position - room_position;

    float room_u =
        dot(delta_p, axis_u) / max(dot(axis_u, axis_u), 1e-8) + 0.5;
    float room_v =
        dot(delta_p, axis_v) / max(dot(axis_v, axis_v), 1e-8) + 0.5;

    v@roomUV = set(room_u, room_v, 0.0);

For a 2:1 or 1:2 window this produces the same [0, 1] coordinate range as
for a square window. The material maps that range into physical aperture space
inside one common room. With *room_uniform_scale* `2`, a square `1:1` window
maps to `U = .5…1.5, V = .5…1.5`; a landscape `2:1` window maps to
`U = 0…2, V = .5…1.5`; and a portrait `1:2` window maps to
`U = .5…1.5, V = 0…2`. The visible aperture is therefore centred in the same
proportionate room, and the atlas is never stretched to the aperture aspect
ratio.

## Material inputs

| Input | Default | Contract |
| --- | --- | --- |
| room_uniform_scale | 1 | Common X/Y extent of the virtual room for every window bound to the material. |
| window_aperture_scale | (1, 1) | Independent horizontal and vertical aperture scale about the window centre. |
| window_aperture_offset | (0, 0) | Independent horizontal and vertical aperture offset in normalised room space. |
| window_shift | (0, 0) | Retained legacy offset. It is added after aperture scale and offset so default aperture controls preserve existing scenes. |

The material uses the common room extent, then centres the physical aperture
in that room:

    room_extent = room_uniform_scale
    aperture_extent = (width, height) * safe_scale
    aperture_uv =
        (roomUV.xy - 0.5) * aperture_extent
        + 0.5 * room_extent
        + (window_aperture_offset + window_shift) * room_extent

It then constructs the ray origin in the uniformly scaled virtual room with:

    ray_origin = float3(
        aperture_uv.x,
        aperture_uv.y,
        0.0
    )

The direction ray remains the physical camera-to-surface direction. Aperture
scale and offset affect only the aperture position and extent, never the
virtual-room perspective. The side planes remain at `x = 0`,
`x = room_extent`, `y = 0`, and `y = room_extent`; room-face and slice
coordinates are normalised by *room_extent* before atlas mapping. The depth is
`room_depth × room_extent`.

Zero or negative aperture scales are limited to the material epsilon. An
offset can intentionally place part of the aperture outside the front plane.
Invalid frame-vector magnitudes retain the existing fallback-colour path.
These bounds avoid unstable intersections and invalid texture coordinates.

## Validation scenes

*tests/test_room_map_apertures.usda* is the isolated material proof. It
contains square 1:1, landscape 2:1, and portrait 1:2 windows, together with
three additional centred default windows that retain separate material
instances for the aperture controls. The six visible windows share the
default centred aperture, so the visual check isolates room-size and aspect
behaviour. *tests/test_room_map_apertures.py* validates the static geometry,
primvar, material-input, aperture-scale, aperture-offset, fixed-virtual-volume,
and texture-lookup contracts.

The DCC-exported proof follows the KRM-90 composition pattern:

1. Retain the Houdini source scene and its layered USD component.
2. Reference that component from a capture-ready USDA wrapper.
3. Override the material binding only on the exported window geometry.
4. Preserve the exported facade material and all component layers.
5. Verify physical dimensions against the exported *tangentu* and *tangentv*
   magnitudes before renderer validation.

The retained KRM-94 Houdini source is *hip/room map test 005.hiplc*. Its
layered component is rooted at
*assets/_external/usd/test_grid_wins_diff/test_grid_wins_diff.usd*, and the
capture-ready wrapper is *tests/test_room_map_apertures_houdini.usda*.

## Camera-position bridge

The camera-position bridge is a singleton update subscription. It discovers
every composed `inputs:camera_position_world` attribute in the active stage,
then updates all discovered inputs from the active viewport camera. One
bootstrap therefore works unchanged for both validation scenes: four material
instances in the isolated scene and one shared material instance in the
Houdini-exported wrapper.

Open either `tests/test_room_map_apertures.usda` or
`tests/test_room_map_apertures_houdini.usda` in USD Composer and run this in
the Script Editor. `stop()` is deliberately called before reload, so an older
subscription cannot survive while the updated helper module is loaded:

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

When the check is complete, stop the subscription:

```python
camera_position_bridge.stop()
```

Inspect each scene head-on and obliquely in RTX Real-Time and RTX Interactive
(Path Tracing). The expected result is one undistorted, proportionate room
scale in every physical window shape. Landscape and portrait apertures reveal
different portions of that room, but the `Back` marker must retain its aspect
ratio and room scale. Room-face, slice, and room-variant behaviour must remain
stable.

## Current validation boundary

Renderer validation completed on 26 August 2026 in RTX Real-Time and RTX
Interactive (Path Tracing). The isolated scene confirmed a common centred
virtual-room scale across square, landscape, and portrait apertures. The
Houdini wrapper confirmed the same contract on all fifteen exported windows,
with stable room faces, slices, and UDIM variants during oblique camera motion.

The isolated USD and Python contract, Houdini-exported component, and capture
wrapper are retained with the implementation.
