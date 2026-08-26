# Deterministic Room-Variant Selection

## Purpose

`src/mdl/room_map.mdl` can select one room atlas variant from an MDL tiled
texture by using an explicit integer `roomID` primvar. The selection is stable
for every polygon carrying the same identifier: it does not depend on mesh
adjacency, primitive order, world position, camera movement, render mode, or
stage reload.

The Omniverse-authored validation scene is `tests/test_room_map_variants.usda`.
It has six disconnected window polygons, three repeated room identifiers, one
material binding, and a three-tile diagnostic UDIM sequence.

The companion scene, `tests/test_room_map_variants_houdini.usda`, applies the
same material to a 15-window component exported from a DCC. Together the two
scenes separate shader behaviour from data-transport behaviour: the first
proves deterministic selection, and the second proves that the required
primvars survive the authored OpenUSD path. Houdini is the retained DCC source
for this test, but the material contract itself is expressed in OpenUSD terms.

This contract deliberately separates two questions:

1. **Variant identity:** disconnected polygons with the same `roomID` select
   the same atlas tile. This is the scope of KRM-90.
2. **Shared room space:** windows facing different directions can reveal one
   coherent interior volume. This requires shared frame construction and is
   the scope of KRM-93.

## Material and geometry contract

| Input or primvar | Default | Contract |
| --- | --- | --- |
| `room_atlas` | empty texture | MDL tiled texture using a `<UDIM>` token. |
| `room_variant_count` | `1` | Number of available variants. Values below one are treated as one. |
| `variation_seed` | `0` | Material-level integer that changes the deterministic distribution. |
| `roomID` | lookup fallback `0` | Integer USD primvar, normally authored with `uniform` interpolation so each polygon has one logical room identifier. |
| `roomP`, `tangentu`, `tangentv` | zero-vector lookup fallback | Unindexed vertex `float3` primvars defining the window centre and horizontal and vertical room axes. A usable room requires a non-degenerate frame. |
| `roomUV` | `st` | Dedicated face-varying `texCoord3f` coordinates in `[0, 1]`, aligned with the room axes for each logical window. The shader uses the first two components. |
| `st` | renderer texture coordinate 0 | Legacy mesh coordinates used only when `roomUV` is absent, preserving the earlier hand-authored validation scenes. |

The USD tiled texture path in the validation scene is:

```text
../assets/_external/tex/roommap_debug.<UDIM>.png
```

Variant index zero selects tile 1001, index one selects tile 1002, and index
two selects tile 1003. The implementation adds the selected zero-based index
to the atlas U coordinate. For an MDL UV-tile set, the integer part of the
coordinate selects the tile and the fractional part addresses the texture
inside it. The MDL specification also states that wrap and crop parameters are
ignored for UV-tile textures, so retaining `tex::wrap_clip` does not alter tile
selection.

References:

- [NVIDIA MDL SDK tiled-resource example](https://github.com/NVIDIA/MDL-SDK/blob/master/examples/mdl/nvidia/sdk_examples/tutorials.mdl)
- [NVIDIA MDL 1.10.2 specification, texture functions](https://raytracing-docs.nvidia.com/mdl/specification/MDL_spec_1.10.2_14Mar2025.pdf)
- [Omniverse Primvar Lookup Int](https://docs.omniverse.nvidia.com/extensions/latest/ext_material/ext_material-graph/nodes/Constants_State_Primvars/primvar_int.html)

## Deterministic mapping

The material calculates:

```text
positive_modulo(
    roomID * 1664525 + variation_seed * 1013904223,
    max(room_variant_count, 1)
)
```

This is an identity-based mixer, not a spatial random-number source. The
result therefore remains identical wherever a given `roomID` is used. Every
room face and all four depth slices receive the same selected UDIM coordinate,
so the public material still performs exactly five atlas lookups.

For the Omniverse-authored scene with three variants, the expected mappings are:

| `roomID` | Seed 0 | Seed 1 |
| --- | --- | --- |
| `0` | index 0 / tile 1001 | index 1 / tile 1002 |
| `1` | index 2 / tile 1003 | index 0 / tile 1001 |
| `2` | index 1 / tile 1002 | index 2 / tile 1003 |

The six window polygons are arranged in two rows. Their authored identifiers
are `0, 1, 2` on the lower row and `2, 0, 1` on the upper row. This makes every
same-identifier comparison spatially separated and easy to read.

## Omniverse-authored Composer validation

Open `tests/test_room_map_variants.usda` in USD Composer. In the Script Editor,
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
    "/World/Looks/RoomMapVariants/Shader.inputs:camera_position_world"
)
```

Then check:

1. At seed 0, both `roomID=0` windows use tile 1001, both `roomID=1`
   windows use tile 1003, and both `roomID=2` windows use tile 1002.
2. Orbit and dolly the camera. The parallax changes, but variant identity does
   not.
3. Set `variation_seed` to 1. The distribution changes to the Seed 1 column
   above while same-identifier pairs remain matched.
4. Switch between RTX Real-Time and RTX Interactive (Path Tracing).
5. Reload the stage and repeat the seed 0 comparison.

## DCC-exported geometry validation (Houdini source)

The DCC-exported test is deliberately small, but follows the layered USD
composition expected from a production asset. Its retained evidence is:

- `hip/room map test 004.hiplc` — the Houdini source scene;
- `assets/_external/usd/test_grid_wins/test_grid_wins.usd` — the exported
  component root with payload, geometry, and material layers;
- `tests/test_room_map_variants_houdini.usda` — the capture-ready wrapper that
  preserves the facade material and overrides only the window material.

In Houdini:

1. Create disconnected window quads suitable for the Room Map Frame SOP.
2. Author a repeated integer primitive attribute `roomID` so spatially
   separated windows share deterministic interior identities.
3. Generate the accepted `roomP`, `tangentu`, and `tangentv` frame attributes.
4. After Room Map Frame, run the Vertex Wrangle documented below on the window
   geometry. It authors a separate vertex `roomUV` attribute in `[0, 1]` for
   each logical window without replacing or repacking the model's ordinary
   `uv` attribute.
5. Export through the normal Solaris/USD path, preserving `roomID` as an
   integer `uniform` primvar, the frame attributes as unindexed vertex
   `float3` primvars, and `roomUV` as an unindexed face-varying `texCoord3f`
   primvar.
6. Bind one `room_map` MDL material to all window polygons and use the
   three-tile diagnostic atlas.

### Vertex Wrangle used before export

The retained Houdini asset uses an Attribute Wrangle SOP configured with
`Run Over = Vertices`. It is placed after Room Map Frame and restricted to the
window geometry that will receive the MDL material. The snippet reads the
point-class frame attributes explicitly, projects each window vertex into that
frame, and stores normalised coordinates in the dedicated vertex attribute
`roomUV`:

```vex
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
```

Using `point()` here is deliberate: the Room Map Frame attributes are point
attributes in Houdini. Binding `roomP`, `tangentu`, or `tangentv` directly as
vertex attributes would create zero-valued vertex data and collapse every
generated coordinate to `(0.5, 0.5)`. After USD export, the point frame becomes
unindexed `vertex` data and the Houdini vertex `roomUV` becomes unindexed
`faceVarying` data.

This projection is the accepted contract for the planar quad windows used by
KRM-90. It does not claim a general unwrap for curved, concave, convex, or
irregular window surfaces; that parameterisation remains KRM-97 work.

After export, inspect the composed USD in Composer and repeat the
Omniverse-authored validation sequence. Matching results prove that the
Houdini-authored component preserves the OpenUSD material contract. General
Building 150 robustness, references, payloads, and repeated production updates
remain KRM-65 work.

## Recorded Omniverse-authored result

The Omniverse-authored USDA stage was visually accepted on 26 August 2026 in USD
Composer. Six disconnected windows retained the expected same-`roomID` pairs
at seed 0 while the camera moved. Changing `variation_seed` changed the atlas
distribution without breaking pair consistency. The same deterministic result
was observed in RTX Real-Time and RTX Interactive (Path Tracing).

The Python contract tests separately validate the Omniverse-authored scene,
primvar types and interpolation, material binding, UDIM resource,
deterministic mapping, the named `roomUV` path with legacy `st` fallback, and
the five-lookup limit.

## Recorded DCC-exported static result

The DCC-exported component, authored in Houdini for this test, was statically
accepted on 26 August 2026. It contains 15 disconnected window quads, repeated
integer `roomID` values, 15 independent room frames, and 60 face-varying
`roomUV` values. Every exported coordinate matches the corresponding `roomP`,
`tangentu`, and `tangentv` frame. The ordinary `st` channel is deliberately not
suitable for Room Map projection, proving that the MDL material uses the
dedicated primvar rather than requiring the building UV layout to be replaced.

## Recorded DCC-exported renderer result

The DCC-exported component geometry was visually accepted on 26 August 2026 in
USD Composer. All 15 windows rendered complete parallax rooms through the
dedicated `roomUV` primvar while the ordinary `st` channel remained unsuitable
for Room Map projection. Spatially separated windows carrying the same `roomID`
retained the same diagnostic UDIM variant. The labelled room faces and depth
slices remained correctly oriented as the camera moved.

The accepted result was observed in RTX Real-Time and RTX Interactive (Path
Tracing). The facade retained its original Houdini material because the
capture wrapper overrides only the window material.

Retained captures:

- `docs/img/krm90/krm90_01.png` — Omniverse-authored test scene in RTX
  Real-Time;
- `docs/img/krm90/krm90_02.png` — Omniverse-authored test scene in RTX
  Interactive;
- `docs/img/krm90/krm90_03.png` — DCC-exported test geometry in RTX Real-Time;
- `docs/img/krm90/krm90_04.png` — DCC-exported test geometry in RTX Interactive.

## Current validation boundary

The Omniverse-authored and DCC-exported scenes are renderer-validated, the
static Houdini-to-USD contract is retained, and all capture scenes are
reproducible. The implementation and acceptance evidence required by KRM-90
are complete. Shared room space across differently oriented windows remains
outside this contract and belongs to KRM-93.
