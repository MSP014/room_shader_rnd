# Building 150 ORMS Production Integration

## Record

| Field | Value |
| --- | --- |
| Jira | KRM-98 — Integrate ORMS with the Building 150 Production Asset |
| Source asset | `assets/_external/usd/Moskovskiy_av_150/usd/Moskovskiy_av_150.usd` |
| Fixture | `tests/building_150_runtime/` |
| Reference implementation | `tests/shared_room_runtime/`, `tools/omniverse/`, `src/mdl/room_map.mdl` |
| Evidence state | Building 150 debug-atlas, glass-surface, real x1 atlas, luminance-selected emission, and per-depth-slice emission-selector validation passed in both renderers; real x2–x4 content is not yet available |
| Last reviewed | 2 September 2026 |

## Purpose

This record preserves the completed order used to apply the accepted ORMS
technical core to the real Building 150 OpenUSD asset. The first milestone was
a diagnostic scene using the existing labelled debug atlases. The second
integrated the composited room colour with an independently controlled
one-surface glass response. The final KRM-98 milestone used the real x1 atlas
to validate luminance-selected emission and per-slice emission eligibility.

The completed integration record answers four questions:

1. How is the external Building 150 asset composed into a reproducible Kit
   validation scene without rewriting its source layers?
2. Does the production window geometry satisfy the accepted ORMS primvar and
   material contracts?
3. How are the ORMS colour result and the physical window-surface properties
   kept independent?
4. How can selected bright regions of real room textures contribute to
   emission without weakening the existing lookup budget or making
   unsupported lighting claims?

## Accepted contract

This record retains the accepted Building 150 renderer evidence and the
constraints preserved by every completed surface-material change.

### Source and composition ownership

- The Building 150 USD files remain external, read-only production inputs.
- The validation scene references the canonical entry layer instead of copying
  or flattening the building.
- Test-only lighting, cameras, renderer settings, material overrides, and
  runtime-derived values belong to the wrapper stage or ORMS-owned Session
  Layer state.
- Source layers, referenced layers, payloads, authored hierarchy, and
  non-window material bindings are not rewritten.
- Authored `upAxis` and `metersPerUnit` are read from the composed stage. Missing
  or invalid values use the existing visible ORMS fallback; the fixture does
  not silently repair production metadata.

### Required window data

Eligible production windows must satisfy the accepted KRM-93 source contract:

| Primvar | USD type | Interpolation | Responsibility |
| --- | --- | --- | --- |
| `roomID` | `int[]` | `uniform` | Stable room identity and atlas variation. |
| `roomP` | `float3[]` | `vertex` | Per-window room-frame origin. |
| `tangentu` | `float3[]` | `vertex` | Physical horizontal axis and aperture width. |
| `tangentv` | `float3[]` | `vertex` | Physical vertical axis and aperture height. |
| `roomUV` | `texCoord3f[]` | `faceVarying` | Normalised coordinates for the physical aperture. |

The completed audit also identified the window prim paths, mesh orientation,
material subsets, source bindings, building or reference boundaries, payload
state, and instanceability. Missing or incompatible authoring remains a
production-asset blocker and belongs in the Houdini-to-OpenUSD authoring path,
not in permanent validation-wrapper edits.

### Retained ORMS runtime contract

- The camera-position bridge and KRM-93 classifier start only after the stage
  has opened.
- Initial classification and geometry-driven reclassification build a complete
  replacement on an isolated stage composed from the live root and a snapshot
  of the live Session Layer. Intermediate primvar, subset, binding, and
  material edits must not reach the render stage.
- The finished draft is transferred into the owned runtime layer inside one
  `Sdf.ChangeBlock`. The live stage observes one coherent publication instead
  of the clear-and-rebuild notice storm; source-material values and effective
  non-window bindings remain unchanged.
- Derived mappings, x1–x4 family bindings, diagnostics, optional de-instancing,
  and camera values remain in isolated ORMS-owned Session Layer state.
- Runtime materials are created once per enabled x1–x4 atlas family. Building
  150 currently exercises all four families; discovery, material authoring,
  camera updates, and binding remain family-independent.
- ORMS opinions under the production hierarchy are limited to classified
  window prims and their material subsets. No runtime opinion may be authored
  under a source `mtl` or `Looks` hierarchy, and non-window mesh bindings must
  retain their effective source material.
- Camera updates target only `inputs:camera_position_world` on runtime family
  materials and on materials effectively bound to classified windows. A
  stage-inherited camera primvar on `/World` is forbidden for ordinary meshes;
  it is allowed only when a preserved instance requires the inherited primvar
  transport contract.
- x1 remains the mandatory fallback. x2, x3, and x4 are used only when their
  complete debug-atlas families resolve.
- The accepted deterministic `roomID` variation, physical aperture controls,
  shared-room grouping, lifecycle cleanup, and safe fallback behaviour remain
  unchanged.
- The material retains one room-face lookup and four possible depth-slice
  lookups. Building 150 integration does not add a sixth atlas lookup.
- ORMS does not author `/rtx/materialDb/syncLoads` or
  `/rtx/hydra/materialSyncLoads`. These process-wide renderer controls remain
  outside classifier ownership; asynchronous MDL and texture loading is
  observed and timed without serialising unrelated renderer work.
- The source stage must have the same effective state before and after the
  runtime is stopped.

### Observable runtime and transition logging

Every material operation and runtime state that can change the interpretation
of the Building 150 result must produce a structured ORMS diagnostic event.
Important execution steps must never depend on an unrecorded controller,
setting, fallback, or Session Layer transition.

Every record must use `format_room_map_diagnostic_block()` through the shared
`log_room_map_warning()` helper in
`tools/omniverse/runtime/status_log.py`; direct `print` calls, direct Carb log
calls, and locally invented formats are outside the contract. The R&D
Omniverse Console exposes these operational records at warning severity, so
successful steps, state transitions, fallbacks, and failures all use that
visible warning channel. Warning severity is a Console-visibility workaround,
not a claim that a successful operation is faulty. Semantic status belongs in
the diagnostic code, state, outcome, and failure fields.

