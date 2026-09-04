# Shared Multi-Window Room Volume Contract

## Record

| Field | Value |
| --- | --- |
| Jira | KRM-93 — Shared Multi-Window Room Volume and Aspect Controls |
| Implementation | `exts/msp.orms.runtime/msp/orms/classification/`, `exts/msp.orms.runtime/msp/orms/shared_room/`, `exts/msp.orms.runtime/msp/orms/scene/`, `exts/msp.orms.runtime/msp/orms/runtime/reload_room_map_runtime.py`, `exts/msp.orms.runtime/data/mdl/room_map.mdl`, `exts/msp.orms.runtime/data/mdl/room_map_single.mdl` |
| Automated evidence | `tests/shared_room_runtime/room_run/`, `tests/shared_room_runtime/shared_room/`, `tests/shared_room_runtime/runtime/`, `tests/shared_room_runtime/integration/`, `tests/shared_room_runtime/test_fixture_launcher_bundle.py` |
| Validation scenes | `tests/shared_room_runtime/test_room_map_shared_rooms_omniverse.usda`, `tests/shared_room_runtime/test_room_map_shared_rooms_houdini.usda`, `tests/shared_room_runtime/test_room_map_shared_rooms_instances.usda`, `tests/shared_room_runtime/test_room_map_shared_rooms_houdini_instances.usda` |
| Evidence state | Renderer-accepted in both required RTX modes; focused automated evidence recorded; final repository quality gate reserved for pre-commit |
| Last reviewed | 31 August 2026 |

## Purpose

KRM-93 makes one coherent virtual room visible through a geometrically
connected run of flat window apertures carrying the same `roomID`. Coplanar
and bay runs use one to four apertures. A bounded one-turn corner may contain
one to four apertures on each of its two facade legs, for at most eight
physical apertures. The runtime derives grouping, atlas family, and rectangular
footprint from the already-open composed stage. It does not require `floorID`,
`roomInstanceID`, `windowIndexInRoom`, `windowCountInRoom`, or other new
Houdini-authored identity attributes.

## Accepted contract

### Source asset contract

Eligible window meshes retain the existing ORMS data and a source x1 binding.
The retained fixtures use the renderer-validated `exts/msp.orms.runtime/data/mdl/room_map_single.mdl`;
classified faces receive an ephemeral binding to `exts/msp.orms.runtime/data/mdl/room_map.mdl`:

| Primvar | Type | Normal interpolation | Responsibility |
| --- | --- | --- | --- |
| `roomID` | `int[]` | `uniform` | Atlas identity and the grouping label for adjacent apertures. |
| `roomP` | `float3[]` | `vertex` | Existing per-window frame origin. |
| `tangentu` | `float3[]` | `vertex` | Existing physical horizontal axis and width. |
| `tangentv` | `float3[]` | `vertex` | Existing physical vertical axis and height. |
| `roomUV` | `texCoord3f[]` | `faceVarying` | Existing normalised aperture coordinate. |

Disconnected equal-`roomID` windows remain independent rooms. Adjacent
equal-`roomID` windows within the same building boundary and compatible floor
band form one candidate run. Source layers, references, payloads, and Houdini
assets are never rewritten.

### Geometric classification

The pure classifier uses physical metres after resolving stage metadata. Two
apertures are neighbours only when all of these are true:

- their building or reference roots match;
- their `roomID` values match;
- their bottom heights differ by no more than `0.25 m` and their vertical
  overlap is at least `50%` of the shorter aperture;
- their nearest horizontal edges are no more than `0.65 m` apart;
- their flat-face normals turn by no more than `100°`.

The resulting graph must be a deterministic linear chain. Branched, cyclic,
ambiguous, degenerate, or otherwise unsupported components fall back to
independent x1 rooms and emit formatted ORMS diagnostics. Primitive order is
not an identity input.

### Room sizes and long runs

Runs of one, two, three, or four apertures select x1, x2, x3, or x4 when that
family is enabled and all eight of its UDIM files are present. x1 is mandatory.

