# ORMS Runtime Recovery and Native-Instance Integration Plan

## Record

| Field | Value |
| --- | --- |
| Jira | Follow-up to KRM-91, KRM-92, KRM-93, and KRM-98; recovery issue not yet assigned |
| Known-good pre-recovery baseline | Commit `f0f625f`, `Release ORMS 1.0.1 with demo and licensing` |
| Current recovery implementation | Commit `40dc4dd`, `Restore native-instance ORMS parity`, pushed to `origin/main` |
| Accepted native-instance evidence | `009_shared_multi_window_rooms.md` |
| Implementation target | `exts/msp.orms.runtime/` |
| Validation assets | `assets/_demo/Moskovskiy_av_150/usd/Moskovskiy_av_150.usd`; `assets/_external/usd/Moskovskiy_av_150/usd/Moskovskiy_av_150.usd`; `assets/_external/usd/room_map_city.usd` |
| State | In progress — installed 1.0.16 has initial native S1-S4 visual acceptance and clean runtime evidence, and the working recovery implementation is committed and pushed; the remaining Phase-5 matrix is still open |
| Last reviewed | 7 September 2026 |

## Purpose

This record defines a two-milestone recovery plan for ORMS.

The first milestone restores and publishes one reliable runtime that supports:

- full classified x1–x4 ORMS on ordinary authorable USD meshes; and
- the already proven native-instance `Preserve` path from record 009, using
  `x1 room_map_single` without de-instancing.

That recovery milestone must make the complete applicable material controls,
camera bridge, material ownership, Stop, Restart, and Restore behaviour work
for both target kinds. It must be built, published to the local Kit Registry,
and accepted manually before any new native x2–x4 experiment begins.

The second milestone investigates full x2–x4 room grouping while native
instancing remains enabled. It is deliberately isolated from the recovered
runtime. Failure of that research must not damage or delay the accepted
ordinary plus native-x1 build.

### Why this plan exists

The last committed baseline, `f0f625f`, retained the working ordinary-USD
runtime and the implementation lineage of the accepted record-009 instance
path. Later uncommitted attempts to expand city-instance support changed
shared discovery, assignment, material, and lifecycle code before preserving
that baseline.

The resulting regressions included:

- ordinary non-instance window meshes no longer being recognised;
- selector masks replacing compatibility discovery rather than routing
  compatible meshes;
- native-instance material replacement escaping the selected windows and
  recolouring façades or whole buildings;
- emission being repaired in one path while the parallax graph stopped
  working;
- parallax being captured at the Start or Restart camera position and then
  failing to update;
- Stop and Restore failing to reveal the complete original material state;
- sidecar, adapter, reference-substitution, de-instance, and stage-reopen
  experiments violating the source-safe runtime contract; and
- accepted records 009, 011, and 012 being edited to describe an unaccepted
  experimental workflow.

Those historical records have been restored. This record now treats the
working `Preserve/x1` implementation in 009 as accepted starting evidence,
not as a hypothetical feature.

The first recovery candidate, ORMS 1.0.9, exposed a contradiction that the
OpenUSD-only tests did not catch. Its instance-root collection resolved to the
window in `ComputeBoundMaterial()`, but Kit/RTX visibly applied the result to
non-window parts of the city prototypes. At the same time the camera bridge
targeted an unattached empty classifier layer and raised `SetEditTarget` on
every frame, freezing native parallax. Version 1.0.9 is rejected evidence and
must not be used as the native recovery baseline.

Version 1.0.10 is also rejected. It replaced the collection binding with a
second runtime `inherits` arc whose class pointed at a global ORMS material.
OpenUSD material-resolution tests again reported window-only bindings, but the
real nested `PointInstancer -> native instance` city rendered corrupted
non-window materials, unstable source-prototype materials, and broken
parallax on the original prototype block. The defect proves that adding a
runtime composition arc to each building root and targeting an external
material are both outside the accepted recovery shape.

Inspection of the retained record-009 fixture established the actual working
shape: its window already has a direct `room_map_single` binding inside the
composed prototype, and its facade has a separate direct source binding. The
fixture does not create an instance-root collection at runtime. Recovery must
therefore reproduce that direct descendant-binding shape in temporary
composition, not retry the rejected collection mechanism.

The regressions are runtime integration failures. They do not establish a need
to re-export the city or Building 136 from Houdini. Re-export is required only
if an individual source asset independently lacks the topology or primvars
required by the accepted ORMS mesh contract.

> **Evidence status:** record 009 is accepted evidence for its exact fixture
> and boundary. Recovery on the current ordinary assets and
> `room_map_city.usd` remains pending. Native x2–x4 with `Preserve` remains an
> unverified research hypothesis.

## Accepted starting point

### Ordinary USD

The accepted ordinary-Mesh path provides:

- compatibility discovery for legacy `Windows_Glass` identity, compatible
  semantic child meshes below a `windows` container, and explicit opt-in;
- x1–x4 classification and bounded family GeomSubsets on the selected window
  Mesh only;
- temporary material bindings and derived primvars in ORMS-owned anonymous
  Session Layer sublayers;
- full room, aperture, slice, glass, emission, diagnostic, and atlas controls;
- camera-following parallax; and
- source restoration by removing ORMS-owned opinions rather than reconstructing
  source materials.

### Native instances

Record 009 already accepted the following `Preserve` path:

- native instances remain instanceable;
- eligible instance-proxy windows receive the native
  `room_map_single` x1 material, including four layered-depth slices;
- the accepted fixture supplies a direct material binding on the window inside
  the composed prototype;
- non-window descendants retain their Houdini-exported material bindings;
- `roomID` retains deterministic x1 atlas variation;
- the inherited `ormsCameraPositionWorld` value drives camera-following
  parallax; and
- ORMS-owned Session Layer state can be removed without changing source
  Houdini/USD layers.

The accepted instanceable fixtures passed `Preserve`, `Session de-instance`,
return to `Preserve`, Stop, reload, and stage replacement. This recovery plan
uses only `Preserve/x1` as the required production native-instance mode.
`Session de-instance` is historical evidence, not an allowed fallback for the
city workflow.

### Exact accepted boundary

The first recovery build does not promise shared x2–x4 rooms inside preserved
native instances:

- ordinary meshes retain full x1–x4 classification;
- preserved native instances deliberately use x1
  `room_map_single` for every eligible window;
- x2–x4 family enablement and resources do not imply x2–x4 grouping for the
  native `Preserve` route; and
- full native x2–x4 is investigated only after the recovery build is accepted.

This distinction must be visible in diagnostics and release notes.

## Evidence

### Ordinary assets to recover

The external Building 150 asset contains:

    /Moskovskiy_av_150/geo/render/Windows_Glass

An exact `Windows_Glass` or `*/Windows_Glass` mask can select it. A misspelled
mask such as `*/Window_Glass` matches nothing and must produce a zero-match
diagnostic without changing unrelated materials.

The demo Building 150 asset uses compatible semantic child meshes below its
`windows` container, including `other_rooms`, `halls`, `living_rooms`,
`cabinets`, and `library_windows`. Editable selectors must not erase this
accepted compatibility route.

### Native-instance evidence to restore

Record 009 retains:

- Omniverse-authored and Houdini-authored instanceable fixtures;
- two referenced instanceable buildings;
- exact `Preserve` and `Session de-instance` reproduction steps;
- source-layer immutability checks;
- an x1 room-grouping material contract with four layered-depth slices;
- stable per-room x1 variation;
- camera-bridge behaviour; and
- renderer acceptance in RTX Real-Time and RTX Interactive Path Tracing.

The current city regressions do not invalidate that evidence. They show that
later changes failed to preserve its target filtering, material state, camera
initialisation, or lifecycle ownership.

### Known portability boundary

The accepted instance fixture predeclared the inherited camera input before
Hydra first synchronised the prototype-bound material. A camera primvar first
introduced after an already-rendered prototype was not accepted as reliable
in record 009.

The recovered backend must therefore prove both:

1. cold stage startup, where ORMS-owned inherited inputs exist before the
   native x1 material is published; and
2. Start on an already-open, already-rendered `room_map_city.usd` stage.

The second case may use a supported material or renderer resynchronisation, but
must not create a sidecar, reopen the USD stage, change source layers, or
de-instance geometry. Failure of this case blocks the recovery release.

### Provenance rule

The current worktree must be reconstructed by ownership rather than by either
retaining or discarding the entire uncommitted diff.

Every post-`f0f625f` change is classified as:

1. accepted baseline behaviour to restore;
2. a separately verified material or UI improvement to retain;
3. a broken instance, selector, material, or lifecycle experiment to remove;
4. a useful test that must be rewritten against the recovered contract; or
5. an unverified future x2–x4 experiment to keep outside the recovery backend.

Records 009 through 012 remain historical accepted evidence. New findings are
recorded in 014 until they pass their stated renderer boundary.

## Implementation plan

### Non-negotiable recovery contract

The first published recovery build must satisfy all of the following:

1. The user opens and continues working in the original USD stage.
2. ORMS does not create an adapter or sidecar stage, replace references, close
   or reopen the stage, or trigger a save prompt.
3. Root, reference, payload, and other source-owned layers remain unchanged.
4. Runtime USD opinions exist only in explicitly ORMS-owned anonymous Session
   Layer sublayers.
5. Native instances remain native instances.
6. Only compatible windows selected by the assignment policy receive an ORMS
   material.
7. Façades, roofs, doors, building roots, material scopes, and unrelated
   GeomSubsets retain their source materials.
8. Ordinary meshes receive the restored full x1–x4 path.
9. Native instance proxies receive the restored `Preserve/x1`
   `room_map_single` path from record 009.
10. All applicable material settings work in both paths.
11. Camera movement updates parallax continuously.
12. Stop, Restart, Restore, stage replacement, and extension shutdown are
    source-safe and idempotent.
13. Any failure is fail-open: source appearance remains visible.

### One recovered runtime, two accepted target routes

The recovery does not introduce a new renderer backend. It restores one
runtime service with shared discovery, selectors, settings, diagnostics,
material state, camera ownership, and lifecycle orchestration.

| Target | Recovery route | Room-family result | Temporary binding |
| --- | --- | --- | --- |
| Ordinary authorable Mesh | Existing classified Session Layer route | Full x1–x4 | Exact window Mesh and its ORMS-owned GeomSubsets |
| Window below a preserved native instance | Record-009 Preserve shape reproduced through the source asset's existing Houdini class | x1 `room_map_single` | Class-local material and direct descendant binding at the exact eligible relative window path |

The classifier chooses the route from the composed prim kind. It must never
fall through from a failed instance route to an ancestor-wide binding.

### Compatibility and selector semantics

Compatibility discovery and artist selection are independent:

1. Compatibility discovers legacy `Windows_Glass` identity, semantic meshes
   below a `windows` container, valid topology, and explicit opt-in.
2. Interior Set masks route or narrow compatible candidates.
3. Specific Sets are evaluated in stable displayed order.
4. The editable Default mask starts as `Windows_Glass`, as required by the
   artist workflow, but does not erase compatible semantic child meshes.
5. Default receives compatible candidates not claimed by a specific Set.
6. Explicit exclusion wins.
7. Matching is deterministic; a near-match diagnostic never silently changes
   the selector.

The automatic-assignment panel reports composed path, compatibility reason,
selector result, Interior Set, target route, and final binding scope.

### Ordinary route recovery

The ordinary route is restored first against `f0f625f`:

- recover exact Mesh and GeomSubset ownership;
- recover x1–x4 classification and existing family fallback rules;
- retain source material bindings below the removable runtime layer;
- remove selector changes that bypass legacy compatibility;
- remove instance-specific code from ordinary assignment;
- preserve the accepted object-space mapping and stage-metric behaviour; and
- prove that a direct Building 150 stage behaves identically before proceeding
  to city integration.

### Native Preserve/x1 route recovery

The native route is restored from the accepted 009 contract:

- detect eligible window proxies read-only;
- derive exact relative window paths below each authorable instance root;
- require one unambiguous source class already inherited by the Houdini asset;
- author an ORMS-owned temporary overlay at that existing class path, without
  changing the instance root's inherit list;
- create `room_map_single` below that class so its material target resolves in
  the instance-local namespace rather than to a global external material;
- place direct bindings only at the eligible relative window paths inside the
  existing class overlay;
- reject empty, invalid, escaping, or ancestor-broadened relative paths before
  publication;
- preserve `roomID`-based deterministic x1 variation;
- publish inherited camera and material-control inputs before the binding;
- force only a supported renderer/material resynchronisation when starting
  after prototype creation;
- never author directly through an instance proxy;
- never put a material binding on the building root;
- never de-instance the building; and
- remove the complete class overlay, material, primvar, and subscription state
  on cleanup.

The rejected instance-root collection and added-inherit paths are not
fallbacks. If an asset has no single usable existing source class, native
activation fails open and the source appearance remains visible.

Building 136 is a required production check, not a new source-preparation
step. Its corrected `Windows_Glass` geometry must pass the same contract as
the other city prototypes.

### Unified material settings

One typed public MaterialState owns all material controls. It feeds both the
classified `room_map` materials and the native `room_map_single` material.

The parity check includes:

- room depth and room scaling used by x1;
- aperture scale and offset;
- depth-slice scale and visibility controls;
- glass roughness, reflectivity, tint, and transmission;
- emission enablement, per-slice enablement, strength, threshold, and
  softness;
- diagnostic fallback colour and diagnostic modes; and
- x1 atlas source, variant count, and deterministic `roomID` selection.

Primary and fallback atlas modes consume the same MaterialState. Emission
cannot replace or bypass the parallax graph.

Controls that only select or scale x2–x4 families are not silently applied to
the native x1 route. The UI and diagnostics explicitly report that native
`Preserve` is x1-only in the recovery build.

Both the classified shader and the native x1 shader use a bounded five-lookup
budget: four S1-S4 depth slices plus the visible room face. The native route
remains x1-only because room grouping and depth layering are independent
contracts. Full native x2-x4 grouping remains Phase 6 work.

### Camera bridge contract

The active viewport camera remains the supported camera source.

The bridge must:

- publish the initial world-space camera position before either route becomes
  visible;
- update it continuously after Start and Restart;
- preserve the accepted ordinary-Mesh coordinate transform;
- supply preserved instances through the inherited input required by
  `room_map_single`;
- avoid reclassification on camera movement;
- reject callbacks from a stale stage or runtime generation; and
- remove its subscription while retaining the last runtime values on Stop;
  remove both on Restore.

Validation moves the camera after Start and after Restart. A correct initial
frame is not sufficient evidence.

### Material and source ownership

Before Start, the runtime snapshots source identities for diagnostics but does
not copy source material values for later reconstruction.

Restoration works by removing stronger ORMS-owned opinions:

- ordinary Mesh and GeomSubset bindings disappear with the ordinary runtime
  sublayer;
- native existing-class overlays and their descendant bindings disappear with
  the Preserve runtime sublayer; the source inherit arcs never change;
- inherited runtime primvars disappear with their ORMS-owned sublayer;
- synthetic runtime materials and callbacks are destroyed; and
- original composed materials become visible without being rewritten.

No operation may bind ORMS to a building merely because an instance proxy is
not authorable.

### Transactional lifecycle

Start:

1. Build a complete assignment snapshot without publishing.
2. Validate selectors, compatibility, topology, source bindings, resources,
   and exact relative instance-window paths.
3. Build all candidate runtime layers and materials off the active layer stack.
4. Publish only after both required target routes are ready.
5. On failure, remove the candidate and leave the source view visible.

Restart:

1. Keep the current valid runtime active while a replacement is built.
2. Swap only after complete validation.
3. Retain the previous valid runtime if candidate construction fails.
4. Return to source state if publication fails; never retain a mixed
   ordinary/native state.

Stop:

- retain the currently rendered ORMS result;
- suspend camera-driven parallax updates and other live runtime subscriptions;
- retain artist configuration; and
- leave ORMS assignments visible until Start, Restart, or Restore Original
  Asset explicitly changes them.

Restore Original Asset:

- stop live updates and remove both visual assignment routes;
- destroy cached assignments, generated subsets, existing-class overlays,
  materials,
  ORMS-owned anonymous layers, callbacks, and stage-generation state;
- retain only intentionally persistent artist configuration; and
- never reopen or save the stage.

Stage close, stage replacement, payload changes, and extension shutdown use
the same idempotent cleanup owner.

### Unit-test coverage contract

Every new or changed functional unit must receive focused unit coverage in the
same implementation phase. A functional unit includes a pure function,
decision rule, state transition, cache or ownership operation, and any adapter
boundary whose behaviour can be isolated from Kit or RTX.

The minimum case budget for each unit is:

- at least one happy-path case;
- three to five distinct boundary or negative cases; and
- up to eight boundary or negative cases where the unit has high fan-out,
  destructive failure potential, ambiguous USD composition, or asynchronous
  lifecycle behaviour.