Each applicable event records:

- owner and process;
- previous state and new state;
- trigger or requested operation;
- affected stage, controller, setting, atlas family, material, or prim scope;
- relevant previous and new setting values;
- outcome, fallback, warning, or failure reason;
- host-local timestamp.

The required events include:

- Kit readiness and the stage-open request boundaries;
- Building 150 stage attachment, replacement, close, and reload;
- camera-bridge, classifier, scene-load probe, renderer-setting owner, and
  controller start, stop, supersession, and teardown;
- settings initialisation and every user-driven change to room-family
  availability, partition seed, instance policy, stage-metrics mode, local
  axis, local scale, and material, glass, or emission controls;
- the request, start, completion, or failure of controlled
  reclassification after a relevant setting or stage change;
- atlas discovery, family enablement, degraded availability, repartitioning,
  x1 fallback, and missing-resource recovery;
- source-material discovery, runtime material creation or reuse, binding
  changes, optional Session de-instancing, and restoration;
- atomic runtime-layer publication, including the publication mode, draft and
  live layer identifiers, live USD notice count, bounded resynced and
  changed-info paths, and any source-material dependency paths invalidated by
  USD;
- the complete bounded set of prim specs actually authored into the runtime
  layer, whether that authored scope is valid, and a separate count of any
  authored source-material paths; a propagated USD dependency notice must not
  be reported as an authored source-material change;
- renderer-setting acquisition, previous value, applied value, and restoration;
- validation-mode and renderer-mode changes that affect the interpretation of
  the result;
- source-safety and cleanup confirmation when ORMS stops or the stage changes.

Logging remains state-transition driven. Per-frame camera values, unchanged
settings, repeated valid resources, and other high-frequency steady state must
not flood the Console. Long operations may emit a bounded heartbeat, while
repeated warning-channel records use deduplication until their underlying
state changes. A log may state only an observable boundary: application
readiness, first viewport frame, stage-open completion, asset-batch state, and
renderer idle must not be treated as interchangeable events.

### Current one-surface material boundary

`src/mdl/room_map.mdl` remains a complete MDL material rather than a standalone
colour-producing node. Its composited room colour now sits beneath a tinted
Fresnel-shaped glass response with four public controls:

| Control | USD type | Default | Responsibility |
| --- | --- | --- | --- |
| `glass_roughness` | `float` | `0.1` | Controls only the squared GGX reflection roughness. |
| `glass_reflectivity` | `float` | `0.04` | Controls normal-incidence reflection strength; one provides an explicit mirror diagnostic. |
| `glass_tint` | `color3f` | `(1, 1, 1)` | Tints the glass base and the visible ORMS room colour. |
| `glass_transmission` | `float` | `1.0` | Controls the visible share of the virtual room beneath the glass. |

The initial three-control implementation fixed the normal-incidence reflection
to the approximately four-percent Fresnel response of IOR 1.5. This made a
correctly sharp `glass_roughness = 0` lobe too weak to assess reliably on a
front-facing dark window. `glass_reflectivity` now owns that independent F0
term through a bounded custom reflection curve. Roughness still changes only
the GGX lobe width: it does not silently change reflection strength.

The corrected response is visually accepted on Building 150 in both RTX
Real-Time 2.0 and RTX Interactive Path Tracing. The accepted views preserve
the ORMS interiors while showing the HDRI in sharp low-roughness reflections;
the accompanying logs report `RealTimePathTracing` and `PathTracing`, four
active family materials, matching x1-x4 values, explicit previous/new setting
transitions, and no MDL compilation failure.

Native Shader Properties streams every intermediate slider and colour-picker
sample. The first observed session therefore produced 1,299 tint, 356
reflectivity, and 32 roughness notices despite correct guarded family
propagation. Runtime preview remains continuous, while the corrected
production logger coalesces one editing gesture into the first
`previous_value` and final `new_value`; a colour gesture likewise produces one
completed colour transition instead of narrating intermediate components.

The single proxy surface cannot use true refractive transmission without
revealing the intentionally absent physical room geometry. The current
`glass_transmission` is therefore a bounded one-surface visibility control:
zero produces the tinted opaque glass base and one reveals the tinted ORMS
result beneath the Fresnel reflection. It does not author
`df::scatter_reflect_transmit`, stage opacity, or fractional cutout.

All four inputs are authored with explicit types and defaults before the
runtime material reaches Hydra. They participate in the existing shared-input
contract, so an edit on any active x1–x4 family propagates to every other
active family and records explicit `previous_value` and `new_value` fields.
The same controls are present on `room_map_single.mdl` for the retained x1
fallback and KRM-93 fixtures.

KRM-92 must represent the single `glass_tint` value through one compact colour
editor row containing:

- a HEX text field accepting `#RRGGBB` without alpha;
- three numeric HSV fields using `H = 0–360°` and `S/V = 0–100%`;
- a small rectangular colour preview beside the editable fields.

HEX, HSV, and the preview are bidirectional views of one underlying linear
`color3f` material input. HEX and HSV use display-sRGB values; the UI converts
to linear RGB before authoring `glass_tint` and converts back when stage or
runtime values change externally. A valid edit updates the other
representations, every active x1–x4 material, and one structured transition
record. Invalid or incomplete text remains visibly invalid and must not author
a partial USD value, trigger family propagation, or emit misleading change
logs. `glass_transmission` remains the independent transparency control and
must not be encoded into the HEX value or preview alpha.

The material continues to own binary `geometry.cutout_opacity` separately for
the physical ORMS aperture and portal contract. Emission selection is likewise
independent from cutout opacity and the glass controls.

### Target surface-material separation

The production surface integration separates the room-image calculation from
the optical properties of the physical window surface:

- the composited ORMS result supplies the room colour used by the surface base
  colour;
- roughness, transmission or artistic opacity, index of refraction, tint, and
  any glass-normal treatment remain independent surface controls;
- ORMS must not derive these controls from the room atlas;
- the existing binary ORMS cutout remains a geometry and portal mask and must
  not be repurposed as fractional glass transparency;