A linear component with exactly one turn at or above the corner threshold is
split into two facade legs before generic long-run partitioning. If both leg
counts are between one and four and both required atlas families are usable,
the whole component remains one logical room. An `A x B` corner uses one fixed
world-space box whose width is `max(A, B)` and whose depth is `min(A, B)`.
The longer leg defines the box orientation; an equal-leg tie follows the first
leg of the deterministic geometric traversal. Every aperture uses that same
basis and box size. Atlas binding remains facade-specific: leg A uses xA and
leg B uses xB, while both keep the same `roomID`, variant, and derived group
identity. Thus a `4 x 1` room is always one 4-wide, 1-deep box; its long facade
binds x4 and its side facade binds x1 without rotating the box. Reversing input
primitive order does not change the result. If either required family is disabled or
incomplete, each straight leg returns to the normal deterministic partition
policy. Components with more than one sharp turn are unsupported and fall
back to independent x1 mappings with a formatted diagnostic.

Longer runs are partitioned into contiguous x1–x4 rooms using a stable hash of
the geometric run, the local `partition_seed`, and the current offset. The
selection is pseudo-random but deterministic across camera motion, primitive
reordering, renderer changes, and stage reloads. Disabled or incomplete atlas
families are excluded before partitioning.

### Ephemeral direct mapping

The runtime authors the following face primvars into one anonymous sublayer
beneath the stage Session Layer. The detailed affine fields remain available
for diagnostics, while the last two rows are the compact compiler-facing
contract consumed by MDL:

| Derived primvar | USD type | Interpolation | Space and default | Meaning |
| --- | --- | --- | --- | --- |
| `ormsRoomSize` | `int[]` | `uniform` | Unitless; `1` | Width of the shared x1–x4 room box. |
| `ormsRoomDepthSize` | `int[]` | `uniform` | Unitless; `1` | Depth multiplier of the same box; x1 for ordinary runs. |
| `ormsRoomGroupId` | `int[]` | `uniform` | Unitless; `0` | Deterministic runtime group identity. |
| `ormsMappingValid` | `int[]` | `uniform` | Boolean integer; `0` | Whether the shared affine map is safe to consume. |
| `ormsRoomAxisU` | `float3[]` | `uniform` | World-space direction; `(1, 0, 0)` | Horizontal axis of the shared room basis. |
| `ormsRoomAxisV` | `float3[]` | `uniform` | World-space direction; `(0, 1, 0)` | Vertical axis of the shared room basis. |
| `ormsRoomPositionWorld` | `float3[]` | `uniform` | World-space point; `(0, 0, 0)` | Shared room-frame origin consumed directly by MDL. |
| `ormsRoomScale` | `float3[]` | `uniform` | Shared-room scale; `(1, 1, 1)` | World-to-room scale that fits the complete classified box. |
| `ormsRoomMapOrigin` | `float3[]` | `uniform` | Centred pre-scale room frame in metres; `(0, 0, 0)` | Per-aperture corner of the affine `roomUV` embedding. |
| `ormsRoomMapAxisU` | `float3[]` | `uniform` | Centred pre-scale room frame in metres; `(1, 0, 0)` | Full 3D embedding of the source `roomUV` U tangent. |
| `ormsRoomMapAxisV` | `float3[]` | `uniform` | Centred pre-scale room frame in metres; `(0, 1, 0)` | Full 3D embedding of the source `roomUV` V tangent. |
| `ormsPhysicalNormal` | `float3[]` | `uniform` | World-space normal; `(0, 0, 1)` | Stable aperture normal used by both RT and PT for physical backface cutout. |
| `ormsSliceStartDepth` | `float[]` | `uniform` | Normalised room depth; `0` | Depth at which the rectangular rear volume begins; zero for flat and corner rooms. |
| `ormsRoomParameters` | `float3[]` | `uniform` | Packed unitless values; `(11, 0, 0)` | `(10 * width + depth, slice start depth, portal mode)`. Portal mode is `0` for fallback, `1` for a front aperture, and signed `2` for a depth-aligned side aperture. |
| `ormsRoomMapPosition` | `float3[]` | `faceVarying` | Shared room-mapping coordinates; `(0, 0, 0)` on unmapped face vertices | Affine `roomUV` embedding evaluated at every face vertex. |
| `ormsPrimaryApertureMinU012` | `float3[]` | `uniform` | Shared room U; `(0, -1, -1)` | Minimum U bounds for physical primary-aperture intervals 0–2; negative values disable unused intervals. |
| `ormsPrimaryApertureMaxU012` | `float3[]` | `uniform` | Shared room U; `(1, -1, -1)` | Maximum U bounds for physical primary-aperture intervals 0–2. |
| `ormsPrimaryApertureU3` | `float3[]` | `uniform` | Shared room U; `(-1, -1, 0)` | Minimum and maximum U bounds for interval 3, with the third component reserved. |
| `ormsApertureMaskOffsetU` | `float[]` | `uniform` | Shared room U; `0` | Per-face U offset used when evaluating the physical aperture mask. |