The number is a minimum risk budget, not permission to duplicate equivalent
assertions. Parameterised cases should be used where they preserve the reason
and expected result of every boundary.

The high-risk units expected to require up to eight cases include:

- compatibility and selector resolution: exact names, absolute paths,
  wildcards, zero matches, overlapping Sets, Default fallback, explicit
  opt-in, and exclusion precedence;
- native existing-class overlays: exact window-only relative paths, mixed
  window/non-window candidates, empty selections, duplicate signatures,
  ancestor broadening, invalid proxies, missing primvars, and stale stage
  identity;
- lifecycle transactions: construction failure, publication failure, failed
  Restart, repeated Stop, repeated Restore, stage replacement, payload unload,
  and extension shutdown;
- camera delivery: cold start, already-rendered stage, movement after Start,
  movement after Restart, stale callbacks, stage switch, transformed
  instances, and subscription cleanup;
- material parity: ordinary versus native x1, primary versus fallback,
  boundary values, reset values, emission with parallax, per-slice emission,
  glass controls, and invalid resource fallback; and
- source ownership: correct anonymous-layer ownership, foreign Session Layer
  preservation, source binding restoration, failed candidate cleanup,
  instanceability preservation, repeated runs, and absence of disk output.

Every reproduced defect receives a regression test that fails for the defect
before its implementation fix is accepted. A broader fixture or renderer test
does not replace that unit test when the faulty decision can be isolated.

Coverage is layered:

1. pure unit tests validate decisions and state transitions without launching
   Kit;
2. focused OpenUSD fixtures validate composition, direct bindings, inherits,
   primvars, subsets, and layer ownership;
3. focused Kit runtime tests validate subscriptions, renderer
   resynchronisation, stage events, and lifecycle integration; and
4. manual RTX checks validate the final visible result.

Passing a happy path, a fixture, or a manual viewport check alone is
insufficient. A phase is incomplete until its changed units meet this case
budget. Focused tests run during implementation; the repository-wide quality
gate remains reserved for an explicitly requested commit.

### Delivery sequence

#### Phase transition record

After every phase is completed, rejected, or blocked, update this record's
iteration ledger and current-status table before starting the next phase.
State what was completed or rejected, the latest confirmed finding, the next
unfinished action, and any experiments that must not be repeated.

#### Phase 0 — recover the implementation baseline

- Keep records 009, 011, and 012 at their accepted committed content.
- Inventory the implementation diff from `f0f625f` by ownership.
- Remove sidecar creation, adapter generation, stage reopening, reference
  substitution, native-instance preparation, ancestor-wide fallback binding,
  and automatic de-instancing.
- Retain later changes only when a narrow test proves they do not violate the
  recovery contract.
- Do not bump or publish a version.

#### Phase 1 — restore ordinary USD

- Restore compatibility discovery independently from selector routing.
- Restore exact window Mesh and GeomSubset binding.
- Restore full x1–x4 classification.
- Restore material, camera, lifecycle, and source-layer ownership.
- Run the narrow ordinary assignment, classification, material-control,
  camera, and lifecycle tests.
- Validate both direct Building 150 assets in RTX Real-Time and RTX
  Interactive Path Tracing.

Phase 1 must be green before native code is enabled in the same candidate.

#### Phase 2 — restore native Preserve/x1

- Reproduce the record-009 direct window-binding shape with a removable
  overlay on the asset's existing Houdini class and a class-local
  `room_map_single` material.
- Restore inherited camera and material-control publication order.
- Cover cold stage startup and Start after the city has already rendered.
- Validate Building 136 and the remaining recognised city prototypes.
- Confirm native instanceability and source material identity before and after
  every lifecycle operation.

No x2–x4 native grouping experiment is permitted in this phase.

#### Phase 3 — prove material and lifecycle parity

- Drive both target routes from the same public MaterialState.
- Exercise every applicable material control in the primary and fallback
  modes.
- Move the camera after Start and Restart.
- Repeat Start, Restart, Stop, and Restore.
- Switch stages and disable/re-enable the extension.
- Record that façades and all non-window materials remain unchanged.
- Record that source Houdini/USD layers remain unchanged.
- Check that callbacks, layers, materials, and class overlays do not
  accumulate, and that source inherit arcs never change.

#### Phase 4 — build the recovery candidate

- Run only the focused recovery tests during implementation.
- When Phases 1–3 pass, bump one candidate version.
- Build one package and inspect its manifest and contents.
- Publish that package to the local Kit Registry.
- Install it through Extension Manager rather than running from the source
  tree.

No repository-wide hook, linter, or security suite is run merely for this
iteration. The full quality gate remains reserved for an explicitly requested
commit.

#### Phase 5 — manual Registry acceptance and baseline freeze

Max validates the installed Registry package on:

1. direct demo Building 150;
2. direct external Building 150;
3. `room_map_city.usd`, including Building 136;
4. day and night lighting sufficient to inspect glass and emission;
5. camera movement after Start and Restart; and
6. Stop and Restore without reopening the stage.

The final recovery-candidate acceptance run must additionally record:

- direct demo Building 150 in RTX Real-Time and RTX Interactive;
- direct external Building 150 in RTX Real-Time and RTX Interactive;
- glass, emission, and moving-camera parallax in both day and night lighting;
- the sequence `Start -> Stop -> move camera -> Start -> move camera ->
  Restart -> Stop -> Restore`, proving that Stop retains the ORMS image and
  freezes it while only Restore reveals the source material;
- at least three repeated lifecycle cycles, followed by Restore, with no
  accumulated ORMS layers, materials, camera targets, or callbacks;
- process RAM and GPU/VRAM values from the `ORMS PHASE 5 AUDIT` baseline,
  lifecycle samples, and restored comparison; and
- renderer prototype, unique-mesh, and instance counts from the RTX Statistics
  panel before Start, after repeated lifecycle cycles, and after Restore.

The installed `omni.hydra.engine.stats` Python surface provides device and
memory statistics but no exact renderer-prototype counter. ORMS therefore logs
the exact composed USD prototype count and any public renderer structure-memory
categories it receives, while the exact RTX renderer count remains an explicit
manual Statistics-panel observation. A USD prototype count must not be reported
as though it were the renderer count.

After manual acceptance:

- record the exact package version and renderer evidence in this document;
- retain the package as the recovery baseline;
- update the changelog and Jira state when requested; and
- create a repository commit only after Max explicitly authorises it.

The recovery build is not held back by native x2–x4 research.

#### Phase 6 — investigate preserved native x2–x4

Only after Phase 5 is accepted:

- branch the experiment away from the recovered backend;
- construct a minimal repository fixture with one instanced building,
  different façade and window materials, and mixed x1–x4 window faces;
- compare supported mechanisms for per-face and per-instance renderer data;
- keep the rejected instance-root collection path out of the experiment;
- evaluate a Hydra Scene Index override only as one possible mechanism, not as
  a predetermined architecture;
- measure renderer prototype sharing, RAM, VRAM, material count, and update
  cost;
- prove camera movement, per-instance transforms, Interior Sets, Stop, and
  Restore; and
- merge nothing into the recovery backend until the complete experiment has
  passed.

No experiment may modify or duplicate the user's production city. A small
purpose-built test fixture is test evidence, not a generated sidecar workflow.

If full native x2–x4 cannot be implemented safely, the accepted recovery build
remains ordinary x1–x4 plus native Preserve/x1. No de-instance, sidecar,
reference rewrite, or building-wide binding is accepted as a fallback.

## Reproduction

### Automated recovery matrix

| Scenario | Required result |
| --- | --- |
| Direct external Building 150 with `Windows_Glass` | Exact window Mesh receives classified ORMS; façade materials remain unchanged |
| Direct demo Building 150 with semantic window children | Compatible semantic children remain discoverable |
| Misspelled `*/Window_Glass` selector | Zero-match diagnostic; no unrelated Mesh changes |
| Correct `Windows_Glass` selector | Correct compatible target routing |
| Ordinary Mesh containing mixed families | Correct bounded x1–x4 GeomSubsets |
| Existing manual window binding | Temporarily overridden until Restore; exact source binding then returns |
| Instance fixture in `Preserve` | Native instances remain; only eligible windows receive `room_map_single` |
| City Building 136 | Only `Windows_Glass` changes; façade and all other materials remain original |
| Camera movement after Start and Restart | Continuous parallax in ordinary and native x1 routes |
| Material controls | Same applicable values reach `room_map` and `room_map_single` |
| Primary and fallback modes | Glass, emission, parallax, and diagnostics remain functional |
| Stop | Current ORMS view remains visible; camera-driven parallax updates freeze and settings remain |
| Restore Original Asset | All ORMS-owned state is destroyed without save or reopen |
| Repeated lifecycle cycles | No accumulating layers, materials, class overlays, callbacks, RAM, or VRAM; source inherit arcs remain exact |
| Stage switch and extension shutdown | Complete cleanup against the correct stage identity |