- changing glass roughness or transmission must not change room identity,
  atlas coordinates, shared-room mapping, slice placement, or variant
  selection.

The first implementation keeps one complete MDL material as the smallest
compiler-safe integration. A later refactor may extract the
camera-dependent PIM calculation into a reusable function or structured result
only if the tested Kit MDL compiler accepts the resulting expression graph.
The accepted KRM-93 compact primvar hand-off and shader-DAG safeguards must not
be reopened merely to obtain a different Material Graph shape.

Optional normal detail, dirt, smudges, and other glass contamination controls
are deferred to KRM-100 under the KRM-95 Room Map Shader 2.0 epic. They must
retain neutral defaults, use a documented glass-only UV contract, and justify
any texture lookups added beyond the current room-atlas budget.

### Luminance-selected interior emission

The real x1 atlas includes lamps and baked light pools suitable for the first
emission experiment. The implementation reuses each already sampled room-face
or slice colour and adds no texture lookup. It converts every eligible untinted
linear-sRGB source colour to luminance, applies a smooth threshold mask, and
only then composites and multiplies the selected contribution by
`emission_strength` and the existing glass visibility.
Changing `glass_tint` therefore does not silently change which pixels emit.
The front portal without a depth-slice hit always receives a zero emission
mask. Back, Left, Right, Ceiling, Floor, and actually intersected depth slices
are the only eligible virtual sources; neither `glass_base_colour` nor an
uncovered front portal participates in emission selection.

The public artist controls are:

| Control | Initial contract |
| --- | --- |
| `enable_emission` | Boolean, disabled by default. |
| `emission_slice_1` | Boolean, enabled by default; allows slice 1 to contribute to emission. |
| `emission_slice_2` | Boolean, enabled by default; allows slice 2 to contribute to emission. |
| `emission_slice_3` | Boolean, enabled by default; allows slice 3 to contribute to emission. |
| `emission_slice_4` | Boolean, enabled by default; allows slice 4 to contribute to emission. |
| `emission_strength` | Float, default `1.0`; scales only the selected luminous contribution. |
| `emission_threshold` | Float, default `0.8`; defines the centre of the linear-luminance selection. |
| `emission_softness` | Float, default `0.1`; defines the width of the smooth transition. |

All eight controls use the shared artist-input contract and propagate across
x1–x4. Atlas assets and variant counts remain family-specific. The Building
150 fixture overrides the neutral default with `enable_emission = true` and
`emission_strength = 5.0` so the current pass is directly observable.

An LDR luminance threshold can misclassify white walls, curtains, and highlights
as light sources. A separate emission atlas remains a later option only if art
direction requires an explicit mask and profiling justifies the additional
samples. It is not the current default because it would increase the bounded
five-lookup material budget.

The focused MDL, runtime-authoring, Building 150 fixture, and family-sync run
passes all 27 selected checks. It proves the eight typed emission defaults
before material publication, the unchanged five-lookup budget, per-source
thresholding, slice occlusion with independent emission eligibility, and live
`enable_emission` plus `emission_slice_3` propagation from one family to x1–x4.

Visual acceptance passed in RTX Real-Time 2.0 and RTX Interactive Path Tracing
on 2 September 2026. The retained night captures show that the threshold and
softness controls isolate the intended bright regions of the real x1 interiors
instead of making the entire front portal luminous. The same shared controls
reach the labelled x2–x4 debug families, while glass roughness, reflectivity,
tint, and transmission remain independently editable. The acceptance trace
records explicit previous and new values for every emission edit and matching
x1–x4 family values after each synchronisation.

The first accepted pass also exposed a source-selection defect: a bright but
non-luminous prop on a depth slice, such as a white tablecloth, can pass a pure
luminance threshold. The four `emission_slice_*` flags now gate the emission
contribution of each sampled depth slice independently. A disabled slice still
contributes its normal colour, alpha, and occlusion, so it cannot emit and does
not reveal a luminous wall or a deeper slice through an opaque prop. Room
walls, ceiling, and floor remain governed by the global emission controls.

The retained follow-up captures pass in RTX Real-Time 2.0 and RTX Interactive
Path Tracing with `emission_slice_1 = false`, `emission_slice_2 = true`,
`emission_slice_3 = false`, and `emission_slice_4 = true`. The disabled slices
remain visible and occlusive without contributing to emission, while the two
enabled slices retain their luminous response. The observed diagnostic values
were strength `16000`, threshold `0.16`, and softness `0.1`.

Emission validation must distinguish a self-luminous appearance from actual
illumination of surrounding geometry. Light transport, indirect illumination,
bloom, exposure response, and renderer-mode differences require direct
observation before the material is described as casting light.

## Evidence

### Production input

The external source currently resolves to:

- `assets/_external/usd/Moskovskiy_av_150/usd/Moskovskiy_av_150.usd`;
- `assets/_external/usd/Moskovskiy_av_150/usd/Moskovskiy_av_150 - Thumbnail.png`.

The republished entry layer composes with default prim `/Moskovskiy_av_150`,
Y-up stage metrics, and `metersPerUnit = 1`. Its component payload resolves
without changing the source layers.

`/Moskovskiy_av_150/geo/render/Windows_Glass` contains 928 points and 232 quad
faces. All 232 faces have the accepted `roomID`, `roomP`, `tangentu`,
`tangentv`, and `roomUV` types and interpolations; the authored values contain
eight distinct room IDs. The complete production render set contains 29
meshes, and all 29 pass the same source-primvar type and interpolation audit.
The KRM-98 wrapper deliberately binds ORMS only to `Windows_Glass`.

### KRM-93 fixture reference

The retained shared-room bundle supplies the accepted fixture pattern:

- `tests/shared_room_runtime/test_room_map_shared_rooms_houdini.usda` shows a
  wrapper over a DCC-exported component;
- `tests/shared_room_runtime/launch_shared_rooms_houdini_omniverse.bat` starts
  the existing Kit application and passes the stage to the fixture launcher;
- `tests/shared_room_runtime/kit_exts/msp.orms.fixture_launcher/` waits for Kit
  application readiness and the first viewport frame before opening the heavy
  validation stage;