This is a direct coordinate map, not an editable window index. Physical window
widths, heights, gaps, facade turns, and depth offsets are projected into a
fixed frame rather than selected from the camera direction. Coplanar runs and
faceted bay windows use one common 3D frame for the whole group. Matching
physical points on a shared bay-aperture edge therefore produce the same 3D
room-space point from either face. The physical aperture planes may turn, but
the virtual back wall and side walls remain one rigid box and do not rotate
independently per aperture.

The group basis is selected deterministically. An odd group uses its central
aperture. An even group uses its two central apertures when their aligned
normals are parallel within 1°; otherwise it uses the aligned mean normal of
the whole group. The selected normal and stage-up direction are rebuilt into
one orthonormal frame, so the virtual back wall is perpendicular to the shared
normal and both virtual side walls remain perpendicular to that back wall.
The MDL ray starts from the aperture's full 3D position in this frame, not from
an artificial `z = 0` plane. `window_aperture_scale` scales the complete group
around its shared centre, preserving the same edge position on both sides of a
facet boundary.

The default corner threshold is 60°. Exactly one neighbouring pair turning by
at least that amount classifies a component as a bounded `Corner`, instead of
letting the bay basis average across a 90° turn. The longer facade is embedded
on the front boundary of one box. The perpendicular facade is embedded on the
connected left or right boundary and spans the full derived depth. Both use
the same fixed world-space basis, so crossing the physical corner cannot
replace the room coordinate frame with a 90°-rotated frame. Physical gaps stay
in the test geometry, while the virtual side portal is fitted to the common box
boundary. The 30°, 45°, and 8°-step fixtures remain rigid bays. The threshold
is a persistent local Preference and does not modify source USD.

For a shared bay, `ormsRoomScale` maps the projected outer horizontal bounds
to `0…ormsRoomSize` and the vertical bounds to `0…1`. At the default aperture
scale, the virtual side walls therefore meet the outer edges of the first and
last windows. Changing `window_aperture_scale` intentionally introduces or
removes a symmetric margin around the complete group.

### Material and atlas contract

The runtime creates at most four shared material instances, one for each usable
x1–x4 atlas family. Each runtime material specialises the canonical source
`room_map` material and overrides only `room_atlas`. Artist inputs such as
`window_aperture_scale`, room depth, slice controls, and variation settings
therefore have one source of truth and continue to compose into every family.
The retained labelled debug families use tiles `1001…1008` from their own
directories under `assets/_external/tex/`. The source material may instead
author an independent x1 atlas and matching variant count. Canonical UDIM
addressing uses ten tiles per row, so variant index `n` maps to
`(u = n % 10, v = n / 10)` and can continue beyond tile `1010`. Face subsets
bind the selected family without changing the source material binding. A
rectangular corner may bind two such subsets on one mesh, keyed by the same
group identity but different xA/xB families. Atlas family is deliberately
separate from the common box width and orientation. Matching production
families must retain compatible variant identity when both sides of one room
use different atlas sizes.

The MDL material consumes `ormsRoomParameters` and the baked
`ormsRoomMapPosition`, scales virtual width by the decoded room width, and
scales virtual depth by the decoded room depth. The authored
`room_depth` remains an artist multiplier on that derived footprint. All
apertures in a valid group reveal one continuous volume while preserving
physical aperture aspect, room scale, window shift, aperture controls,
deterministic `roomID` variation, four depth slices, and the existing total of
five atlas lookups.

This compact hand-off is also a compiler-safety requirement for the tested Kit
build. Reconstructing the affine position from separate origin/axis primvar
lookups and then repeating five ray/plane distance expressions caused the RTX
MDL backend to expand one source shader into a pathological native DAG. The
classifier now bakes only camera-independent affine work, while MDL retains all
camera-dependent parallax, aperture controls, wall tracing, and slice sampling.
The room shell is traced once and returns both cross-atlas coordinates and the
nearest distance, avoiding repeated wall-selection expression trees.