### Source-integrity checks

For every recovery scenario:

- the opened stage identifier remains unchanged;
- no `.orms.usda`, adapter, or wrapper is created;
- no save prompt is triggered by ORMS;
- root, reference, payload, and component layers gain no ORMS specs;
- runtime USD changes exist only in named ORMS-owned anonymous Session Layer
  sublayers;
- instanceable flags and prototype sharing remain unchanged;
- every native existing-class overlay contains bindings only at eligible
  selected relative window paths; and
- source material bindings compare equal before Start and after Restore.

### Renderer checks

Visual acceptance is repeated in:

- RTX Real-Time; and
- RTX Interactive Path Tracing.

The camera is moved after Start and after Restart. Glass and emission are
changed after the material is already visible. The result is inspected both at
the selected building and across the city to catch any escaped binding.

## Acceptance plan

### Recovery Registry release gate

The first recovery candidate may be published to the local Registry only when:

1. both direct Building 150 assets regain their ordinary x1–x4 behaviour;
2. record-009 `Preserve/x1` works on the retained instance fixture;
3. `room_map_city.usd` remains the open stage throughout the city check;
4. Building 136 and the other recognised prototypes keep native instancing;
5. only selected window proxies receive `room_map_single`;
6. every non-window part retains its source material;
7. all applicable material controls work in ordinary and native routes;
8. emission does not disable or replace parallax;
9. camera-following parallax survives Start and Restart;
10. Stop freezes the current ORMS appearance, while Restore reveals the exact
    original appearance;
11. source Houdini/USD layers remain unchanged;
12. no sidecar, adapter, stage reopen, save prompt, or de-instance occurs;
13. every new or changed functional unit has its happy path plus the required
    three to five, or up to eight, boundary and negative cases; and
14. repeated lifecycle operations do not accumulate runtime state.

The published Registry package becomes accepted only after Max completes the
manual Phase-5 viewport check.

### Native x2–x4 research gate

Native x2–x4 work cannot begin before the recovery Registry package is
accepted and recorded.

It cannot replace the recovery backend until it independently proves:

- x1–x4 grouping while native instancing remains enabled;
- exact window-only material ownership;
- per-instance transforms and Interior Set decisions;
- continuous camera response;
- material-control parity;
- bounded renderer prototype and memory cost;
- source-layer immutability; and
- complete Stop and Restore cleanup.

Every experimental unit is subject to the same unit-test coverage contract
before it can replace any part of the accepted recovery backend.

## Implementation journal after plan approval

This section is an additive execution record. It does not revise the
implementation plan, delivery order, or acceptance gates above. Its purpose is
to preserve what was actually attempted after the plan was approved, including
failed candidates and tests that proved earlier assumptions wrong.

### Ordinary-USD freeze

The recovered ordinary-USD route is no longer an experimental surface for
native-instance work. Native recovery must not redesign or replace:

- ordinary compatibility discovery;
- ordinary direct-Mesh and GeomSubset ownership;
- the classified `room_map` x1–x4 material graph;
- ordinary camera-coordinate handling; or
- ordinary Stop, Restart, and Restore ownership.

Max reported that the ordinary USD route worked during the manual check that
rejected the native part of 1.0.10. This is positive regression evidence, but
does not replace the complete two-asset and two-renderer Phase-1 acceptance
matrix.

One shared-API regression was found while preparing 1.0.11:
`AssignmentSession.apply()` had made `instance_source_asset_path` mandatory,
so an existing ordinary-only caller raised `TypeError` before assignment. A
focused run exposed the failure with 41 passing tests and one failure. The fix
only restored the argument to an optional native input; it did not change the
ordinary classifier, binding route, or `room_map` graph. The same focused
contour then passed 42 of 42 tests.

From this point forward, a native-only change that requires an ordinary-route
algorithm or shader change must stop for a separate review. Native work may
use shared read-only discovery and lifecycle infrastructure, but it must have
its own binding adapter and `room_map_single` ownership. The focused ordinary
regressions remain mandatory before publishing any native candidate.

### Iteration ledger

