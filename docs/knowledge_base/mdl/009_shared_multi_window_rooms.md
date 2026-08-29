# Shared Multi-Window Room Volume Contract

## Record

| Field | Value |
| --- | --- |
| Jira | KRM-93 — Shared Multi-Window Room Volume and Aspect Controls |
| Implementation | `tools/omniverse/room_run_classifier.py`, `tools/omniverse/shared_room_classifier.py`, `tools/omniverse/shared_room_preferences.py`, `src/mdl/room_map.mdl` |
| Automated evidence | `tests/krm_93/test_room_run_classifier.py`, `tests/krm_93/test_shared_room_classifier_usd.py`, `tests/krm_93/test_shared_room_classifier_fixtures.py`, `tests/krm_93/test_stage_load_probe.py`, `tests/krm_93/test_fixture_launcher_bundle.py` |
| Validation scenes | `tests/krm_93/test_room_map_shared_rooms_omniverse.usda`, `tests/krm_93/test_room_map_shared_rooms_houdini.usda`, `tests/krm_93/test_room_map_shared_rooms_instances.usda` |
| Evidence state | Automated contract complete; RTX renderer validation pending |
| Last reviewed | 29 August 2026 |

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

Eligible window meshes retain the existing ORMS data and an effective binding
to `src/mdl/room_map.mdl`:

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

| Derived primvar | Type | Meaning |
| --- | --- | --- |
| `ormsRoomSize` | `int[]` | Width of the one shared x1–x4 room box. |
| `ormsRoomDepthSize` | `int[]` | Depth multiplier of that same box; x1 for ordinary runs. |
| `ormsRoomGroupId` | `int[]` | Deterministic runtime group identity. |
| `ormsMappingValid` | `int[]` | Whether the shared affine map is safe to consume. |
| `ormsRoomAxisU`, `ormsRoomAxisV` | `float3[]` | One shared orthonormal basis for every aperture in the logical room. |
| `ormsRoomScale` | `float3[]` | World-to-room scale that fits the complete classified box. |
| `ormsRoomMapOrigin` | `float3[]` | Per-aperture corner in the centred pre-scale room mapping frame, in metres. |
| `ormsRoomMapAxisU`, `ormsRoomMapAxisV` | `float3[]` | Full 3D affine embedding of source `roomUV` tangents into that shared frame, in metres. |
| `ormsSliceStartDepth` | `float[]` | Shared normalised depth at which the rectangular rear volume begins; zero for flat and corner rooms. |
| `ormsRoomParameters` | uniform `float3[]` | Packed `(10 * width + depth, slice start depth, portal mode)`. Portal mode is `0` for fallback, `1` for a front aperture, and signed `2` for a depth-aligned side aperture. |
| `ormsRoomMapPosition` | face-varying `float3[]` | The affine `roomUV` embedding evaluated at every aperture vertex. Linear interpolation preserves the exact shared mapping without rebuilding origin and two axes in MDL. |

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
Each family uses tiles `1001…1008` from its own directory under
`assets/_external/tex/`. Face subsets bind the selected family without
changing the source material binding. A rectangular corner may bind two such
subsets on one mesh, keyed by the same group identity but different xA/xB
families. Atlas family is deliberately separate from the common box width and
orientation. The shared `roomID` selects the same variant number in both
families.

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

For a bay room, the classifier derives `ormsSliceStartDepth` from the rearmost
aperture corner in the shared room frame. This separates the projecting bay
from the rectangular rear volume without a hand-authored bay parameter. The
authored `room_depth` remains the complete depth of that rear volume; the bay
extension is added in front of it. The back wall therefore lies at
`ormsSliceStartDepth + room_depth`, while the four artist percentages are
remapped over the unchanged `room_depth` interval beginning at the throat.
Angled apertures cannot cut the front slice, and a deep bay cannot compress
the four slices into its leftover depth. Flat and bounded corner rooms author
zero and keep their existing full-depth distribution. This adds no texture
lookup and remains one identical derived value for every aperture in a group.