- `tools/omniverse/reload_room_map_runtime.py` provides the manual R&D runtime
  composition entry point after the stage opens.

The launcher is deliberately scoped. `APP_READY`, the first viewport frame,
and completion of the USD stage-open request are observable. They are not
evidence that MDL compilation, texture upload, or the renderer idle boundary
has completed.

The KRM-93 shared diagnostic formatter and warning-channel routing, controller
lifecycle messages, scene-load heartbeat, atlas-family diagnostics, and
renderer-setting ownership records supplied the starting evidence for the
Building 150 logging contract. KRM-98 extended their coverage only where the
production asset introduced a new observable state or transition.

### Lighting reference

The Building 150 wrapper reproduces the accepted KRM-93 environment:

- one `DomeLight` named `RoomMapEnvironment`;
- `inputs:exposure = 0`;
- `inputs:intensity = 1000`;
- `inputs:texture:file` referencing
  `assets/_external/hdri/kloofendal_48d_partly_cloudy_puresky_4k.exr` through a
  repository-relative asset path;
- dome-light background selection and rotation expressed in the wrapper stage,
  with final orientation adjusted only through an explicit validation choice.

### Current shader evidence

The current implementation proves the five-face room, four alpha slices,
deterministic variants, aperture controls, shared-room mapping, binary portal
cutout, independent glass controls, real x1 textures, and Building 150
compatibility. Luminance-selected LDR emission and the independent per-depth-
slice emission selectors have passed in both required renderer modes.

### KRM-98 defect and correction record — 1 September 2026

The first Building 150 export failed the complete ORMS window-frame audit. All
232 window quads reported invalid `roomP`, tangent lengths and directions,
winding agreement, and `roomUV` corner order. The Houdini network calculated
`roomUV` before the final `roomP`, `tangentu`, and `tangentv` values were in
place. Reordering the nodes so the final room frame precedes the vertex
`roomUV` projection made all 232 windows pass the primitive validation, after
which the production asset was republished.

The first runtime integration also produced one x1 material assignment per
window and repeatedly caused the non-window Building 150 material to render as
a flat brown or white fallback. The accepted correction set:

- groups bindings by atlas family rather than by individual room identity;
- binds a whole classified mesh directly when every face uses one family and
  otherwise creates no more than one material subset per family;
- discovers source Room Map materials only through classified window prims;
- limits runtime hierarchy opinions under the production asset to classified
  window prims and their subsets;
- creates the enabled x1–x4 material families without an x1-only bypass;
- removes the inherited `/World.primvars:ormsCameraPositionWorld` update for
  ordinary meshes and writes camera values only to ORMS material inputs;
- avoids acquiring scene-wide renderer controls that change unrelated
  Building 150 geometry or materials;
- builds the replacement runtime layer on an isolated stage and publishes it
  in one coherent live-stage change.

The accepted visual run preserved the original Building 150 colour while the
debug Room Map material remained visible on `Windows_Glass`. The retained log
showed 28 non-window meshes still bound to
`/World/Building150/mtl/base_lod00_mat`, one classified window mesh bound to
`/__ORMSRuntime/Looks/RoomMapX1`, no authored source-material specs, no
unexpected runtime paths, and an unchanged source material network.

USD may still report `/World/Building150/mtl/base` and
`/World/Building150/mtl/base_lod00_mat` as dependency paths when the window
binding changes. These propagated dependency notices are not authored material
opinions. Runtime diagnostics must continue to report dependency-notice paths
separately from the prim and property specs actually authored in the owned
layer. USD snapshots cannot observe the final rendered material and must not
claim that they can.

### Fixture and control-path corrections — 1 September 2026

The authored `/World/Building150ValidationCamera` was not required by ORMS.
The camera bridge reads the active Kit viewport camera. The fixture camera
also used `focalLength = 35` and `horizontalAperture = 36` as if they were raw
millimetres on a stage whose `metersPerUnit` is `1`. `UsdGeomCamera` lens and
filmback values are measured in tenths of a scene unit, so this produced a
physically enormous camera representation. The Camera prim and its fixture
metadata were removed. If a later capture needs a persistent shot camera,
author all its optical values consistently with the stage units and hide it
from the normal Stage workflow.

The fixture currently exposes `/World/Looks/RoomMapSource` before the runtime
starts and `/__ORMSRuntime/Looks/RoomMapX1` through `RoomMapX4` afterwards. The
first material is the source eligibility/bootstrap binding; the second scope
owns classifier-selected atlas families and makes teardown unambiguous. This
source/runtime split follows the KRM-93 architecture, but exposing both scopes
as artist-facing material libraries is not an acceptable production UX.
KRM-92 must expose one logical assignable ORMS material, use its effective
binding as the eligibility signal, and keep x1–x4 family materials internal to
the extension.

The Building 150 runtime created fallback `room_map.mdl` shaders without the
complete shared artist-input interface before material realisation. Editing
`window_aperture_scale` in Material Graph therefore first created a previously
absent USD input. The observed transition was
`None -> (1, 1) -> (0.85, 0.85)`: the controller propagated the final value to
all four families, but the rendered material did not change and no renderer
material-realisation boundary was observable in the log.

The correction discovers both `room_map.mdl` and `room_map_single.mdl` only
through the selected window binding. It retains compatible source values,
including Building 150's `emission_strength = 0`, and fills every absent input
with the exact USD type and default declared by the public MDL material. The
complete interface is authored on the isolated draft before the runtime layer
is published and before `MATERIAL_UPDATE_SUBMITTED`. Atlas paths and opacity
remain family-specific overrides. A transient missing source value is not
propagated to the other families and is logged as `DEFERRED`; `SYNCHRONISED`
is emitted only when every active family has the same effective non-`None`
value. Subsequent runtime validation proved that edits to scale, offset,
depth, slices, and variation affect the rendered result.

### Adaptive façade classification defect — 1 September 2026