| Iteration | Intended change | What was wrong | How it was detected | Disposition or correction |
| --- | --- | --- | --- | --- |
| Recovery cleanup before 1.0.9 | Remove generated sidecars, preparation UI, stage reopening, reference substitution, and automatic de-instancing | Earlier experiments violated the temporary in-place runtime contract | Source and package inspection, plus the unwanted save/reopen behaviour seen in Kit | Removed from the recovery path; no duplicate city file, adapter workflow, preparation button, or automatic stage reopen is permitted |
| 1.0.9 | Restore ordinary USD and give preserved instances x1 through an instance-root collection | `ComputeBoundMaterial()` appeared window-only, but Kit/RTX broadened the visible result to non-window prototype geometry; the camera bridge also targeted an unattached classifier layer | Manual `room_map_city.usd` validation and repeated `SetEditTarget` failures in the supplied log | Candidate rejected; collection binding is prohibited as a native fallback; camera updates were moved to an attached owned layer |
| 1.0.10 | Replace the collection with a synthetic class containing exact window descendants | Each building received a second runtime `inherits` arc and the class targeted one global external `room_map_single` material. Point-instanced placements gained parallax, but the original prototype block lost it; non-window materials corrupted and the source block flickered. Stop and Restore did not make the result acceptable | Manual RTX Real-Time validation on the production city; the failure was visible only after material loading and was not represented by the passing OpenUSD binding assertions | Candidate rejected; the synthetic `InstanceClasses` namespace, root `AddInherit()`, and global native material were removed |
| 1.0.11 ordinary compatibility correction | Keep the already working ordinary route callable while isolating native inputs | A native parameter had accidentally become mandatory in the shared assignment session | Focused `test_assignment_session` failure before packaging | `instance_source_asset_path` is optional again; no ordinary assignment algorithm or material graph was changed |
| 1.0.11 native replacement | Reproduce the record-009 source-local x1 shape without changing native instance roots | Manual RTX validation rejected the candidate. Initial parallax appeared, but moving the camera corrupted materials across the city. The bridge still updated the inherited global `/World.primvars:ormsCameraPositionWorld`, so a camera change crossed the complete nested native-instance graph instead of an ORMS-material-only boundary | Manual production-city camera movement; the supplied log confirmed nine `INSTANCE_PRESERVED_X1_FALLBACK` paths all consuming the same global camera primvar | Candidate rejected. The existing-class window binding remains the narrowest composed binding proven by OpenUSD, but its global camera delivery is prohibited for the city route |
| 1.0.11 diagnostic failure | Capture the renderer failure with enough evidence to localise it | `/persistent/app/usd/muteUsdDiagnostics` remained `true`, ORMS verbose tracing remained disabled, and the log explicitly reported that USD warnings were muted. The earlier direct instruction to restore logging was not implemented | Supplied 1.0.11 log and the Kit user configuration | 1.0.12 enables USD diagnostics, USD coding errors, ORMS trace, Verbose file/Console logging, and all registered Console sources before stage activation |
| 1.0.12 native camera isolation | Preserve the window-only class overlay while removing camera motion from the complete `/World` hierarchy | The global inherited camera channel was shared by every native building and was rewritten every camera update | A production-city integration regression requires exactly nine class-local ORMS shader targets and zero `/World.*` camera targets, changes every target, and verifies that no Mesh binding changes. The installed Registry build was then checked in RTX Real-Time while the camera moved | Each native `room_map_single` material owns `Shader.inputs:camera_position_world`; the bridge updates only those source-class attributes. Ordinary `room_map`, ordinary assignment, and the ordinary camera route remain frozen. Automated evidence passed, and the manual viewport check confirmed moving-camera parallax with unchanged non-window appearance |
| 1.0.12 lifecycle validation | Validate Restart, Stop, and Restore on the installed native city rather than accepting unit coverage alone | Restart preserves the recovered result and Restore returns the source appearance, but Stop currently detaches the native ORMS assignment instead of freezing the current parallax state | Manual checks in both RTX renderer modes plus the complete-diagnostics lifecycle log | Restart and Restore are accepted for this candidate. Stop is safe and reversible but does not meet the intended frozen-result contract; record it as follow-up work and do not silently redefine Stop as Restore |
| Final fixture alignment | Keep the ordinary x1–x4 regression independent from mutable production exports | The retained Building 150 wrapper referenced `_external`, whose current consolidated `Windows_Glass` layout no longer matched the five-mesh fixture contract and made the complete suite fail despite the runtime recovery passing | The complete pre-commit suite failed six Building 150 expectations; a direct composed-stage check confirmed the versioned `_demo` component still contains the original five window meshes and 232-aperture x1–x4 contract | Point the retained wrapper at the versioned demo component and preserve every original count and grouping assertion. Do not weaken the test to accept 232 independent x1 rooms; production-city native validation remains a separate manual and integration path |
| 1.0.13 Phase-5 implementation | Correct Stop and add formal source/runtime evidence without changing the accepted ordinary route | The previous Stop called destructive runtime and assignment teardown, so it behaved like a partial Restore. The existing diagnostics proved in-memory source state during publication but did not compare exact source files, stage identity, instance structure, or resource ownership after Restore | Focused lifecycle tests exercise Stop, repeated Stop, Start-after-Stop, Restore-after-Stop, and inactive Stop. Source-integrity tests deliberately mutate source bytes, reopen the stage, de-instance an asset, and create a sidecar. The production-city test compares the complete baseline after teardown | Stop now pauses classifier and camera subscriptions while retaining the ORMS runtime and assignment layers. Restore alone performs teardown. The Phase-5 audit hashes all loaded file-backed USD layers and compares layers, bindings, materials, instances, prototypes, sidecars, callbacks, RAM, VRAM, and runtime structure. The ordinary classifier, material, binding, and camera paths were not changed |
| 1.0.13 package inspection | Inspect the actual Registry archive before asking for manual validation | The functional code was correct, but the bundled artist README still claimed that Stop removed the visual result | Archive content inspection after publication | Do not manually validate 1.0.13. It is superseded by 1.0.14, which changes only the packaged Stop description |
| 1.0.14 installed Stop/resume check | Verify the complete frozen-session transition rather than accepting owner counts from the unit model | Stop retained the correct ORMS image and froze parallax, but Start created a nominal camera subscription without restoring live parallax. Restart from the stopped state destroyed and recreated the same runtime material paths; RTX then reported destruction of the old MDL nodes after the replacement had already been published. Restore followed by a fresh Start worked | Manual direct-external Building 150 viewport sequence and the complete 6 September 2026 17:12–17:19 log | Reject 1.0.14. A non-null observer guard is not evidence that update callbacks are being delivered, and a stopped-session Restart must not recycle renderer prim paths merely to resume camera motion |
| 1.0.15 stopped-session correction | Resume the exact frozen runtime without touching the accepted ordinary classifier, bindings, material graph, or camera-coordinate algorithm | `CameraPositionBridge.pause()` used `ObserverGuard.reset()` and `resume()` registered a replacement observer from the UI lifecycle transition. The audit counted the returned guard but did not count delivered callbacks or successful writes | The installed SDK documents `ObserverGuard.enabled` as the supported pause control. Five focused bridge cases cover disable/enable reuse, repeated resume, permanent Restore reset, legacy reset fallback, and a forced first resumed write. Service coverage proves Restart from Stopped does not invoke the destructive rebuild path. The complete changed contour passes 51 tests | Stop now disables and retains one observer; Start re-enables it and clears the cached camera position so the next frame must write. Restart from Stopped uses the same resume path and therefore avoids same-path MDL destruction. Restore/shutdown alone call `reset()`. The audit now reports retained observers, delivered update callbacks, successful camera writes, and a one-shot `CAMERA UPDATE RESUME / ACTIVE` confirmation |
| 1.0.15 Registry publication | Package the stopped-session correction as a new immutable candidate | A published version must not be overwritten, and source tests do not prove archive content | Kit publisher verification passed. The 195-entry archive reports version 1.0.15, contains the corrected bridge, lifecycle audit, service resume branch, and current artist README, and contains no city sidecar, adapter, or native-preparation artefact | Published to the local Kit Registry for the narrow Stop -> Start and Stop -> Restart viewport retest before the remaining Phase-5 matrix continues |
| 1.0.15 installed lifecycle acceptance | Retest the previously failing stopped-session transitions in both supported renderers | The 1.0.14 observer replacement did not deliver updates after Stop, while Restore followed by Start did | Manual `Stop -> Start` and `Stop -> Restart` camera-movement checks in RTX Real-Time and RTX Interactive | Both transitions resume live parallax in both renderer modes. The lifecycle correction is accepted and must not be reopened while repairing the separate slice regression |
| 1.0.15 native depth-slice rejection | Verify that saved material controls affect the native x1 material in Debug and Production atlas modes | Slice toggles, depth, offset, scale, and per-slice emission were present in MaterialState and the UI, but `SINGLE_MATERIAL_INPUT_NAMES` filtered them out and `room_map_single.mdl` performed only the final room-face lookup | Manual Debug and Production checks failed in RTX Real-Time and RTX Interactive. The log confirms native assignments use `room_map_single.mdl`; source inspection confirms one lookup and no slice inputs. A 34-test focused contour covers the restored controls and five-lookup contract, and the dedicated `native_x1_full` Kit probe completed MDL compilation | Reject 1.0.15 as the final recovery baseline. In 1.0.16 the native x1 shader receives S1-S4 enable, depth, offset, scale, and emission inputs and composites four bounded slice samples over the room face. Ordinary `room_map`, ordinary classification/binding, and both camera routes remain unchanged |
| 1.0.16 Registry publication | Deliver the native depth-slice correction without reopening accepted ordinary or lifecycle code | The defect is renderer-visible and cannot be accepted from source assertions alone | The 34-test native contour and six package/Registry tests pass. Kit publisher verification reports `OK`. Archive inspection confirms version 1.0.16, 195 entries, five texture lookups and the new slice inputs in `room_map_single.mdl`, the corresponding material allow-list entries, and no city, sidecar, adapter, or preparation artefact | Published to the local Kit Registry for the narrow native Debug/Production slice retest in both RTX modes |
| 1.0.16 installed initial slice check | Verify that the published package, rather than source checkout or 1.0.15, is rendering the recovered native city | Kit initially autoloaded 1.0.15, then Extension Manager downloaded, installed, and started 1.0.16 from the local Registry before the city run | Max reports that the slices now appear. The 21:00-21:08 local log identifies the active package and Python modules as 1.0.16, opens its packaged `room_map_single.mdl`, assigns all nine eligible `Windows_Glass` meshes, authors nine native material specs, retains nine native instances and nine USD prototypes, and updates nine class-local camera inputs through one observer. No ORMS/MDLC compile error occurs. The only MDLC warnings are unrelated unused MaterialX transmission parameters | Initial native S1-S4 result accepted. The city Start record also reports an unchanged source USD digest, no changed Mesh bindings, and valid runtime binding scope. The log does not encode rendered S1-S4 pixels or include a post-Restore city comparison, so Debug/Production, both-renderer, control-by-control, and Restore claims remain limited to explicit manual observations |
| 1.0.16 committed recovery baseline | Freeze the working ordinary x1–x4 plus preserved-native x1/S1–S4 implementation before completing the remaining manual matrix | Source, package, compile-probe, installed lifecycle, city-camera, material-isolation, and initial slice evidence now agree on one implementation | The complete configured pre-commit gate passed, including formatting, linting, security checks, dependency audit, and the complete pytest suite | Commit `40dc4dd`, `Restore native-instance ORMS parity`, was pushed to `origin/main`. This is the current recovery implementation, but its commit status does not replace the still-open Phase-5 visual and resource observations |
| 1.0.17 live atlas switch | Force a targeted Material resync when a generated `room_atlas` value changes | USD published the expected resync, but RTX retained an incomplete specialised dependency graph and the window could remain transparent | Installed `single_room` Debug/Production Apply check; Restart restored the selected atlas | Reject 1.0.17. A classifier-only USD notice test is not evidence for the public Apply lifecycle |
| 1.0.18 synchronous Apply reactivation | Reuse the complete running-state Restart teardown/rebuild order inside Apply | The new graph was rebuilt in the same Kit update. The log shows correct Debug publication at 97,094 ms followed by stale RTX `MdlShadeNode` destruction at the reused paths at 97,137 ms | Installed Debug/Production Apply check plus the supplied complete-diagnostics log; only separate Restore then Start exposed the selected atlas | Reject 1.0.18. Synchronous call ordering and composed USD assertions do not model asynchronous renderer destruction |
| 1.0.19 renderer-separated Apply | Tear down first and publish only after RTX has processed the old graph removal | Acceptance still requires installed pixels; the source fix must also remain safe under repeated Apply, Restore, stage replacement, and deferred failure | The public service Apply regression models stale-node destruction and enforces publication afterward. Four edge cases cover supersession, cancellation, stale-stage rejection, and fail-open; the two affected files pass 49 tests and seven package/Registry tests pass | Published as an immutable local Registry candidate. The inspected 195-entry archive contains the two-update reactivation, reports 1.0.19, and contains no city, adapter, sidecar, or preparation artefact |
| 1.0.20 Extension Manager artwork | Package the updated ORMS icon and preview without reopening runtime behaviour | The installed 1.0.19 ordinary Apply result is accepted; this package must remain an artwork-only successor | Both replacement PNG files validate, seven focused package/Registry tests pass, and Kit publisher verification reports `OK` | Published to the local Registry. The inspected 195-entry archive reports 1.0.20 and contains byte lengths matching the repository icon and preview; runtime behaviour is unchanged from 1.0.19 |