For a bay room, the classifier places the shared room-frame front plane at the
frontmost aperture corner and derives `ormsSliceStartDepth` as the complete
projected depth to the rearmost aperture corner. This separates the projecting
bay from the rectangular rear volume without a hand-authored bay parameter. The
authored `room_depth` remains the complete depth of that rear volume; the bay
extension is added in front of it. The back wall therefore lies at
`ormsSliceStartDepth + room_depth`, while the four artist percentages are
remapped over the unchanged `room_depth` interval beginning at the throat.
Angled apertures cannot cut the front slice, and a deep bay cannot compress
the four slices into its leftover depth. Flat and bounded corner rooms author
zero and keep their existing full-depth distribution. This adds no texture
lookup and remains one identical derived value for every aperture in a group.

The shared room shell extends continuously across the complete combined depth.
Its left wall, right wall, floor, and ceiling span from the frontmost bay extent
to the back wall, so a bay with no aperture on the shared reference plane cannot
expose an unfilled or atlas-clamped strip of the room envelope. All four
surfaces use one depth coordinate over
`ormsSliceStartDepth + room_depth`. The throat remains a separate visibility
boundary only for the four depth slices: the shared camera ray must enter the
rear room before a slice may contribute. This keeps slice cards out of the
narrow bay while preserving a closed shell and one perspective across central
and angled apertures. Flat and corner paths remain unchanged.

For a depth-aligned corner portal, the exact physical primary-aperture
intervals also bound slice visibility. A slice contributes only when its ray
intersection lies before the primary-window exit plane. The four existing
slice alpha values are composited into one coverage value; a binary threshold
keeps a covered slice pixel on the virtual surface and cuts only an uncovered
physical window opening. This prevents the primary-window cutout from removing
a foreground slice, preserves the exact gaps between adjacent apertures, and
does not add a sixth atlas lookup or a new USD primvar.

The classifier marks every ephemeral family Material prim with
`omni:rtx:enableCutoutOpacity = true`. While the manual R&D runtime is active,
it also owns `/rtx/material/omniRtxEnableOpacityOverride = true`: NVIDIA defines
the Material attribute as inactive unless that renderer setting is enabled.
The MDL definition also exposes the renderer-recognised
`uniform bool enable_opacity = true` convention and gates its binary
`geometry.cutout_opacity` expression with that parameter.
The previous setting is restored on stop/reload. Without the complete pair,
RTX may classify a custom MDL material as opaque and skip the any-hit cutout
path, leaving virtual primary-window openings black in RTX Interactive / Path
Tracing even when the same binary mask is correct in RTX Real-Time. The
15-second scene-load heartbeat records the active renderer mode, global
override, and cutout opt-in state of every runtime family material.

### Stage metrics, instances, and local settings

`Auto from stage` reads authored `upAxis` and `metersPerUnit`. Missing or
invalid metadata emits a diagnostic and uses a local Y-up, 1-metre fallback
without authoring metadata. `Local override` can interpret the stage as Y-up
or Z-up with an explicit metres-per-unit value, again without changing the
source stage.

The default instance policy is `Preserve`. A preserved instance that contains
eligible Room Map meshes emits an `INSTANCE_PRESERVED_X1_FALLBACK` diagnostic
and creates one camera-bridgeable runtime x1 material. A collection binding on
each instance root targets only mesh proxies carrying the complete Room Map
source-primvar contract. It does not author descendants of instance proxies,
and non-window descendants retain their Houdini-exported material bindings.
The lightweight x1 shader reads `tangentu`, `tangentv`, and `roomUV` without
compiling the classified five-lookup/cutout graph inside a prototype.
It also reads `roomID` and applies the same seeded eight-way UDIM selection as
the classified material, so Preserve keeps stable per-room texture variation
instead of sampling x1 tile `1001` for every aperture.
Instanceable wrapper stages predeclare the inherited uniform
`ormsCameraPositionWorld` primvar on `/World`, before Hydra first syncs the
prototype-bound x1 material. Runtime camera motion changes only that primvar's
Session Layer value. A primvar created for the first time after the prototype
has rendered is not accepted as a reliable Preserve startup contract because
the material may not discover that late scene-data channel until its render
representation is rebuilt.
`Session de-instance` authors `instanceable = false` only in the owned runtime
layer and classifies each reference independently; removing the layer restores
instancing.