The first Building 150 classifier run extracted 232 valid apertures but
produced 232 x1 groups. The runtime authored all x1–x4 materials correctly;
the final direct binding to `RoomMapX1` was a consequence of the classification
result, not an x1-only material path. Offline reproduction against the same USD
confirmed that every intended same-`roomID` pair was rejected by the global
`edge_gap_tolerance_metres = 0.65`. Building 150 uses different window spacing
on different façade sections: valid same-floor gaps begin at `1.087 m` and the
widest marked neighbour gap is approximately `2.2064 m`. Singleton components
are valid, so the old classifier emitted no diagnostic explaining the fallback.

Replacing `0.65 m` with a Building-specific constant is not an acceptable
correction. Classification must preserve these invariants:

- equal `roomID` is mandatory but not sufficient for windows to share a room;
- different `roomID` values must never be merged;
- a repeated `roomID` cannot skip an intervening physical window;
- floor and façade organisation must isolate local spacing statistics;
- a façade boundary must not prevent a valid corner room from spanning two
  façade directions.

The corrective classifier therefore follows this sequence:

1. Cluster window centres into building-local floor bands. `row_snap` denotes
   the allowed vertical range of centres on one floor; it is not a window-gap
   threshold.
2. Cluster compatible window normals into local façade directions and compute
   one shared horizontal `u` frame per façade component.
3. Sort every façade row by `u` and assign a deterministic façade-local window
   index before considering `roomID`.
4. Build straight adjacency only between consecutive indices. Accept an edge
   only when `roomID`, row, height, and orientation are compatible and the
   centre spacing belongs to the local spacing model of that façade. No global
   metre-space edge-gap constant determines membership.
5. Before room partitioning, run a separate corner pass over the endpoints of
   façade chains. A corner edge requires the same building, row, and `roomID`,
   mutual endpoint proximity, compatible height, and a supported angle between
   the two window normals. Small turns continue a curved façade; deliberate
   turns retain the existing one-corner room mapping.
6. Partition the resulting deterministic linear components into the available
   x1–x4 families and author one derived group identity for every accepted
   room.

Diagnostics record the floor and façade counts, local spacing model,
straight and corner candidate counts, accepted and rejected edges with reasons,
fallback states, and the final x1–x4 group distribution. An ambiguous façade
or corner must degrade explicitly rather than silently becoming a plausible
but unexplained x1 result.

Implementation result on the corrected Building 150 export:

- the obsolete global `edge_gap_tolerance_metres` setting was removed;
- `row_snap` remains a vertical floor-band tolerance only;
- `facade_angle_snap_degrees` controls normal-direction bucketing;
- `maximum_local_spacing_ratio` is dimensionless and compares a candidate
  with its façade-local median centre spacing, falling back to aperture width
  only when a façade segment has too few neighbours to define a median;
- parallel façade bodies are separated by their plane offset before local `u`
  ordering;
- cross-façade links use mutual-nearest aperture endpoints, so gentle façade
  changes and intentional corner rooms remain connected without allowing an
  equal `roomID` to jump over a different window;
- the runtime trace now reports the spacing model, row and façade counts,
  straight and transition candidate counts, accepted and rejected edge counts,
  local pitch range, and the final family distribution.

The deterministic OpenUSD integration test now classifies all 232 apertures as
`98 x1`, `33 x2`, `12 x3`, and `8 x4` groups. Their material subsets cover
`98`, `66`, `36`, and `32` faces respectively, with no spacing rejection and
without changing any source material or non-window mesh binding. The
subsequent interactive Kit validation confirmed the rendered appearance that
the ordinary test runner could not prove.

The first successful interactive run exposed a separate performance defect:
`CLASSIFICATION_COMPLETE.phase_ms` was approximately `14600 ms` for only 232
apertures. Profiling confirmed that the cross-facade mutual-nearest pass
recomputed height bands, normals, angles, and endpoint distances for every
directed endpoint pair. The corrected pass precomputes aperture normals,
vertical intervals, and horizontal endpoint coordinates, then evaluates each
unordered aperture pair once while retaining the same deterministic tie-break
and mutual-nearest rule. The focused profile dropped from 3.62 million calls
and `1.286 s` to 425 thousand calls and `0.167 s`, approximately 7.7 times
faster, without changing any Building 150 classification counter. A repeated
Kit run in RTX Real-Time 2.0 recorded `1574.187 ms` instead of `14600.764 ms`,
approximately 9.3 times faster in the renderer process. The repeated run kept
all 232 mappings, zero diagnostics, zero spacing rejections, 72 straight and
9 transition edges, and the same `98 x1`, `33 x2`, `12 x3`, `8 x4`
distribution. Source USD remained unchanged, runtime-layer scope remained
valid, and all room atlas inputs resolved. This timing evidence validates the
optimisation; the later cross-renderer captures supplied the final visual
acceptance of the complete Building 150 integration.

A maintenance pass then replaced the opaque facade-key tuple with a named
internal contract, centralised vertical-band compatibility, split facade
construction into bounded helpers, and documented why physical transition
candidates are ranked before the mandatory `roomID` check. Facade-angle
snapping now uses an exact circular subdivision, so an arbitrary requested
step cannot create an asymmetric bucket at the `-180`/`+180` seam. The focused
classifier and Building 150 regression suite retained every counter above.

### Cross-renderer and material-control validation — 1 September 2026

The Building 150 debug result is accepted in RTX Real-Time 2.0 and RTX
Interactive Path Tracing. The retained captures show the same x1–x4 room
grouping, labelled atlas orientation, unchanged non-window building material,
and readable HDRI lighting in both modes. Material edits visibly change the
interiors. The `19:22:06Z` trace records synchronised x1–x4 values for
`window_aperture_scale`, `window_aperture_offset`, and `room_depth`, including
the accepted `room_depth = 2.0` test.

