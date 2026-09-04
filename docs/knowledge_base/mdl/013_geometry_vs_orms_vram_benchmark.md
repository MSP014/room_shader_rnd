# Geometry Rooms versus ORMS VRAM Benchmark

## Record

| Field | Value |
| --- | --- |
| Jira | Follow-up to KRM-92; issue not yet assigned |
| Implementation target | Reproducible geometry-room and ORMS comparison scenes using the same building, room families, variants, camera, renderer settings, and 1080x1080 source textures |
| State | Planned — unverified calculated hypothesis; empirical renderer measurements are pending |
| Last reviewed | 4 September 2026 |

## Purpose

This record defines a like-for-like benchmark for the VRAM and runtime cost of
fully modelled interior rooms versus ORMS representations. The comparison asks
how much texture memory ORMS can save when both approaches provide five
interior categories, four room-size families per category, and four visible
variants per family.

> **Evidence status:** every VRAM figure and ratio in this draft is a calculated
> hypothesis. None has been confirmed empirically in Omniverse, and none is an
> accepted renderer benchmark result.

The calculation must not be quoted as measured evidence until the reproduction
and acceptance passes have been completed. Actual residency can differ because
of GPU compression, texture streaming, resource deduplication, driver-managed
budgets, renderer caches, and acceleration-structure allocations.

## Accepted starting point

### Shared content target

Both paths represent the same high-level content inventory:

| Property | Value |
| --- | ---: |
| Interior Sets | 5 |
| Room families per Set | 4 (`x1`, `x2`, `x3`, `x4`) |
| Complete visual variants per family | 4 |
| Complete room variants | `5 * 4 * 4 = 80` |
| Texture resolution | 1080x1080 |
| Texture precision | 8-bit channels |
| Mip-chain multiplier | approximately `4 / 3` |

The benchmark deliberately gives every ORMS family the same 1080x1080
resolution. It does not reproduce the current production library's larger x1
tiles, because the purpose is to compare representations at equal source-map
resolution.

Facade textures, window geometry, renderer frame buffers, and the common
building are excluded from the analytical comparison because both paths need
them. The measured benchmark must still report their shared baseline.

### Geometry-room path

Each of the 20 room families contains:

- 10-15 furniture slots;
- 2-3 model variations per slot, available across the four complete room
  variants;
- the typical metallic/roughness PBR channels: base colour, normal,
  roughness, metalness, and ambient occlusion.

The primary calculation assumes a production-conscious three-texture layout
for every unique furniture variation:

1. one RGBA8 base-colour texture;
2. one RGBA8 normal texture;
3. one RGBA8 packed ORM texture containing ambient occlusion, roughness, and
   metalness.

This preserves all requested PBR channels without inflating the comparison
with five wasteful RGBA resources. A secondary sensitivity case retains five
separate RGBA8 maps to show the cost of an unoptimised material library.
Every furniture variation is charged exactly one PBR material set, even though
production furniture often contains several sub-materials. Room-shell textures
for walls, floors, and ceilings are also excluded. Both choices bias the draft
in favour of the geometry path.

Across the 20 room families, the resident asset-library range is therefore:

```text
low  = 5 Sets * 4 families * 10 slots * 2 variations = 400 furniture assets
mid  = 5 Sets * 4 families * 12.5 slots * 2.5 variations = 625 furniture assets
high = 5 Sets * 4 families * 15 slots * 3 variations = 900 furniture assets
```

The four complete variants place 800-1,200 furniture instances. Correct
instancing can share vertex buffers and BLAS for repeated assets, but the
primary calculation assumes that every named furniture variation has its own
material texture set. A separate sensitivity case covers texture reuse among
model variations.

### ORMS path

Each complete room variant is represented by one RGBA8 ORMS atlas tile. The
room appearance and depth-slice masks are baked into that resource; furniture
does not retain separate base-colour, normal, roughness, metalness, or ambient
occlusion textures at runtime.

```text
5 Sets * 4 families * 4 variants = 80 ORMS texture resources
```