The manually registered `ORMS Classifier` Preferences page stores room-family
switches, partition seed, instance policy, metrics policy, local metrics,
geometric tolerances, and the corner threshold under
`/persistent/exts/orms/classifier`. Kit persists these settings in the user's
local configuration, not in USD.

x1 remains visibly enabled and locked because it is the mandatory fallback;
x2, x3, and x4 are independently switchable. An optional family that is
disabled or whose complete eight-tile atlas cannot be resolved is removed from
the usable partition set before classification. This rule is size-agnostic:
missing x2 repartitions through the remaining usable sizes in the same way as
missing x3 or x4. Missing x1 produces `MISSING_X1_ATLAS` and delegates to the
standard KRM-92 missing-room-atlas material and UI fallback instead of
constructing an invalid shared room.

Fallback and metrics diagnostics use the common ORMS formatter and expose the
same degraded state through the runtime inspection path and Preferences UI.
Records include owner, process, state, affected prim path where applicable,
and the relevant measured or configured values. The accepted manual settings
sequence covered independent x2/x3/x4 disablement, unavailable optional atlas
families, missing x1, valid Auto metrics, the local metrics override, and the
corresponding warning and UI states without mutating stage metadata.

### Runtime lifecycle

The R&D module is started manually after a stage is already open. It processes
that composed stage once, registers an `Usd.Notice.ObjectsChanged` listener,
and reclassifies only after relevant USD changes. It does not classify per
frame. Camera transforms, MDL `inputs:*`, and changes under `/__ORMSRuntime`
are explicitly excluded. Geometry, source grouping primvars, material
bindings, instancing, and transforms of eligible-window ancestors remain
classification triggers. Stage open and close events replace or remove the
active classifier. Stopping removes only the ORMS-owned anonymous sublayer and
Preferences page.

Repeated start, stop, reload, stage replacement, and Preferences changes leave
one active classifier, one owned stage-event subscription set, and one
Preferences subscription set. The accepted lifecycle log showed no duplicate
subscription-driven classification after the instance-policy round trip.

Info-only ancestor paths emitted alongside an excluded material-input change
do not independently trigger classification. A true resync of the same prim
path remains relevant, so topology, composition, and hierarchy changes are
still observed without letting the camera bridge submit a duplicate runtime
pass.

KRM-91 later owns extension packaging for both this classifier and the camera
bridge.

### Full-scene load trace

The R&D Kit application starts `runtime/stage_load_probe.py` through the local
`msp.orms.stage_load_probe` startup extension, before a stage opens. The manual
reload entry point can replace that observer before reloading the classifier,
material runtime, or camera bridge. Each observer begins with `PROBE_ARMED`;
coverage starts at that record and never claims knowledge of earlier work.

The probe records Kit's `OPENING`, `OPENED`, `ASSETS_LOADING`, `ASSETS_LOADED`,
`ASSETS_LOAD_ABORTED`, `MDL_PARAM_LOADED`, and Hydra geometry-streaming stage
events. On Kit updates it samples `UsdContext.get_stage_loading_status()` and
`get_stage_streaming_status()`. A changed five-percent bucket produces
`STAGE_LOADING_PROGRESS`; an unchanged pending status produces a five-second
heartbeat; and the observed transition from a non-empty/pending status to an
empty status produces `STAGE_LOADING_STATUS_EMPTY`. This is explicitly a
snapshot with `completion_claim=False`, because more async work can begin on a
later update. Each status record retains the raw loading message, loaded and
total file counts, percentage, streaming-busy flag, and active-batch state.

`ASSET_BATCH_LOADING_COMPLETE` means only that Kit completed the current async
asset batch. Its summary includes batch duration, maximum queue size, and the
loading message that remained unchanged for the longest interval. An empty
public status is never described as idle or complete. The batch event is not
renamed to renderer or material completion, because the native status bar's
renderer-idle boundary remains unavailable to Python.