### Current status against the delivery sequence

| Phase | Recorded status for the 1.0.16 candidate |
| --- | --- |
| Phase 0 — recover the implementation baseline | Implemented for the recovery candidate: sidecar generation, preparation UI, stage reopen, reference substitution, automatic de-instancing, and ancestor-wide fallback bindings are absent |
| Phase 1 — restore ordinary USD | Runtime route restored and reported working in the ordinary manual check. The accidental mandatory native argument was corrected. Complete direct-demo/direct-external validation in both required RTX modes remains part of final acceptance |
| Phase 2 — restore native Preserve/x1 | 1.0.11 was rejected because its global camera channel invalidated the city on camera movement. 1.0.12 retains the exact window overlay but isolates live camera writes to nine class-local ORMS shader inputs. OpenUSD production-city regression coverage passes; camera movement now preserves parallax and the original non-window appearance in both installed RTX modes |
| Phase 3 — prove material and lifecycle parity | Lifecycle parity is accepted: installed 1.0.15 passes Stop freeze plus Start/Restart resume in RTX Real-Time and RTX Interactive. Version 1.0.16 implements the missing native S1-S4 inputs and five-lookup composition, and the first installed visual check reports that the slices are visible again. Complete Debug/Production, both-renderer, control-by-control, emission, and post-Restore material parity remains part of Phase 5; the accepted lifecycle and ordinary paths remain frozen |
| Phase 4 — build the recovery candidate | Completed for `msp.orms.runtime-1.0.16`: 34 focused native tests and six package/Registry tests pass, the dedicated Kit `native_x1_full` probe compiles, Kit verification reports `OK`, and the inspected 195-entry archive contains the restored slice graph and no forbidden scene artefacts. The working implementation is committed as `40dc4dd` and pushed to `origin/main` |
| Phase 5 — manual Registry acceptance and baseline freeze | Installed 1.0.15 accepts the complete stopped-session lifecycle transition in both renderer modes but is rejected as the final baseline because native depth slices are absent. Installed 1.0.16 has initial visual confirmation that S1-S4 returned, and its log confirms the correct package, nine window-only native materials, preserved instance/prototype counts, active class-local camera delivery, and unchanged source USD state at Start. Live atlas Apply rejected 1.0.17 and 1.0.18; the installed 1.0.19 ordinary Debug/Production round trip is visually and log-confirmed. Artwork-only 1.0.20 carries the same runtime and is published. Native Apply plus the complete both-renderer, per-control and post-Restore scope still depend on explicit manual observations; the remaining direct-asset, lighting, source-integrity, repeated-cycle, and renderer-resource matrix also remains open |
| Phase 6 — investigate preserved native x2–x4 | Not started and remains prohibited until Phase 5 is accepted |

## Validation record

ORMS 1.0.9 passed OpenUSD binding checks but failed the required Kit/RTX city
check on 6 September 2026. The failure reproduced both prohibited outcomes:
non-window instance materials changed, and camera-following parallax did not
update. Its log records repeated `UsdStage::SetEditTarget` failures because
`orms_shared_rooms.usda` was not in the active local layer stack. This is a
rejected validation record, not partial acceptance.

ORMS 1.0.10 passed the focused OpenUSD suite and was published to the local
Registry, but failed the required manual RTX city check on 6 September 2026.
Point-instanced placements gained parallax, while the original prototype block
lost it. When ORMS materials loaded, non-window materials across the city were
corrupted, and the original block flickered between source and corrupted
states. Stop and Restore did not make this candidate acceptable. The added
runtime inherit arc and global instance material are therefore rejected even
though `ComputeBoundMaterial()` reported only window changes.

ORMS 1.0.11 retained the existing source-class window overlay and was
published to the local Registry, but failed the production-city RTX check on
6 September 2026. The initial frame could show parallax; moving the camera
then corrupted materials across the city. The supplied log records the same
global `/World.primvars:ormsCameraPositionWorld` target for all nine preserved
building paths. It also states that USD diagnostics were muted, while the
extension had left its detailed trace disabled. This candidate and its
diagnostic configuration are rejected.

The 1.0.12 correction keeps the same exact-window class overlay but removes
the global camera channel from this route. Each class-local `room_map_single`
shader receives its own explicit `camera_position_world` input; the runtime
classifier publishes those nine class-source attributes as the only native
camera targets. A production-city test starts assignment and classification,
requires zero `/World.*` camera targets, changes every class-local input,
verifies that all Mesh bindings stay unchanged, and then verifies complete
source restoration. Together with the focused diagnostics, assignment,
bridge, authoring, controller, and reload contour, 60 tests pass. Ten focused
package/Registry tests also pass. The resulting 193-file archive was published
to the local Registry as `msp.orms.runtime-1.0.12` and inspected for the
diagnostic and native-camera changes.

The installed 1.0.12 build passed the core manual recovery check in RTX
Real-Time and RTX Interactive on 6 September 2026. Max moved the camera and
confirmed that native-instance parallax continued to update while every
non-window building part retained its source appearance. Restart rebuilt the
same working result, and Restore Original Asset returned the source appearance.
The supplied complete-diagnostics logs independently record:

- startup of `msp.orms.runtime-1.0.12` with USD diagnostics, USD coding errors,
  ORMS trace, Verbose file logging, and all 21 registered Console sources
  enabled;
- two deliberate `manual_start` runs for two different stage identifiers,
  `room_map_city.usd` and `room_map_city_HDRI.usd`, rather than a classifier
  rerun caused by camera movement;
- exactly nine recognised `Windows_Glass` meshes in each stage;
- nine camera updates addressed only to
  `/__class__/.../ORMSRoomMapSingle/Shader.inputs:camera_position_world`;
- zero runtime-authored prim paths, zero runtime-authored source-material
  paths, zero unexpected runtime paths, and no direct Mesh or GeomSubset
  bindings from the classifier; and
- identical source-state digests before authoring, after authoring, and after
  the first rendered frame, with no changed or unexpected Mesh bindings and
  `runtime_binding_scope_valid=True`;
- `renderer_mode=PathTracing` during the RTX Interactive interval and
  `renderer_mode=RealTimePathTracing` during the RTX Real-Time interval; and
- a clean runtime detach followed by a user-triggered Restart, another complete
  runtime publication, nine renewed class-local camera updates, and another
  unchanged source-state digest after the first rendered frame.

No ORMS, OpenUSD, Hydra, or RTX error or Python traceback occurs in the checked
runtime interval. One `Ill-formed SdfPath <>` warning occurs while the first
stage is opening, before the ORMS loader begins; it is not accompanied by a
failed ORMS phase or source-state change. The log also contains ordinary Kit
stage-save messages, so source-file immutability is not inferred from those
messages alone; it remains an explicit file/layer-diff acceptance check.

This evidence closes the camera-movement and non-window-material failure that
rejected 1.0.9–1.0.11 in both required renderer modes. It also accepts Restart
and Restore for the 1.0.12 recovery candidate. The Restore result is manual
viewport evidence because the current service does not emit a dedicated
Restore-complete event.

Stop exposed one bounded lifecycle defect. It releases the camera subscription
and safely detaches the native ORMS overlay, which immediately restores the
instance assets to their source appearance. The intended product behaviour is
different: Stop must preserve the current ORMS visual result and freeze further
camera-driven parallax updates until Start, Restart, or Restore. This mismatch
does not reproduce material corruption, damage the source stage, or invalidate
the accepted Start/Restart/Restore result, but it remains explicit follow-up
work. No Stop implementation change is part of 1.0.12.