This draft assumes that all 80 resources are resident. That is deliberately
conservative for ORMS and avoids relying on texture streaming or lazy material
creation before those behaviours have been measured.

## Draft calculation

### One 1080x1080 RGBA8 texture

The approximate full-mip residency of one texture is:

```text
1080 * 1080 pixels * 4 bytes * (4 / 3 mip factor)
    = 6,220,800 bytes
    = 5.93 MiB
```

Disk size is not used in this calculation. PNG compression can make an image
small on disk while the renderer still expands it into a much larger GPU
resource.

### ORMS texture residency

```text
80 textures * 6,220,800 bytes
    = 497,664,000 bytes
    = 474.61 MiB
    = 0.464 GiB
```

The analytical ORMS texture budget is therefore approximately **0.46 GiB**.

### Geometry texture residency: packed PBR baseline

Each furniture asset uses three RGBA8 resources:

```text
3 textures * 5.93 MiB = 17.80 MiB per furniture asset
```

| Geometry case | Unique furniture assets | Texture VRAM | Relative to ORMS |
| --- | ---: | ---: | ---: |
| Low: 10 slots, 2 variations | 400 | 6.95 GiB | 15.00x |
| Mid: 12.5 slots, 2.5 variations | 625 | 10.86 GiB | 23.44x |
| High: 15 slots, 3 variations | 900 | 15.64 GiB | 33.75x |

Under the primary assumptions, ORMS needs approximately **15-34 times less
texture VRAM**, a reduction of approximately **93.3-97.0%**. This comparison
does not yet charge the geometry path for vertex buffers, index buffers, BLAS,
TLAS instance data, or additional material state.

On a 12 GiB GPU, the high geometry case cannot fit its uncompressed texture
set even before geometry and Path Tracing resources are added. The mid case is
also likely to exceed the effective Windows GPU-memory budget once the shared
scene and renderer allocations are included. These are predictions to test,
not accepted runtime results.

### Sensitivity: five separate PBR maps

If base colour, normal, roughness, metalness, and ambient occlusion are each
stored as separate RGBA8 resources, every furniture asset needs approximately
29.66 MiB:

| Geometry case | Texture VRAM | Relative to ORMS |
| --- | ---: | ---: |
| Low | 11.59 GiB | 25.00x |
| Mid | 18.10 GiB | 39.06x |
| High | 26.07 GiB | 56.25x |

This case is retained as an upper-bound warning, not as the preferred
production comparison.

### Sensitivity: model variations share textures

If the 2-3 geometry variations for each furniture slot share one packed PBR
texture set, the unique texture-set count falls from 400-900 to 200-300:

| Shared-texture case | Unique PBR texture sets | Texture VRAM | Relative to ORMS |
| --- | ---: | ---: | ---: |
| 10 slots per family | 200 | 3.48 GiB | 7.50x |
| 15 slots per family | 300 | 5.21 GiB | 11.25x |

Even this favourable geometry assumption predicts approximately 7.5-11.25
times the ORMS texture residency. Broader sharing of a small common furniture
and material library could reduce that ratio further and must be reported by
the measured benchmark rather than hidden inside an assumed asset count.

### Costs deliberately excluded from the headline ratio

The following allocations must be measured but are not guessed here:

- geometry vertex and index buffers;
- RTX BLAS per unique furniture mesh and TLAS instance data;
- room-shell materials and their PBR textures;
- renderer-specific material and shader records;
- texture page alignment, sparse residency, streaming, and cache retention;
- GPU compression such as BC7, BC5, or packed single-channel formats;
- ORMS runtime primvars, material instances, and shared shader resources;
- geometry-room lighting, emissive meshes, and any per-room light data.

These omissions make the 15-34x figure a texture-only comparison. Geometry and
ray-tracing acceleration structures are expected to widen the measured gap,
while aggressive texture reuse and compression can narrow it.

## Implementation plan

### Fixtures

Create two stages that reference the same exterior building and expose the
same 80 complete room variants through the same windows:

1. `geometry_rooms_5x4x4.usda` uses modelled room shells and instanced
   furniture;
2. `orms_rooms_5x4x4.usda` uses five ORMS Interior Sets with x1-x4 families
   and four variants in each family.

Retain three geometry asset manifests for the low, midpoint, and high cases.
Every manifest must list the exact number of unique meshes, texture resources,
materials, instances, triangles, and texture-sharing relationships. The ORMS
manifest must list all 80 atlas resources and prove that every map is
1080x1080 RGBA8.

### Controlled conditions

- Use the same workstation, driver, Kit build, viewport dimensions, camera,
  stage metrics, lighting, and visible windows.
- Run RTX Real-Time and RTX Interactive Path Tracing as separate benchmark
  passes.
- Restart Kit between representation changes so one renderer texture cache
  cannot contaminate the other result.
- Close or hold constant unrelated GPU applications.
- Let asset loading complete, keep the camera stationary, and record the
  settled value after at least 60 seconds.
- Run every case three times and report the median as well as the range.
- Record the global GPU baseline before opening the stage. Windows WDDM may
  not expose reliable per-process values through `nvidia-smi`, so retain the
  Kit HUD and renderer telemetry alongside the system reading.

### Measurements

Record at minimum:

- physical VRAM capacity and current WDDM budget;
- peak and settled GPU-memory use above the clean Kit baseline;
- process working set and private commit;
- stage-open and material-ready times;
- steady viewport FPS and frame time;
- Path Tracing time to the agreed sample count;
- runtime material, unique texture, mesh, triangle, BLAS, and instance counts;
- any eviction, allocation, device-loss, or material-compilation warning.

Run `Restore Original Asset` and `Start` repeatedly in the ORMS fixture. A
settled memory baseline that rises after every identical cycle is a lifecycle
defect and must be investigated separately from the representation cost.

### Scaling sequence

Run the geometry path incrementally:

1. low case: 10 slots and 2 variations;
2. midpoint case: 12-13 slots and alternating 2-3 variations;
3. high case: 15 slots and 3 variations.

If a case exceeds the GPU budget, record the last completed scale and the
exact failure or eviction behaviour. Do not lower texture resolution or hide
assets only in the failing geometry stage; any quality change must be applied
to both representations and treated as another benchmark row.

## Acceptance plan

The record may move from `Draft` to measured evidence only when:

1. both fixtures expose the same five Sets, four room families, and four
   complete variants;
2. source texture dimensions, formats, mip policy, and compression are
   recorded rather than inferred from filenames;
3. unique versus instanced geometry and unique versus shared textures are
   reported explicitly;
4. clean-start RTX Real-Time and RTX Interactive Path Tracing measurements are
   retained for all cases that fit the device budget;
5. the final comparison separates shared scene cost, texture cost, geometry
   and acceleration-structure cost, and renderer cache behaviour;
6. the result reports the measured ratio even if it contradicts the 15-34x
   analytical hypothesis.

The intended showreel summary is one compact comparison showing identical
visible room variety, settled VRAM, FPS or frame time, and the number of unique
assets required by each representation.

## Boundary

- This is a draft analytical model, not a completed benchmark.
- Equal room count and external appearance do not imply equal physical
  capability. Modelled interiors can provide free camera access, dynamic
  relighting, cast shadows, and object-level interaction that baked ORMS rooms
  do not provide.
- The headline calculation assumes one unique packed PBR texture set per
  furniture variation. Reusing materials across rooms can substantially reduce
  geometry residency.
- The calculation assumes uncompressed resident RGBA8 resources. GPU-native
  compression, sparse textures, and renderer streaming must be measured in
  separate rows.
- The ORMS result assumes one RGBA8 atlas tile per complete room variant and
  does not add per-room PBR maps. Changing that resource contract invalidates
  the ratio.
- No conclusion about visual quality, temporal stability, load latency, or
  leak freedom may be derived from the arithmetic alone.
