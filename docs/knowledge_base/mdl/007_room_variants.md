# Deterministic Room-Variant Selection

## Record

| Field | Value |
| --- | --- |
| Jira | KRM-90 — Automatic Debug Room Variant Selection |
| Implementation | `exts/msp.orms.runtime/data/mdl/room_map.mdl` |
| Automated evidence | `tests/test_room_map_variants.py`, `tests/test_room_map_variants_houdini.py`, `tests/test_room_map_texture_assets.py` |
| Validation scenes | `tests/test_room_map_variants.usda`, `tests/test_room_map_variants_houdini.usda` |
| Evidence state | Renderer-validated on Omniverse- and Houdini-authored geometry |
| Last validated | 26 August 2026 |

## Purpose

The Room Map material selects one atlas variant from an MDL tiled texture by
using an explicit integer `roomID`. Selection is stable for every polygon with
the same identifier and independent of adjacency, primitive order, world
position, camera motion, renderer mode, and stage reload.

This record concerns atlas identity only. Equal `roomID` values do not by
themselves create shared room space; that later contract is documented in
[009 — Shared Multi-Window Rooms](009_shared_multi_window_rooms.md).

## Accepted contract

### Material and geometry inputs

| Input or primvar | Default | Contract |
| --- | --- | --- |
| `room_atlas` | empty | MDL tiled texture addressed with `<UDIM>`. |
| `room_variant_count` | `1` | Available variants; values below one become one. |
| `variation_seed` | `0` | Material-level deterministic distribution seed. |
| `roomID` | lookup fallback `0` | Integer primvar, normally `uniform` per window polygon. |
| `roomP`, `tangentu`, `tangentv` | zero vectors | Unindexed vertex `float3` room frame. |
| `roomUV` | `st` fallback | Dedicated face-varying `texCoord3f` window coordinate. |
| `st` | texture coordinate 0 | Compatibility path for earlier hand-authored fixtures. |

The validation atlas is
`assets/_external/tex/room_map_debug/room_map_debug.<UDIM>.png`. Variant zero
selects tile 1001, variant one selects 1002, and so on. The adjacent-window
families x2, x3, and x4 also contain tiles `1001…1008`; their completeness is
checked before shared-room classification consumes them.

### Deterministic mapping

The material calculates:

```text
positive_modulo(
    roomID * 1664525 + variation_seed * 1013904223,
    max(room_variant_count, 1)
)
```

The selected zero-based index is added to atlas U. MDL uses the integer U tile
for UDIM selection and the fractional coordinate within that tile. Every room
face and depth slice receives the same tile selection, and the material retains
exactly five texture lookups.

For three variants, the accepted examples are:

| `roomID` | Seed 0 | Seed 1 |
| --- | --- | --- |
| `0` | index 0 / tile 1001 | index 1 / tile 1002 |
| `1` | index 2 / tile 1003 | index 0 / tile 1001 |
| `2` | index 1 / tile 1002 | index 2 / tile 1003 |

### Houdini transport

The retained export uses:

- `roomID` as an integer `uniform` primvar;
- `roomP`, `tangentu`, and `tangentv` as unindexed vertex `float3` primvars;
- `roomUV` as an unindexed face-varying `texCoord3f` primvar;
- the building's ordinary UV channel unchanged.

The canonical Vertex Wrangle runs over Houdini vertices after Room Map Frame:

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

Using `point()` is required because Room Map Frame authors point attributes in
Houdini. Reading nonexistent vertex frame values collapses the result to
`(0.5, 0.5)`.

## Evidence

The isolated scene has six disconnected polygons arranged as `0, 1, 2` and
`2, 0, 1`. It proves stable, spatially separated same-ID pairs with one
material binding.

The DCC path retains:

- `hip/room map test 004.hiplc` as the KRM-90 source;
- `assets/_external/usd/test_grid_wins/test_grid_wins.usd` and its layered
  payload, geometry, and material assets;
- `tests/test_room_map_variants_houdini.usda` as the capture wrapper that
  changes only the exported window material binding.

The Houdini component contains 15 disconnected quads, repeated room IDs, 15
independent frames, and 60 face-varying `roomUV` values. The dedicated
coordinate matches the frame projection while the ordinary building UV does
not, proving that production UV repacking is unnecessary.

Supporting references:

- [NVIDIA MDL SDK tiled-resource example](https://github.com/NVIDIA/MDL-SDK/blob/master/examples/mdl/nvidia/sdk_examples/tutorials.mdl)
- [NVIDIA MDL 1.10.2 specification](https://raytracing-docs.nvidia.com/mdl/specification/MDL_spec_1.10.2_14Mar2025.pdf)
- [Omniverse Primvar Lookup Int](https://docs.omniverse.nvidia.com/extensions/latest/ext_material/ext_material-graph/nodes/Constants_State_Primvars/primvar_int.html)

## Reproduction

Open either validation scene, start `camera_position_bridge.start()`, and
inspect it in RTX Real-Time and RTX Interactive (Path Tracing).

For the isolated stage, confirm the seed-0 table, move the camera, set seed 1,
switch renderer modes, and reload. Same-ID pairs must remain matched throughout.

For the Houdini wrapper, confirm that all 15 windows render complete parallax
rooms through `roomUV`, spatially separated equal IDs select the same tile,
and the facade retains its exported material.

## Validation record

On 26 August 2026, the isolated stage retained expected same-ID pairs at both
seeds while the camera moved, renderer mode changed, and the stage reloaded.
The Houdini component reproduced the same variant contract on all 15 windows
without replacing the facade material or ordinary UV layout.

Both scenes were accepted in RTX Real-Time and RTX Interactive (Path Tracing).
Retained captures are `docs/img/krm90/krm90_01.png` through
`docs/img/krm90/krm90_04.png`.

## Boundary

The accepted `roomUV` projection is for planar quad windows. Curved, concave,
convex, or irregular individual surfaces belong to KRM-97. Shared room space
across adjacent windows belongs to KRM-93; production Building 150 robustness
remains KRM-65 work.