An active asset batch is closed as `ASSET_BATCH_LOADING_SUPERSEDED` before a
new stage-open run or replacement `ASSETS_LOADING` event starts. Its elapsed
time is never carried into the next stage's batch. A terminal event without an
active matching batch is recorded as `ASSET_BATCH_LOADING_COMPLETE_UNTIMED` or
`ASSET_BATCH_LOADING_ABORTED_UNTIMED`, with its duration explicitly marked
unavailable. To capture an entire stage-open timeline, arm the probe before
opening or reopening the stage; starting it mid-load captures only the
remaining interval from `PROBE_ARMED` forward.

KRM-93 retains the fixtures' existing `mdlMaterialWarmup = 1` baseline and
does not disable warmup in the R&D Kit application. The probe is not used as
cold-start acceptance evidence. Comparing MDL compilation with UDIM work,
prewarm policy, persistent shader caches, and cold/warm RTX startup belongs to
KRM-91.

### Runtime phase trace

Each manually started classification pass emits correlated, formatted ORMS
console records with diagnostic code `ORMS-RUNTIME-TRACE`. The records currently
use warning severity because the R&D application's Console shows warnings and
errors only. This severity is a visibility workaround for profiling, not an
assertion that a successful phase is faulty.

One `run_id` follows the pass through these ordered states:

1. `RUNTIME_RUN_BEGIN`;
2. `STAGE_EXTRACTION_COMPLETE`;
3. `CLASSIFICATION_COMPLETE`;
4. `RUNTIME_PRIMVARS_AUTHORED`;
5. `RUNTIME_MATERIALS_AUTHORED`;
6. `RUNTIME_BINDINGS_AUTHORED`;
7. `MATERIAL_UPDATE_SUBMITTED`;
8. `MATERIAL_LOADING_COMPLETION_UNOBSERVABLE`;
9. `FIRST_FRAME_AFTER_MATERIAL_UPDATE` when Kit delivers that frame.

Every record contains `phase_ms` and `elapsed_ms`, plus phase-specific counts.
The trigger distinguishes a manual start, stage open, Preferences change, or
relevant USD change. A USD-triggered run also records the notice's separate
`resynced_paths` and `changed_info_paths`, plus the paths accepted by the ORMS
relevance filter. Each list is limited to 16 entries and retains its complete
count and a `paths_truncated` flag, preventing a large stage notice from
flooding the Console. `MATERIAL_UPDATE_SUBMITTED` is the boundary at which the
runtime material specs and bindings have been submitted to Hydra. A subsequent
`StageRenderingEventType.NEW_FRAME` produces
`FIRST_FRAME_AFTER_MATERIAL_UPDATE`; this proves only that Kit delivered a
frame after the update. It does **not** prove that MDL compilation, PNG decoding,
mip generation, texture upload, shader-cache work, or the native status-bar
operation has completed.

The Kit 110.1.2 status bar implements `Loading material...` inside the native
`omni.kit.window.status_bar` plugin and waits through
`omni::kit::renderer::IRenderer::waitIdle`. That completion state has no public
Python read/event API. The public status-bar message-bus events set third-party
text and progress; they do not expose the native bar's current state. Therefore
the R&D runtime emits `MATERIAL_LOADING_COMPLETION_UNOBSERVABLE` explicitly and
must not report a material-loading duration. If registration of the independent
first-frame observation fails, it emits `FIRST_FRAME_OBSERVATION_UNAVAILABLE`
with the exception.

The classifier retains an internal object-space pose cache for each aperture,
but the authored `ormsRoomPositionWorld`, `ormsRoomAxisU`, `ormsRoomAxisV`, and
`ormsPhysicalNormal` primvars are world-space values consumed directly by MDL.
A rigid translation or rotation of a classified building root refreshes those
uniform values from the object-space cache without rerunning geometric
classification or replacing the runtime layer. Scale, child transforms,
points, topology, source primvars, and material bindings remain structural
changes and do trigger classification.

## Evidence

The retained evidence covers:

- exact x1–x4 runs and the sequences `01 01 02 01 01`,
  `01 02 03 04 04`, and `01 01 02 03 04`;
- deterministic long-run partitioning and primitive-order shuffling;
- independent x2/x3/x4 disablement, unavailable optional atlas families, and
  deterministic repartitioning through the remaining usable sizes;