The interiors follow the active viewport camera without resets, flips, or
variant changes. The ceiling plane on upper floors appears to move somewhat
more strongly than expected during the tested camera motion. This is retained
as a minor art-direction observation rather than a confirmed defect or a
KRM-98 acceptance blocker. Any attempt to tune it is deferred to KRM-99 under
the KRM-95 Room Map Shader 2.0 epic.
The current MDL material has no focal-length input: it forms the room-space ray
from `camera_position_world` and the shaded world-space surface position.
Focal length therefore cannot directly tune the current calculation. If art
direction still requires reduced vertical parallax in ORMS 2.0, a controlled
follow-up must compare the existing room and aperture controls before any
explicit virtual-ray bias is proposed. That control must not be labelled as
focal length unless the runtime supplies and the shader consumes a defined
lens model.

The same trace exposed a material-transition logging defect. Synchronisation
events reported the final `family_values`, but omitted the required explicit
`previous_value` and `new_value`. The controller now retains the last complete
shared value. Successful notices for one `(source_path, input)` editing gesture
are coalesced over 200 ms into one record that preserves the first
`previous_value` and final `new_value`; material propagation itself remains
continuous. A transient unavailable value still emits an immediate `DEFERRED`
record, and runtime teardown flushes a completed edit before detaching its
layer. Focused controller coverage passes. The 2 September live Kit trace
retains explicit `previous_value` and `new_value` fields for completed
`window_aperture_scale` edits, confirming the coalesced production record in
addition to focused controller coverage.

The trace ends while the runtime is active because the current R&D workflow is
started through the manual snippet in `009_shared_multi_window_rooms.md` and
has no artist-facing lifecycle controls. Interactive stop, reload, restart,
stage-replacement, and cleanup validation therefore moves to KRM-92. It is not
a Building 150 shader blocker. The startup
`REPOSITORY_SOURCE_MISSING` warning is a separate Kit integration issue caused
by the probe extension still resolving the pre-`runtime/` module locations; it
does not invalidate the accepted Building 150 material result.

### Real x1 atlas integration — 2 September 2026

The first real atlas family is now available under
`assets/_external/tex/room_maps/` as 56 contiguous 1080×1080 RGBA UDIM tiles,
`room_map.1001.png` through `room_map.1056.png`. These textures currently cover
x1 rooms only. They do not establish real x2–x4 family content.

The Building 150 source material now authors
`room_maps/room_map.<UDIM>.png` with `room_variant_count = 56`. Runtime
authoring treats that source value as the canonical x1 fallback, resolves its
relative asset path against the source layer before copying it into the
anonymous Session Layer, and retains the independent eight-tile labelled
debug atlases for x2, x3, and x4. Each runtime family authors its own matching
variant count, so an x2–x4 material cannot request nonexistent tiles 1009–1056.
Both MDL materials now convert a zero-based variant index into the canonical
ten-column UDIM grid: index 9 selects `1010`, index 10 selects `1011`, and index
55 selects `1056`. This replaces the earlier single-row offset that was valid
only for the eight-tile debug atlases.

The focused Building 150 fixture and MDL variant suites pass all 16 checks,
including the complete 56-tile x1 sequence, the authored real-atlas path,
unchanged eight-tile x2–x4 debug families, and the multi-row UDIM offsets.
`RUNTIME_MATERIALS_AUTHORED` now records `atlas_assets` and
`atlas_variant_counts` for every family through the standard warning-visible
trace.
Visual acceptance of the real x1 rooms passed in RTX Real-Time and RTX
Interactive Path Tracing on 2 September 2026. The accepted captures show real
x1 interiors while x2–x4 rooms retain their expected labelled debug atlases.
The corresponding trace reports 98 x1, 33 x2, 12 x3, and 8 x4 classified room
groups, the real 56-variant x1 source, the three eight-variant debug sources,
no classifier diagnostics, no unresolved textures, unchanged source USD state,
and unchanged non-window bindings.

The ORMS classification, authoring, and first material submission remain at
approximately 2.00 seconds: the runtime layer published at 1.938 seconds, the
material update submitted at 2.004 seconds, and the first frame followed at
2.032 seconds. The first asynchronous asset batch, however, completed in
100.424 seconds compared with 4.196 seconds for the preceding all-debug run,
an observed increase of approximately 96.23 seconds. Both traces report the
same opaque `max_total_files=55`, and the longest new loading status names the
x3 shader rather than an individual x1 texture. The trace therefore does not
justify attributing the full delay solely to the 56 PNG files. This is retained
as a non-blocking cold-load performance observation, not as an accepted
production baseline or an ORMS CPU regression.

The real atlas drove the completed luminance-selected emission experiment. The
fixture enables emission at strength `5.0`, threshold `0.8`, and softness
`0.1`. Visual acceptance passed in both required renderer modes. The
`22:07:23Z` trace records global emission edits from `5.0` through `10000.0`,
threshold edits ending at `0.5`, softness `0.5`, enable toggles, and matching
x1–x4 values after every completed edit. It reports no ORMS or MDL error, no
unresolved texture, unchanged source USD state, and valid runtime binding
scope. Four generated MaterialX warnings concern unused transmission inputs in
the source building material and are unrelated to the ORMS MDL modules.

The same trace reports a 140.098-second first asynchronous asset batch with 87
files and names the x1 runtime shader for 139.849 seconds. Classification,
runtime authoring, publication, and first material submission still complete
in approximately 1.9 seconds. Later material-edit batches complete in roughly
0.11–0.43 seconds with zero newly loaded files. The cold-load result remains a
renderer-side observation rather than an ORMS CPU regression or a production
baseline.

## Reproduction

The following is the retained execution and reproduction sequence. All eleven
steps were completed for KRM-98. The imperative wording describes how to
reproduce the accepted result; it does not mark the steps as pending work.

### Current execution status — 2 September 2026