The 1.0.13/1.0.14 implementation attempted to correct that defect without
changing the accepted ordinary-USD route. Stop kept both temporary ORMS layers
attached, retained the last material state and camera value, and removed the
classifier and camera subscriptions. The unit model reported that Start could
register replacement owners, while Restart rebuilt the runtime and Restore
remained the only artist action that removed ORMS materials and assignments.
Coverage included Stop from Running, repeated Stop, Start after Stop, Restore
after Stop, and Stop without an active runtime. The installed 1.0.14 check later
proved that this ownership model was insufficient.

The same change adds a formal Phase-5 audit. Before assignment it records the
exact stage object and root-layer identity, SHA-256 digest, byte size, and
modification time of every file-backed layer returned by `GetUsedLayers()`,
the source-layer structure and dirty state, source material networks and
effective Mesh/GeomSubset bindings including instance proxies, native-instance
paths, stable USD prototype structure, PointInstancer prototype targets, and a
sidecar/adapter directory inventory. After Restore it repeats that capture and
emits one explicit pass/fail comparison. The production-city integration test
covers all 37 loaded file-backed USD layers and proves exact source restoration
after the native assignment, classifier, and camera bridge are removed.

Each verbose Phase-5 run also records a resource baseline and lifecycle samples
for Start, Restart, resumed Start, Stop, and Restore. The record includes ORMS
runtime layer/spec/material counts, assignment and runtime owners, enabled
camera callbacks, retained observer guards, delivered update callbacks,
successful camera writes, camera targets, native instances, composed USD
prototype count, process working set and private commit, GPU device/VRAM
fields, public Hydra memory categories, and renderer/material settings. This
data is diagnostic evidence rather than a synthetic pass based on an arbitrary
memory threshold. Exact renderer-prototype count is not exposed by the
installed public Python API and must be copied from the RTX Statistics panel;
the automatically reported USD prototype count is a separate composition
metric.

The 1.0.13/1.0.14 functional plus package contour passed 93 tests. The initial
1.0.13 archive passed Kit verification but was superseded before manual testing
because archive inspection found the obsolete Stop description in its bundled
README. Version 1.0.14 contained the same runtime plus corrected artist
documentation. Its 195-entry archive passed Kit verification and contained no
city sidecar, adapter, or native-instance preparation artefact.

The installed 1.0.14 run accepted only the first half of the new Stop contract:
the current ORMS image stayed visible and stopped following camera movement.
After Start, the audit reported one camera subscription, but moving the camera
did not resume parallax. Restart from the stopped state also failed to restore
continuous motion. The log recorded asynchronous RTX destruction of the old
`MdlShadeNode` objects at the same material paths immediately after the
replacement runtime had been published. By contrast, Restore Original Asset
followed by a fresh Start worked. Version 1.0.14 is therefore rejected; guard
existence is not callback-delivery evidence.

The same log contains both passing and failing source comparisons. In the
failing records, source file inventory, bytes and timestamps, stage/root
identity, material bindings, material networks, instance signatures,
prototypes, PointInstancer targets, sidecar inventory, and runtime cleanup all
pass; only the combined source-layer structure/dirty-state comparison fails.
That record does not identify which of identifier, sublayers, ORMS-named specs,
or the ordinary USD dirty flag changed, so it is diagnostic evidence requiring
a clean no-user-edit repeat, not evidence that ORMS rewrote a source file.

Version 1.0.15 changes only the lifecycle subscription boundary and its
diagnostics. `ObserverGuard.enabled` from the installed Kit API now suspends and
resumes the same registered camera observer. The first resumed frame clears the
cached camera position, authors the current value, and emits
`CAMERA UPDATE RESUME / ACTIVE`. Restore and shutdown still permanently reset
the guard. Restart from Stopped uses that same non-destructive resume path,
avoiding immediate reuse of removed material paths; Restart from Running keeps
the existing rebuild path. Five camera-observer edge cases and the stopped
Restart service branch are covered in a 51-test focused lifecycle/package run.
Kit verification passed, and the resulting 195-entry 1.0.15 archive was
published to the local Registry.

The installed 1.0.15 check subsequently confirmed both
`Stop -> Start -> move camera` and `Stop -> Restart -> move camera` in RTX
Real-Time and RTX Interactive. Stop retains the ORMS image and freezes camera
updates; either resume action restores continuous parallax. The lifecycle
correction is therefore accepted in both renderer modes.

That same candidate exposed a separate material-parity regression. All four
depth slices were enabled in the Material Parameters UI and stored in the
Interior Set, yet neither Debug nor Production atlases displayed S1-S4 in
either renderer. The runtime log showed that native city windows were assigned
`room_map_single.mdl`; source inspection then proved that this native shader
had only the final room-face texture lookup and no slice parameters. The public
MaterialState still contained every slice control, but
`SINGLE_MATERIAL_INPUT_NAMES` deliberately filtered them from native
materials. The failure was therefore neither an atlas-loading defect nor a
profile-persistence defect: the selected native shader never consumed the
saved controls.

This was an incorrect interpretation of the record-009 x1 contract. `x1`
means one independently varied room per eligible window; it does not mean that
the room loses its layered S1-S4 depth planes. Version 1.0.16 corrects only
this native material boundary. `room_map_single.mdl` now intersects the same
x1 view ray with four configurable depth planes, clips them to the analytic
room and visible room-face distance, samples the four documented atlas corner
tiles, alpha-composites them over the five-face result, and applies per-slice
emission. Its bounded cost is five atlas lookups. Native material assignment
now forwards slice enable, depth, offset, scale, and emission values. No change
was made to ordinary `room_map`, ordinary classification or binding, the
accepted camera bridges, or lifecycle ownership.

The focused native contour passes 34 tests. It includes static S1-S4 shader
contract assertions, initial and live native material-input authoring, source
integrity and preserved-instance checks, and compile-probe launcher coverage.
The dedicated `native_x1_full` Kit probe completed shader-node construction in
17.219 seconds and the fixture completed in 20.609 seconds. This proves that
the restored MDL graph compiles; visible Debug/Production slice behaviour still
requires the installed 1.0.16 Registry check.

Version 1.0.16 passed six focused package/Registry tests and Kit publisher
verification, then was published to the local Registry. The inspected archive
contains 195 entries and reports version 1.0.16. Its packaged native shader has
four slice lookups plus the room-face lookup and exposes the restored slice
inputs; its packaged native material allow-list includes those inputs. No city
asset, sidecar, adapter, or native-preparation artefact is present.

The first installed 1.0.16 run provides matching runtime evidence. The app
initially autoloaded 1.0.15, then Extension Manager downloaded, installed, and
started 1.0.16 from the local Registry before the city was activated. All
reported ORMS module paths and the loaded native MDL resolve below the installed
1.0.16 directory. Automatic assignment selected exactly nine of nine eligible
`Windows_Glass` meshes. The Phase-5 sample records 443 runtime specs, nine
native material specs, nine native instances, nine composed USD prototypes,
nine class-local camera targets, and one camera observer. The next update
delivered the camera value to all nine class-local shader inputs. There is no
ORMs or MDLC compile error; the only MDLC warnings concern unused parameters in
Kit's generated MaterialX module.

Max's viewport observation reports that the missing native slices are now
visible. The city Start diagnostic also reports an unchanged source USD state
digest, no changed Mesh bindings, no unexpected authored path, and a valid
runtime binding scope. The generic classifier's `material_count=0` and resource
diagnostic's `runtime_material_count=0` refer to the ordinary classified
material collection; native class-local ownership is recorded separately by
`runtime_material_spec_count=9` and is not absent. This log contains no
post-Restore comparison for the city and cannot encode rendered slice pixels,
so it does not by itself close the full Debug/Production, renderer, individual
control, Restore, or resource matrix.

On 7 September, a separate ordinary-USD live-resource regression was reproduced
with `assets/_external/usd/single_room/single_room.usd`. Production resources
rendered on initial Start, but applying the global Debug policy to the running
session left the ORMS window visually empty. The runtime log proved that the
selector still found the same window, its direct binding still targeted the
same generated x1 material, every packaged Debug UDIM resolved, and the draft
contained the expected Debug `room_atlas`. Publication nevertheless reported
zero resynced paths and only an information-only change for
`Shader.inputs:room_atlas`; no ORMS, MDL compiler, or texture-resolution error
followed. Inspection of the packaged x1 tiles also confirmed valid opaque face
regions. The defect was therefore localised to RTX retaining the existing MDL
material node when an asset-valued shader input changed at a stable prim path,
not to atlas content, selection, binding, or source USD.