- unequal aperture widths inside one room, the complete bounded one-turn
  corner footprint matrix with one to four windows per facade leg, an x3 bay
  with side apertures at ±30°, an x4 bay with side apertures at ±45°, and a
  second x4 bay whose four non-parallel apertures turn by 8° between neighbours;
- 0.2-metre physical gaps between every neighbouring bay aperture;
- bay bounds fitted to their x3/x4 room side walls and a configurable 60°
  transition from shared-bay to one fixed rectangular-corner box;
- geometry-derived shared slice throats for the x3/30°, x4/45°, and x4/8°
  bay fixtures, with zero preserved for flat, corner, and Houdini fixtures;
- one shared basis and box for the complete corner matrix, including separate
  x1 and x4 family bindings without a basis change on a `4 x 1` room;
- one distinct existing debug UDIM for each isolated Omniverse case, selected
  through the normal eight-variant `roomID` contract;
- exact 3D mapping continuity at connected facet edges, including non-zero
  depth components for angled apertures;
- disconnected equal-`roomID` components, branched graphs, missing x1, and
  degenerate frame fallback;
- reversible Session Layer ownership, local stage metrics, four shared family
  materials specialised from one source material, camera and rigid
  building-pose filtering, object-space runtime frames, live artist-input
  composition, and the five-lookup MDL budget;
- isolated Omniverse-authored geometry, layered Houdini-authored geometry, and
  two referenced instanceable buildings under both instance policies.

The Houdini scene remains `hip/room map test 005.hiplc`. Its exported component
is `assets/_external/usd/test_bld/test_bld.usd`. The KRM-93 capture layer
preserves the exported geometry, `roomID`, `roomP`, `tangentu`, `tangentv`,
`roomUV`, component hierarchy, payloads, and source MaterialX materials. It
overrides only the windows' composed material binding with the Room Map MDL
source material required by the runtime classifier.

## Reproduction

Launch the default Omniverse-authored fixture with
`tests/shared_room_runtime/launch_shared_rooms_omniverse.bat`, the
Houdini-exported fixture with
`tests/shared_room_runtime/launch_shared_rooms_houdini_omniverse.bat`, or the
instance fixture with
`tests/shared_room_runtime/launch_shared_rooms_instances_omniverse.bat`. Use
`tests/shared_room_runtime/launch_shared_rooms_houdini_instances_omniverse.bat`
for two instanceable references to the Houdini-exported component. After the selected stage
opens, run this from Script Editor:

```python
from pathlib import Path
import runpy

import omni.usd

root_layer = omni.usd.get_context().get_stage().GetRootLayer()
stage_path = Path(root_layer.realPath).resolve()
repository_root = next(
    parent
    for parent in stage_path.parents
    if (
        parent
        / "exts"
        / "msp.orms.runtime"
        / "msp"
        / "orms"
        / "runtime"
        / "reload_room_map_runtime.py"
    ).is_file()
)
extension_root = repository_root / "exts" / "msp.orms.runtime"
orms_runtime_loader = runpy.run_path(
    str(
        extension_root
        / "msp"
        / "orms"
        / "runtime"
        / "reload_room_map_runtime.py"
    )
)
orms_runtime_loader["reload_and_start"](extension_root)
```

The Preferences page is available as `ORMS Classifier`. Setting changes are
persistent and trigger reclassification of the current stage. When the check
is complete, run:

```python
orms_runtime_loader["stop_runtime"]()
```

For the instance fixture, validate `Preserve` first, then switch to
`Session de-instance` and back. For all visual fixtures, inspect the result in
RTX Real-Time and RTX Interactive (Path Tracing).

The Omniverse fixture has a lower row containing the flat x1–x3 cases and the
90° `Corner2x2`, which must select x2 rather than flattening four apertures
into x4. The next row contains `RoomX3Bay30` with one central aperture
and two ±30° side apertures, plus `RoomX4Bay45` with two central apertures and
two ±45° side apertures. `RoomX4Arc8` is centred in the row above those bays;
it contains no parallel pair and uses orientations −12°, −4°, +4°, and +12°,
producing an exact 8° turn between neighbours. Two further rows contain only
the additional corner scenarios `Corner1x1`, `Corner1x2`, `Corner2x1`,
`Corner1x3`, `Corner3x1`, `Corner1x4`, and `Corner4x1`. `Corner4x1` and
`Corner1x4` each retain five physical apertures in one logical 4-wide, 1-deep
box. The four-window facade binds x4 on its front boundary; the one-window
facade binds x1 on the connected side boundary without changing the room
basis. All three bays use 0.2-metre gaps between physical apertures. Each bay
must reveal one continuous rigid
room with no reset, mirror, stretch, or refraction-like bend; its side walls
must meet the outer aperture bounds. Every 90° corner must reveal one common
rectangular room with one fixed orientation: no view-dependent 90° basis
change occurs, no duplicate side wall appears, and the two facade widths are
never unfolded into one long back wall.