| Step | Status | Evidence or remaining boundary |
| --- | --- | --- |
| 1. Production inventory | Complete | The entry layer, metrics, hierarchy, render meshes, windows, and source bindings are recorded. |
| 2. Window contract audit | Complete | All 232 window quads pass after the Houdini node-order correction. |
| 3. Isolated fixture | Complete | The dedicated wrapper and Building 150 fixture bundle are in place. |
| 4. HDRI environment | Complete | The accepted HDRI and facade lighting are observed in RTX Real-Time and RTX Interactive Path Tracing. |
| 5. Source material path | Complete | Only `Windows_Glass` is eligible, all x1–x4 atlases resolve, non-window bindings remain unchanged, and the source material supplies the shared emission controls. |
| 6. Kit launcher | Complete | The dedicated BAT path opens the bootstrap and Building 150 stages through the retained fixture launcher. |
| 7. Runtime inspection | Complete | Start, classification, material publication, typed defaults, source isolation, renderer changes, and material-control propagation pass. Glass inputs use the same x1–x4 sync path, and focused coverage proves one coalesced completed record with the first previous and final new value. UI lifecycle validation remains in KRM-92. |
| 8. Debug-texture milestone | Complete | Saved views in both renderers show coherent x1–x4 runs, camera-following interiors, and unchanged building materials. The stronger upper-floor ceiling motion is a retained non-blocking tuning observation. |
| 9. Real room texture and surface | Complete | The one-surface controls and 56-variant real x1 atlas pass in RTX Real-Time and RTX Interactive Path Tracing. Family-specific variant counts are correct, x2–x4 retain their expected debug atlases, and real x2–x4 content is a later asset milestone. |
| 10. Authored luminous sources | Complete | The no-extra-lookup LDR luminance mask and shared x1–x4 controls pass in both renderers. Independent `emission_slice_1`–`emission_slice_4` eligibility prevents bright non-luminous props from emitting without changing colour, opacity, occlusion, or the lookup budget. |
| 11. Evidence and contract | Complete | The fixture, Houdini correction, classifier result, source-safety proof, logs, optimisation timings, cross-renderer captures, glass-surface acceptance, real x1 atlas acceptance, and focused plus live previous/new coalescing proof are recorded. |

The formal count is eleven complete steps with no partial step. KRM-98's
Building 150 integration scope is complete. Real x2–x4 content is a later asset
milestone, and UI lifecycle evidence belongs to KRM-92.

### Step 1 — Inventory the composed production asset

1. Open the canonical Building 150 entry layer read-only.
2. Record the default prim, root hierarchy, references, payloads, variants,
   instanceability, `upAxis`, and `metersPerUnit`.
3. Identify the complete set of window meshes and the non-window materials
   that must remain untouched.
4. Record the authored window material and subset structure.
5. Confirm that asset resolution succeeds without changing the production
   source.

### Step 2 — Audit the ORMS window contract

1. Inspect `roomID`, `roomP`, `tangentu`, `tangentv`, and `roomUV` on every
   intended window family.
2. Verify their USD types, interpolation, value counts, orientation, and
   consistency across payload or reference boundaries.
3. Check winding, degenerate frames, mixed normals, disconnected runs, and
   same-floor adjacency against the accepted KRM-93 limits.
4. Record every unsupported window group before authoring overrides.
5. If the required source data is missing, stop the fixture implementation and
   define the corresponding Houdini export correction.

### Step 3 — Create an isolated Building 150 fixture bundle

1. Create `tests/building_150_runtime/` as a separate KRM-98 validation bundle
   rather than extending the historical KRM-93 fixtures.
2. Add a wrapper stage named `test_room_map_building_150.usda`.
3. Reference the external Building 150 entry layer through a relative asset
   path.
4. Keep test cameras, lighting, renderer settings, and material overrides in
   the wrapper.
5. Reuse the existing fixture-launcher extension unless a Building 150
   requirement proves that a small, documented extension is necessary.

### Step 4 — Reproduce the accepted HDRI environment

1. Add the Kloofendal 4K HDRI through `RoomMapEnvironment`.
2. Retain the accepted exposure and intensity values for the first comparison.
3. Set a deterministic dome rotation that makes the facade readable and record
   it in the wrapper.
4. Use the active viewport camera for interactive validation. Do not add a
   visible Camera prim solely to seed the runtime camera bridge.
5. Confirm that the background and facade illumination match in RTX Real-Time
   and RTX Interactive before diagnosing ORMS colour differences.

### Step 5 — Establish the source x1 material path

1. Provide the source Room Map material expected by the runtime classifier.
2. Bind or override only eligible window faces in the wrapper or ORMS-owned
   Session Layer state.
3. Retain every non-window binding.
4. Resolve the complete x1–x4 debug UDIM families under
   `assets/_external/tex/`.
5. Keep `emission_strength` at the existing diagnostic setting; do not add or
   validate production emission controls in this phase.

### Step 6 — Add the reproducible Kit launcher

1. Add a Building 150 BAT launcher modelled on
   `launch_shared_rooms_houdini_omniverse.bat`.
2. Resolve the repository root, Kit repository, extension folder, and stage
   path from the launcher location rather than from a personal absolute path.
3. Quote every Windows path and fail visibly when the Kit launcher, stage, or
   fixture extension is missing.
4. Launch the existing `msp.case03.blackwell.kit` application without modifying
   the Kit repository.
5. Let the lightweight bootstrap stage reach application readiness and its
   first viewport frame before opening Building 150.
6. Report stage-open completion without claiming renderer or material
   completion.
7. Emit one structured state transition for every launcher boundary, including
   validation failure and cancellation.

### Step 7 — Start and inspect the ORMS runtime

1. Start the accepted manual runtime through
   `tools/omniverse/reload_room_map_runtime.py` after Building 150 opens.
2. Confirm the camera bridge, classifier, atlas inventory, runtime material
   families, Session Layer owner, and diagnostic heartbeat.
3. Confirm that the camera bridge targets only classified window material
   inputs and that no inherited `/World.primvars:ormsCameraPositionWorld`
   exists unless preserved instances explicitly require it.
4. Confirm that x1 fallback remains available before accepting x2–x4 groups.
5. Confirm that every shared artist input exists with its typed default on all
   enabled runtime families before the first material submission.
6. Inspect warnings before interpreting missing or incorrect rooms as shader
   faults.
7. Change a representative accepted material setting and confirm that one
   completed editing gesture logs its first previous value, final new value,
   trigger, synchronisation scope, outcome, and coalesced notice count.
8. Retain stop, reload, restart, stage-replacement, and cleanup validation for
   the artist-facing KRM-92 lifecycle controls rather than the manual snippet.