Version 1.0.17 adds a narrow renderer-invalidation boundary without changing
the ordinary classifier, source bindings, camera bridge, or native assignment
route. Before the finished draft is transferred, ORMS compares only authored
`room_atlas` signatures below its generated materials. For each actual resource
change it removes that ORMS-owned Material from the live runtime layer and
transfers the complete candidate back inside the same `Sdf.ChangeBlock`. USD
therefore publishes one resync at the exact generated Material path while the
final material path and window binding remain stable. Source geometry,
non-window materials, Root Layer, referenced layers, and Houdini/USD files are
outside that operation. A no-op Apply does not resync anything.

Three focused regressions cover one changed family, Debug/Production round-trip
replacement, and same-resource reapplication. They additionally assert that
all resynced paths remain below the relevant ORMS Interior Set, the bound window
material path is unchanged, and the Root Layer is byte-for-byte unchanged. The
complete nearby controller and pipeline contour passes 25 tests. Installed RTX
validation of 1.0.17 remains required before this correction is accepted.
The immutable 195-entry 1.0.17 archive passed Kit publisher verification, was
published to the local Registry, and was inspected to confirm both its version
metadata and the targeted atlas-resync implementation.

The installed 1.0.17 check rejected that correction. Applying either Debug or
Production resources could still leave the window transparent, while pressing
Restart immediately restored the selected atlas. The targeted Material resync
therefore did not invalidate the complete RTX dependency graph. Code-path
comparison exposed the missing boundary: live Apply removed and recreated the
auto-assignment layer while the existing classifier materials that specialised
those assignments were still attached. Running-state Restart first tears down
the classifier and its renderer dependencies, then replaces assignments and
builds the classifier again.

Version 1.0.18 removes the ineffective targeted-resync experiment and routes
Apply Interior Sets through that same complete reactivation boundary. Because
the Interior Set controller has persisted but not yet accepted its transaction
when the callback runs, the candidate collection and resolved resource snapshot
are passed explicitly into activation. Renderer teardown therefore precedes
assignment-layer teardown; ordinary direct assignments and preserved-native
class-local assignments are then rebuilt from the selected atlas policy before
the classifier and camera bridge start again. Assignment overrides are retained,
and no source or instance-proxy opinion is authored.

The regression boundary now covers the public service callback and the ordering
that distinguishes Apply from the rejected implementation. Separate ordinary
and native replacement tests apply Production and Debug atlas paths in turn.
They verify the resulting shader asset, original binding restoration, unchanged
native facade, retained instanceability, and byte-for-byte unchanged source
layers. Four focused regression cases and the complete two affected test files
pass; the latter result is 44 tests. Installed 1.0.18 validation remains the
required renderer proof.
The immutable 195-entry 1.0.18 archive passed Kit publisher verification, was
published to the local Registry, and was inspected to confirm its version and
controlled Apply-reactivation implementation.

Installed RTX validation rejected 1.0.18. Selecting either Debug or Production
and pressing Apply produced no visible resource change; the selected result
appeared only after two separate user actions, Restore Original Asset followed
by Start. The supplied verbose log removes the remaining ambiguity. At
`97,094 ms` the replacement Debug runtime finished publication with the
correct packaged `room_map_debug_x1.<UDIM>.png` resource and a valid window-only
binding. At `97,137 ms`, roughly 43 ms later, RTX destroyed the old
`MdlShadeNode` objects at the same auto-assignment and Interior Set shader
paths. The nominally correct replacement graph had therefore been published
inside the asynchronous destruction window and was lost with the stale graph.
The earlier 1.0.18 tests checked synchronous Python ordering and composed USD
state, so they could not reproduce this renderer-lifetime race and are not
accepted as evidence for Apply behaviour.

Version 1.0.19 turns Apply into a two-phase reactivation. The synchronous phase
commits the candidate profile, tears down the classifier, then removes its
assignment layer. The service retains the source stage and AssignmentSession
but does not recreate any MDL material immediately. The asynchronous phase
waits for two complete Kit updates, giving RTX a renderer-processing boundary
in which to destroy the previous nodes, and only then rebuilds assignments,
classifier materials, bindings, and the camera bridge from the exact committed
collection and resource snapshot. This changes service orchestration only; the
accepted ordinary classifier, shader, binding, and camera-coordinate route and
the preserved-native x1 material route remain unchanged.

Pending Apply work is revisioned and coalesced so only the newest Debug or
Production choice can publish. Restore, stage replacement, and extension
shutdown invalidate and cancel it. Before publication the delayed phase also
checks that both the active stage and retained AssignmentSession are still the
ones prepared by the synchronous phase. A deferred activation error follows
the existing fail-open cleanup and leaves the original asset visible.

The corrected regression boundary now enters through the public service Apply
callback and models delayed destruction of the stale renderer nodes. It fails
if the new runtime publishes before that destruction boundary. Four additional
edge cases cover newest-Apply supersession, Restore while waiting, stale-stage
rejection, and deferred fail-open cleanup. Together with the ordinary direct
and preserved-native assignment replacement checks, the two affected test
files pass 49 tests; seven focused package and local-Registry tests also pass.
Kit publisher verification reported `OK`, and immutable 1.0.19 was published
to the local Registry. The inspected 195-entry archive contains the deferred
reactivation implementation and correct version metadata, with no city,
adapter, sidecar, or native-preparation artefact.

The installed ordinary-USD round trip is now accepted for 1.0.19. Max observed
both atlas changes without Restart or Restore/Start. The supplied log confirms
that Registry 1.0.19 was loaded, the Production and Debug snapshots were
published in turn, every stale ORMS `MdlShadeNode` was destroyed before the
corresponding replacement runtime began, no later stale destruction occurred,
and the exact window-only binding remained valid. Native-instance validation
remains a separate acceptance item.

Version 1.0.20 changes only the Extension Manager artwork. The new 1080 x 1080
icon and 1734 x 905 preview are valid PNG files; runtime code is identical to
the 1.0.19 candidate. Seven focused package/Registry tests and Kit publisher
verification pass. The immutable 195-entry archive was published to the local
Registry and contains image byte lengths matching the repository sources.

The working recovery implementation was committed as `40dc4dd`,
`Restore native-instance ORMS parity`, after the complete configured
pre-commit gate passed, and was pushed to `origin/main`. This freezes the
ordinary x1–x4 plus preserved-native x1/S1–S4 implementation that produced the
recorded evidence; it does not convert an initial visual observation into full
Phase-5 acceptance.

The remaining Phase-5 gate is therefore to record the still-unconfirmed parts
of the native slice matrix plus the already documented direct-asset, lighting,
repeated-cycle, source-integrity, and resource observations. Native x2–x4
research remains gated behind that acceptance.

Accepted historical evidence:

- `f0f625f` is the known-good pre-recovery baseline;
- `40dc4dd` is the current committed recovery implementation for ordinary
  x1–x4 plus preserved-native x1/S1–S4;
- record 009 contains renderer-validated native-instance `Preserve/x1`
  evidence; and
- records 010 through 012 contain the accepted ordinary Building 150,
  material-control, extension, and artist-workflow evidence.

The 1.0.16 implementation is no longer uncommitted. Commit and publication do
not by themselves close the remaining manual Phase-5 matrix, and rejected
experimental versions remain rejected regardless of their version numbers.

The recovery validation entry must record:

- exact source revision and package version;
- exact Kit, RTX renderer, and extension versions;
- exact fixture and production paths;
- selector values and target counts;
- before/after source material identities;
- camera movement after Start and Restart;
- lifecycle sequence;
- source-layer diff;
- instanceability and renderer-prototype counts;
- RAM and VRAM measurements; and
- Max's manual Registry acceptance.

## Boundary

This record authorises the documented implementation sequence but does not
claim that the recovery build or native x2–x4 research has already passed.

The recovery target is explicitly:

- ordinary USD with full x1–x4; plus
- preserved native instances with the accepted x1 `room_map_single` path.

Full x2–x4 grouping for preserved native instances is a later research target.
Hydra Scene Index is one hypothesis for that later target, not a prerequisite
for recovering the already proven native x1 path.

No fallback may de-instance the city, create a production sidecar, reopen the
stage, rewrite references, author through an instance proxy, or broaden the
ORMs binding to a whole building.
