# ORMS Runtime Recovery and Native-Instance Integration Plan

## Record

| Field | Value |
| --- | --- |
| Jira | Follow-up to KRM-91, KRM-92, KRM-93, and KRM-98; recovery issue not yet assigned |
| Known-good baseline | Commit `f0f625f`, `Release ORMS 1.0.1 with demo and licensing` |
| Accepted native-instance evidence | `009_shared_multi_window_rooms.md` |
| Implementation target | `exts/msp.orms.runtime/` |
| Validation assets | `assets/_demo/Moskovskiy_av_150/usd/Moskovskiy_av_150.usd`; `assets/_external/usd/Moskovskiy_av_150/usd/Moskovskiy_av_150.usd`; `assets/_external/usd/room_map_city.usd` |
| State | In progress — 1.0.12 passed native camera and material-preservation checks in both RTX modes; Stop semantics remain to be corrected |
| Last reviewed | 6 September 2026 |

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
- eligible instance-proxy windows receive the lightweight
  `room_map_single` x1 material;
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
- a lightweight x1 material contract;
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

The five-atlas-lookup budget of the classified shader and the lightweight x1
contract remain unchanged unless a later MDL record supplies new renderer
evidence.

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

### Current status against the delivery sequence

| Phase | Recorded status after 1.0.12 publication |
| --- | --- |
| Phase 0 — recover the implementation baseline | Implemented for the recovery candidate: sidecar generation, preparation UI, stage reopen, reference substitution, automatic de-instancing, and ancestor-wide fallback bindings are absent |
| Phase 1 — restore ordinary USD | Runtime route restored and reported working in the ordinary manual check. The accidental mandatory native argument was corrected. Complete direct-demo/direct-external validation in both required RTX modes remains part of final acceptance |
| Phase 2 — restore native Preserve/x1 | 1.0.11 was rejected because its global camera channel invalidated the city on camera movement. 1.0.12 retains the exact window overlay but isolates live camera writes to nine class-local ORMS shader inputs. OpenUSD production-city regression coverage passes; camera movement now preserves parallax and the original non-window appearance in both installed RTX modes |
| Phase 3 — prove material and lifecycle parity | The focused assignment, material, camera, classifier, and lifecycle contour passes. Manual Start, camera movement, Restart, and Restore pass in the production city. Stop safely restores the native source appearance but fails the intended frozen-result semantics and remains follow-up work; explicit source-layer/prototype measurements also remain pending |
| Phase 4 — build the recovery candidate | Completed for `msp.orms.runtime-1.0.12`: 60 focused functional tests and 10 package/Registry tests passed. The 193-file archive was published and inspected for diagnostic capture, class-local camera targets, and absence of the rejected assignment-side global camera channel |
| Phase 5 — manual Registry acceptance and baseline freeze | The installed 1.0.12 Registry build passed the production-city visual recovery checks in RTX Real-Time and RTX Interactive: moving-camera parallax, non-window material preservation, Restart, and Restore. Stop is reversible but restores the native source appearance instead of freezing ORMS, so the complete lifecycle gate remains open together with explicit source-integrity and resource-count checks |
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

The complete Phase-5 gate therefore remains open for the Stop semantic
correction, explicit source-file/layer comparison, and renderer-prototype and
RAM/VRAM measurements. Native x2–x4 research remains gated behind that work.

Accepted historical evidence:

- `f0f625f` is the last committed recovery baseline;
- record 009 contains renderer-validated native-instance `Preserve/x1`
  evidence; and
- records 010 through 012 contain the accepted ordinary Building 150,
  material-control, extension, and artist-workflow evidence.

The current uncommitted runtime and already published broken experimental
versions are not accepted merely because their version numbers are higher.

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