### Step 8 — Validate the debug-texture milestone

1. Select a representative facade section containing single windows and at
   least one supported multi-window run if the asset provides one.
2. Confirm correct face orientation, aperture proportions, labelled atlas
   regions, stable room identity, and depth-slice order.
3. Move the active viewport camera through the exterior path and check for resets,
   flips, seams, stretching, or variant changes.
4. Confirm that unsupported groups use visible diagnostics and safe x1
   fallback rather than speculative shared rooms.
5. Repeat the accepted view in RTX Real-Time and RTX Interactive or Path
   Tracing.
6. Record before-and-after captures and preserve the exact fixture and camera.
7. Reconfirm that no source layer changed.
8. Retain the concise diagnostic sequence that explains stage open, runtime
   start, classification, material binding, renderer mode, and fallback state
   for the accepted capture.

### Step 9 — Integrate a real room texture with the surface material

1. Retain the implemented one-surface Fresnel-shaped reflection layer while
   the labelled debug atlas makes room mapping directly inspectable.
2. Author `glass_roughness`, `glass_reflectivity`, `glass_tint`, and
   `glass_transmission` with their declared types and defaults before the first
   Hydra material submission.
3. Keep artistic transmission bounded to the visibility of the ORMS result;
   do not refract rays into absent physical room geometry.
4. Keep the binary ORMS portal cutout separate from every glass control.
5. Change each glass input in Kit and confirm x1–x4 propagation, explicit
   previous/new logs, readable parallax, and stable reflections in both
   renderer modes.
6. Use the source material's authored real atlas for x1 with its matching
   variant count. Retain family-specific debug atlases and counts for x2–x4
   until corresponding real families exist.
7. Retain the accepted one-surface material. A separate front glass surface
   was not required because interior readability and facade reflections both
   passed.

### Step 10 — Add emission for authored luminous sources

1. Begin only when a real atlas contains known luminous features.
2. Keep emission disabled by default and verify that the base-colour result is
   unchanged.
3. Test the LDR luminance threshold and softness contract using the existing room
   samples, without adding texture lookups.
4. Confirm that ordinary bright surfaces do not become unintended emitters.
5. Validate the luminous appearance, exposure response, and renderer-mode
   behaviour separately.
6. Use a representative mixed on/off combination of `emission_slice_*` flags
   and confirm that disabled slices retain colour and occlusion but contribute
   no emission.
7. Treat the accepted captures as proof of self-luminous appearance only; no
   indirect-lighting claim was recorded from a bright pixel or bloom.
8. Consider an additional emission atlas only after the luminance approach fails an
   explicit art-direction requirement and the lookup cost is measured.

### Step 11 — Retain evidence and update the contract

1. Record fixture paths, source provenance, camera, HDRI, renderer modes,
   validation date, and accepted material settings.
2. Retain representative structured logs for successful startup, one setting
   change, one controlled reclassification, and one fallback where available.
3. Document any Houdini export correction separately from Session Layer runtime
   data.
4. Replace the KRM-98 pending statements in this record with observed evidence.
5. Record that no remaining production-asset blocker was transferred to
   KRM-91; packaged Kit-extension work remains a separate boundary.

## Validation record

OpenUSD integration, material controls, camera motion, and the debug result in
both required renderer modes have passed. The accepted evidence now includes:

- the Building 150 wrapper opens reproducibly through the BAT launcher;
- the external source asset and all non-window bindings remain unchanged;
- eligible windows satisfy the required ORMS source contract;
- the debug atlas is correctly mapped on a representative production facade;
- supported x1–x4 groups remain coherent during camera motion;
- safe fallback and diagnostics cover unsupported production geometry;
- the result is accepted in RTX Real-Time and RTX Interactive Path Tracing;
- the runtime authors typed `glass_roughness`, `glass_reflectivity`,
  `glass_tint`, and `glass_transmission` controls on every active family before
  publication;
- important startup, setting, classification, binding, fallback, and renderer
  transitions are recorded through the shared structured ORMS
  formatter and its warning-visible Console channel;
- the one-surface implementation keeps room projection and the binary portal
  cutout independent from glass roughness, tint, and artistic transmission;
- the runtime authors typed `enable_emission`, `emission_strength`,
  `emission_threshold`, `emission_softness`, and `emission_slice_1` through
  `emission_slice_4` controls on every active family and synchronises artist
  changes across x1–x4;
- the accepted night captures prove luminance-selected self-emission and
  compatible glass controls in both renderer modes without making an
  unsupported indirect-lighting claim.

The complete KRM-98 Building 150 integration scope is accepted. Recorded Kit
evidence shows readable parallax and visible glass-control response in both
renderers.
Focused controller coverage proves that one completed setting gesture retains
its first previous value and final new value while material propagation remains
continuous. The accepted live Kit trace additionally records explicit
`previous_value` and `new_value` fields for completed
`window_aperture_scale` edits.

The real x1 atlas authoring contract and its 56-tile resource sequence pass
focused fixture validation. Saved RTX Real-Time and RTX Interactive Path
Tracing captures prove the real x1 textures, camera-following room mapping, and
glass surface on Building 150; labelled x2–x4 debug rooms remain deliberately
visible where no corresponding real atlas family exists.

## Boundary

This record does not yet prove:

- that window selections beyond the explicitly eligible `Windows_Glass`
  material can be assigned through the future KRM-92 production UI;
- that the KRM-92 artist-facing lifecycle controls complete their full
  start/reload/stop/stage-replacement transition matrix;
- production real-atlas behaviour for x2, x3, or x4 rooms;
- KRM-100 normal-map, dirt, smudge, or contamination controls;
- that an emissive room texture casts useful light onto other geometry;
- multi-building, KRM-96 procedural-layout, KRM-97 curved-window, or packaged
  KRM-91 extension behaviour.

The external Building 150 source and HDRI remain outside the public repository
history. Any reproducibility claim must therefore name their hydration or
provenance boundary without copying private or heavy source assets into the
tracked fixture bundle.