The fixture source material exposes all eight debug variants. All fourteen
cases select distinct retained files within their selected atlas family
through deterministic `roomID` values. This gives every case a unique
family/UDIM pair without introducing per-case shader definitions or bypassing
runtime family binding.

## Validation record

On 28 August 2026, the corrected corner-portal contract passed 33 pure
classifier tests and 19 focused OpenUSD adapter and fixture tests. They cover
the full 1…4 by 1…4 corner matrix, one shared box basis, facade-specific atlas
subsets, shared logical identity, source-layer immutability,
deterministic grouping, and reversible runtime ownership. The broader KRM-93
validation had previously passed 59 focused tests and the complete repository
suite had passed 103 tests before this final corner-portal correction.

These are the latest recorded automated results, not a claim that the final
repository quality gate has already run after every subsequent corner,
Preserve, Path Tracing, and bay-shell correction. That complete suite is
intentionally reserved for the pre-commit gate and must replace this paragraph
with its exact command, date, and result when it is run.

On 31 August 2026, the isolated Omniverse-authored fixture and retained
Houdini-exported fixture were accepted in RTX Real-Time and RTX Interactive
(Path Tracing). The accepted views cover flat x1 through x4 groups, long-run
partitioning, 30-degree, 45-degree, and 8-degree faceted bays, bounded
right-angle corners, different aperture dimensions, deterministic debug-atlas
variation, and stable perspective while the camera moves. The final all-angled
bay correction extends the Top, Floor, Left, and Right room faces across the
complete main-room and bay depth, removing the exposed gaps at the bay joins.

The Houdini-derived instanceable fixture was also accepted under Preserve and
Session de-instance, including a return to Preserve, runtime stop and reload,
and stage replacement. Preserve retains source instancing and uses the x1
fallback where descendant overrides are unavailable; Session de-instance
restores coherent shared rooms through reversible ORMS-owned Session Layer
opinions. No source Houdini or USD layer is modified.

The retained final renderer evidence is
`docs/img/krm93/krm93_01.png` for RTX Real-Time and
`docs/img/krm93/krm93_02.png` for RTX Interactive (Path Tracing). These compact
building views contain the required flat, bay, corner, differing-aperture, and
Houdini-export evidence, so separate single-case captures are not retained.
The isolated Omniverse-authored fixture was accepted interactively in both
renderer modes, but no separate repository capture of that fixture is retained;
its reproducible scene and automated fixture contract remain the durable
evidence for that fixture family.

## Boundary

KRM-93 supports flat aperture faces in deterministic linear runs, rigid bay
turns below the configured corner threshold, and exactly one bounded corner
with one to four apertures per facade leg. Curved individual window surfaces
belong to KRM-97. Multiple sharp corners, facade legs wider than x4, general
branched or procedural layouts, and any post-KRM-93 expansion of long-run
policy remain subject to the pre-start scope review in KRM-96.

Production glass, Building 150 integration, building-scale profiling,
permanent source-asset mutation, and extension packaging are outside this
record. The current Preferences page and lifecycle are manual R&D code, not a
shipped Kit extension.

### Dependencies and follow-up ownership

- KRM-90 supplies deterministic `roomID`-to-UDIM atlas identity.
- KRM-92 owns the standard missing-x1 material, warning, and UI fallback.
- KRM-94 supplies physical aperture scale and offset controls retained by the
  shared-room mapping.
- KRM-91 owns production Kit-extension packaging, persistent startup
  integration, and cold-versus-warm material-loading diagnostics.
- KRM-96 owns any accepted expansion to branched or general procedural layouts;
  KRM-97 owns curved or deformed individual window surfaces.