The shared room shell extends continuously across the complete combined depth.
Its left wall, right wall, floor, and ceiling begin at the physical window and
continue to the back wall, so the projecting bay cannot expose an unfilled
strip of the room envelope. All four surfaces use one depth coordinate over
`ormsSliceStartDepth + room_depth`. The throat remains a separate visibility
boundary only for the four depth slices: the shared camera ray must enter the
rear room before a slice may contribute. This keeps slice cards out of the
narrow bay while preserving a closed shell and one perspective across central
and angled apertures. Flat and corner paths remain unchanged.

### Stage metrics, instances, and local settings

`Auto from stage` reads authored `upAxis` and `metersPerUnit`. Missing or
invalid metadata emits a diagnostic and uses a local Y-up, 1-metre fallback
without authoring metadata. `Local override` can interpret the stage as Y-up
or Z-up with an explicit metres-per-unit value, again without changing the
source stage.

The default instance policy is `Preserve`. A preserved instance that contains
eligible Room Map meshes retains its source x1 behaviour and emits an
`INSTANCE_PRESERVED_X1_FALLBACK` diagnostic. `Session de-instance` authors
`instanceable = false` only in the owned runtime layer and classifies each
reference independently; removing the layer restores instancing.

The manually registered `ORMS Classifier` Preferences page stores room-family
switches, partition seed, instance policy, metrics policy, local metrics,
geometric tolerances, and the corner threshold under
`/persistent/exts/orms/classifier`. Kit persists these settings in the user's
local configuration, not in USD.

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

Info-only ancestor paths emitted alongside an excluded material-input change
do not independently trigger classification. A true resync of the same prim
path remains relevant, so topology, composition, and hierarchy changes are
still observed without letting the camera bridge submit a duplicate runtime
pass.

KRM-91 later owns extension packaging for both this classifier and the camera
bridge.

### Full-scene load trace

The R&D Kit application starts `stage_load_probe.py` through the local
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
console records with diagnostic code `ORMS-KRM93-TRACE`. The records currently
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

The Kit 108.0 status bar implements `Loading material...` inside the native
`omni.kit.window.status_bar` plugin and waits through
`omni::kit::renderer::IRenderer::waitIdle`. That completion state has no public
Python read/event API. The public status-bar message-bus events set third-party
text and progress; they do not expose the native bar's current state. Therefore
the R&D runtime emits `MATERIAL_LOADING_COMPLETION_UNOBSERVABLE` explicitly and
must not report a material-loading duration. If registration of the independent
first-frame observation fails, it emits `FIRST_FRAME_OBSERVATION_UNAVAILABLE`
with the exception.

## Evidence

The retained evidence covers:

- exact x1–x4 runs and the sequences `01 01 02 01 01`,
  `01 02 03 04 04`, and `01 01 02 03 04`;
- deterministic long-run partitioning and primitive-order shuffling;
- disabled or missing x3/x4 atlas families;
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
  materials specialised from one source material, camera-change filtering,
  live artist-input composition, and the five-lookup MDL budget;
- isolated Omniverse-authored geometry, layered Houdini-authored geometry, and
  two referenced instanceable buildings under both instance policies.

The Houdini scene remains `hip/room map test 005.hiplc`. Its exported component
is `assets/_external/usd/test_grid_wins_diff/test_grid_wins_diff.usd`. The
KRM-93 capture layer changes only the test `roomID` sequence; geometry,
`roomP`, `tangentu`, `tangentv`, `roomUV`, component hierarchy, payloads, and
source materials still come from the retained Houdini export.

## Reproduction

Launch the default Omniverse-authored fixture with
`tests/krm_93/launch_krm93_omniverse.bat`, or open another validation scene,
then run this from Script Editor:

```python
from pathlib import Path
import runpy

import omni.usd

root_layer = omni.usd.get_context().get_stage().GetRootLayer()
stage_path = Path(root_layer.realPath).resolve()
repository_root = next(
    parent
    for parent in stage_path.parents
    if (parent / "tools" / "omniverse" / "reload_room_map_runtime.py").is_file()
)
orms_runtime_loader = runpy.run_path(
    str(repository_root / "tools" / "omniverse" / "reload_room_map_runtime.py")
)
orms_runtime_loader["reload_and_start"](repository_root)
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
basis. All
three bays use 0.2-metre gaps between physical apertures. Each bay must reveal one continuous rigid
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

RTX renderer compilation and visual continuity have not yet been recorded.
This record must remain in the pending state until the isolated, Houdini, and
instance scenes are observed in both required renderer modes.

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
