# Changelog

## 1.0.20

- Replace the Extension Manager icon and package preview with the updated ORMS
  artwork. Runtime behaviour is unchanged from 1.0.19.

## 1.0.19

- Reject 1.0.18 after installed RTX validation showed that Apply detached and
  rebuilt the runtime in one Kit update: the new Debug or Production graph was
  published, then delayed RTX cleanup destroyed MDL nodes at those reused
  paths. Only a separately invoked Restore followed by Start exposed the new
  atlas reliably.
- Split Apply reactivation across the renderer boundary. ORMS now tears down
  the classifier and assignment layer first, waits for two complete Kit
  updates so RTX can release the old graph, and only then publishes the newest
  committed Interior Set snapshot.
- Coalesce repeated Apply requests and guard delayed work by revision, active
  stage, and assignment-session ownership. Restore, stage replacement, and
  extension shutdown cancel pending work; a deferred build failure cleans up
  to the original source state.
- Add regression coverage through the public Apply service callback, including
  delayed old-node destruction, Production/Debug supersession, Restore during
  the renderer wait, stale-stage rejection, and deferred fail-open cleanup.
  Existing ordinary and preserved-native assignment checks continue to cover
  exact window-only binding and unchanged source data.

## 1.0.18

- Reject 1.0.17 after the installed `single_room` check showed that applying
  either Debug or Production resources could still leave a transparent window;
  pressing Restart immediately restored the selected atlas.
- Route Apply Interior Sets through the same controlled renderer teardown and
  complete runtime reactivation as the proven running-state Restart path. The
  not-yet-accepted collection and resource snapshot are passed directly into
  that rebuild, so the committed UI transaction is rendered without recycling
  its auto-assignment layer beneath live specialised MDL materials.
- Preserve assignment overrides, native instancing, window-only bindings,
  non-window materials, source layers, and camera startup across that
  reactivation.
- Add service-level ordering coverage plus ordinary and preserved-native atlas
  replacement tests. The tests cover Production/Debug resource changes,
  renderer teardown before assignment teardown, stable source bindings,
  unchanged facades, retained instances, and unchanged source USD.
- Installed RTX validation rejected this approach: publishing the replacement
  graph in the same Kit update raced delayed destruction of the old MDL nodes.

## 1.0.17

- Attempt to correct live Production-to-Debug and Debug-to-Production atlas
  changes when
  the generated ORMS material keeps its stable prim path. A changed
  `room_atlas` asset now produces a targeted material resync during the same
  atomic runtime-layer publication instead of an information-only update that
  RTX can leave visually empty.
- Limit that resync to the generated ORMS materials whose atlas asset actually
  changed. Window bindings keep their stable material paths, source geometry
  and source material bindings remain untouched, and reapplying the same atlas
  does not invalidate a material.
- Add focused coverage for a one-family resource change, the complete
  Production/Debug round trip, unchanged-resource reapplication, stable window
  binding, and unchanged source USD.
- Installed RTX validation rejected this approach: a Material-prim resync did
  not rebuild the complete specialised dependency graph, while Restart did.

## 1.0.16

- Restore the four S1-S4 depth slices in the preserved-native x1 material.
  Version 1.0.15 correctly saved and displayed those controls, but its
  `room_map_single` shader never consumed them, so both Debug and Production
  atlases rendered only the five room faces.
- Keep native room grouping at x1 while giving that room the same bounded
  four-slice composition and per-slice emission controls as the ordinary
  material. The native material now performs four slice lookups plus one room
  lookup; the accepted ordinary classifier, binding, shader, and camera paths
  are unchanged.
- Add a dedicated native-x1 MDL compile probe and focused material-assignment
  coverage for slice enable, depth, offset, scale, and emission updates.

## 1.0.15

- Reject 1.0.14 after the installed lifecycle check showed that Stop froze the
  correct image but Start did not restore live camera updates. Stop now retains
  one disabled Kit update observer, Start re-enables that exact observer and
  forces a current-camera write, while Restore alone permanently releases it.
- When Restart is pressed from the stopped state, resume the retained runtime
  instead of destroying and immediately recreating MDL prims at the same paths.
  Restart from a running state keeps its existing rebuild behaviour.
- Extend Phase-5 diagnostics with retained-observer, delivered-callback, and
  successful-camera-write counts plus one explicit confirmation after resume.

## 1.0.14

- Supersede the unvalidated 1.0.13 Registry package after archive inspection
  found that its bundled artist README still described the old destructive
  Stop behaviour. The runtime implementation is unchanged from 1.0.13; the
  packaged overview now states that Stop freezes ORMS and only Restore removes
  its temporary layers.

## 1.0.13

- Correct Stop so it retains the current ORMS materials and last camera value
  while releasing live classifier and camera subscriptions. Start resumes that
  frozen session, Restart rebuilds it, and Restore remains the destructive
  removal operation.
- Add a Phase-5 source-integrity audit that hashes every loaded file-backed USD
  layer before activation and compares source bytes, layer structure, material
  networks and bindings, native-instance structure, point-instancer targets,
  stage identity, and new sidecar entries after Restore.
- Record bounded lifecycle resource samples for temporary layers, material
  specs, owned callbacks, camera targets, USD prototypes, RAM, VRAM, and public
  Hydra memory categories. Exact renderer-prototype counts remain a manual RTX
  Statistics measurement because the installed public Python API does not
  expose that counter.
- Leave the accepted ordinary-USD classification, material, binding, and camera
  paths unchanged while extending the production-city native recovery test
  with the complete before-Start/after-Restore source comparison.

## 1.0.12

- Reject 1.0.11 after the production-city RTX check: moving the camera could
  invalidate materials across the nested native-instance graph because the
  bridge updated one global `/World.primvars:ormsCameraPositionWorld` value.
- Give each temporary native `room_map_single` material an explicit
  class-local `camera_position_world` input. The camera bridge now targets
  only those ORMS shader attributes and does not author or update the global
  camera primvar for this native assignment route.
- Leave the recovered ordinary-USD classifier, `room_map` graph, direct mesh
  bindings, and camera route unchanged.
- Enable the complete recovery diagnostic surface at extension startup:
  USD diagnostics and coding errors are unmuted, ORMS trace is enabled, file
  and Console logging use Verbose, and every registered Console source is
  selected.
- Add production-city regressions for assignment, classifier startup, camera
  updates, absence of the global camera primvar, unchanged non-window
  bindings, and complete teardown. Installed RTX Real-Time and RTX Interactive
  checks confirm moving-camera parallax, preserved non-window appearance,
  Restart, and Restore. Stop safely restores the native source appearance but
  does not yet freeze the current ORMS result as intended.

## 1.0.11

- Replace the rejected 1.0.10 added-inherit mechanism with temporary overlays
  on the source classes already authored by the Houdini building assets. ORMS
  never changes an instance root's inherit list.
- Keep each native x1 `room_map_single` material inside its source-class
  namespace and bind only the selected window descendant. The material target
  therefore resolves locally inside each building rather than through a
  global material shared outside the native prototype.
- Fail open when a native asset has no single unambiguous source class, and
  omit the unsupported `enable_opacity` input from `room_map_single`.
- Add regression coverage for the real nested
  `PointInstancer -> native instance` city structure, exact non-window binding
  preservation, unchanged source inherit arcs, cleanup, missing classes, and
  ambiguous classes.

## 1.0.10

- Rejected native-instance candidate. Manual RTX city validation showed
  corrupted non-window materials, unstable source-prototype materials, and
  broken parallax on the original prototype block.
- Replace the rejected instance-root collection from 1.0.9 with a removable
  inherit overlay that composes a direct `room_map_single` binding only at
  each eligible relative window path. Native instances stay instanceable and
  non-window descendants retain their source bindings.
- Route native camera updates to the attached assignment layer when the
  shared-room classifier publishes no layer. A detached runtime layer now
  fails open with one diagnostic instead of raising `SetEditTarget` every
  frame.
- Mark 1.0.9 as rejected for native-instance scenes: its OpenUSD collection
  test did not represent the visible Kit/RTX result.

## 1.0.9

- Rejected native-instance candidate. Do not use it for production native
  scenes; its instance-root collection can recolour non-window geometry in
  Kit/RTX and its camera bridge can target an unattached runtime layer.
- Ordinary authorable USD behaviour remains valid evidence from this build.
- Restore ordinary USD discovery and retain full x1-x4 classification without
  allowing Interior Set selectors to replace legacy compatibility rules.
- Add removable window-only collection bindings for native instances. The
  building remains instanceable, non-window materials stay untouched, and the
  lightweight `room_map_single` x1 material receives live camera, glass, and
  emission controls.
- Remove generated sidecars, stage reopening, and Session de-instancing from
  the native-instance workflow. Stop and Restore reveal source bindings by
  detaching ORMS-owned runtime layers.

## 1.0.8

- Rejected local candidate. Its generated sidecar workflow is removed in
  1.0.9 and must not be used for production scenes.

## 1.0.7

- Disable unsafe Preserve-mode auto-assignment through already composed
  instance proxies. ORMS now reports that those meshes require a source or
  persistent instance-ready adapter and leaves every source material and
  reference arc untouched.
- Retain automatic assignment for ordinary meshes and for the explicit
  Session de-instance policy. Repeated Start, Restart, Stop, and Restore can no
  longer introduce runtime instance-source substitutions.
- Add an editable mesh-name/path selector to the Default Interior Set, seeded
  as `Windows_Glass`, and use all Interior Set selectors when discovering
  source meshes for automatic assignment.

## 1.0.6

- Replace Preserve-mode collection bindings with ephemeral instance-ready
  adapters that bind `room_map_single` directly to eligible window meshes
  before native instancing occurs.
- Keep every non-window material binding untouched in RTX while retaining the
  original building instances and restoring their source references on stop.

## 1.0.5

- Keep the inherited instance camera primvar in the live viewport-camera
  update targets so Preserve-mode parallax continues after `Restart` and
  camera movement.
- Host Preserve-mode collection bindings on non-instance parents and use
  explicit-only membership so restarting ORMS cannot override unrelated
  facade, roof, or trim materials inside building instances.

## 1.0.4

- Apply the Default Interior Set material profile to both classified room
  families and Preserve-mode x1 instance fallbacks.
- Propagate every lightweight x1 control, including glass and emission, to
  Preserve-mode fallback materials without compiling the classified slice DAG
  inside an instance prototype.
- Treat an intentionally empty shared-room runtime layer as a valid Preserve
  result instead of attempting to edit an unattached USD layer.

## 1.0.3

- Keep composed building instances intact while assigning the x1 ORMS fallback
  to eligible `Windows_Glass` proxies through instance-root collections.
- Reserve Session de-instancing for explicitly selected full shared-room
  classification instead of requiring it for automatic material assignment.

## 1.0.2

- Discover eligible `Windows_Glass` meshes inside composed instance proxies.
- Apply ORMS through source-safe Session de-instancing when that instance
  policy is selected, and report a clear diagnostic in Preserve mode.
- Restore original instanceability and remove all temporary bindings when the
  assignment session ends.

## 1.0.1

- Establish an explicit mixed-licence distribution boundary: MIT software,
  CC BY 4.0 debug atlases, evaluation-only demo assets, and the CC0 demo HDRI.
- Include the licence map, licence references, and third-party notices in every
  standalone extension package.

## 0.1.28

- Disable research phase traces and the per-update stage-load probe by
  default, while retaining critical warnings and errors.
- Preserve the complete Warning-level research trace behind the persistent
  `verboseDiagnostics` Kit setting.

## 0.1.27

- Add the bundled Building 150 demo scene and eight-variant atlas with
  one-click opening from the Interior Atlases tab.
- Apply the demo profile automatically only over untouched factory settings,
  while preserving existing configurations and prompting for unsaved stages.
- Resolve relative atlas directories from their owning `.orms` profile and
  include the complete demo content in standalone registry packages.

## 0.1.26

- Organise the runtime package by ownership boundaries for assignments,
  Interior Sets, profiles, materials, and artist-facing UI without changing
  extension behaviour.

## 0.1.25

- Give wrapped hover help an explicit dark text colour so the light tooltip
  background retains readable contrast under the host application's theme.

## 0.1.24

- Render hover help in a compact fixed-width tooltip with automatic word
  wrapping instead of an unreadable single line across the viewport.

## 0.1.23

- Move persistent workflow explanations into hover tooltips across the ORMS
  tabs so controls retain compact vertical spacing.
- Keep transient state, validation errors, and apply feedback visible while
  hiding normal packaged-resource status lines from the atlas layout.

## 0.1.22

- Make `data/atlases/room_map_debug_x1` through `room_map_debug_x4` the
  extension-owned source and packaged location for global debug atlases.
- Add staged editable x1-x4 debug folders with Browse and Clear controls;
  Clear restores the corresponding packaged default.
- Use valid custom debug families in forced Debug mode and as Production
  fallback, while retaining packaged fallback for invalid custom folders.
- Keep production atlas content outside the extension-owned debug tree.

## 0.1.21

- Consolidate all ORMS Python and MDL product source under the Kit extension
  tree, leaving `tools/` for repository utilities only.
- Package the canonical extension tree directly instead of maintaining a
  second Python runtime copy under `data/runtime` or a separate `src/mdl` tree.
- Keep exact-source reload support within the `msp.orms` package hierarchy and
  remove the legacy `tools.omniverse` import bootstrap.

## 0.1.20

- Keep mesh-assignment controls read-only while the runtime is stopped or
  failed, avoiding an implicit rebuild from a frozen state.
- Hide an empty material-feedback label until the first live result so it does
  not reserve unnecessary panel space.
- Keep genuine stage-load failures at Warning while routine trace traffic
  remains at Info.

## 0.1.19

- Add source-safe automatic mesh-assignment inspection and per-mesh
  Use-source, Allow, and Exclude controls on the Classifier tab.
- Explain lifecycle actions and the x1 fallback directly beside their controls.
- Add per-group and complete per-Set material resets with inline success and
  failure feedback.
- Add staged per-family, per-Set, and complete atlas reset actions.
- Replace the developer-oriented Extension Manager README with an artist-first
  setup, workflow, and troubleshooting guide.
- Author the mesh-scoped Interior Set diagnostic as a Fabric-safe constant
  scalar string primvar instead of a uniform string array.
- Route routine stage-load trace blocks to Info while retaining Warning for
  actionable anomalies.

## 0.1.18

- Count runtime materials in the per-Interior-Set hierarchy so renderer
  telemetry reports the generated material total instead of a false zero.

## 0.1.17

- Remove the developer-oriented Applied runtime diagnostics section from the
  Interior Atlases tab while retaining the full structured runtime log.
- Keep selector conflicts as concise actionable inline warnings because they
  directly affect Set ownership and priority configuration.

## 0.1.16

- Route every collapsible section on all three ORMS tabs through one
  content-sized layout helper so folded content releases its scroll height.
- Retain classifier, material Set, and nested material-group collapse state
  across safe UI rebuilds using stable semantic keys and Set UUIDs.
- Add a regression guard that prevents direct, stretching
  `CollapsableFrame` construction from returning to runtime UI modules.
- Give inactive tab and atlas-mode choices a lighter grey background while
  retaining a dark selected state, so the current choice is visible at a
  glance.

## 0.1.15

- Remove the arbitrary upper bound from Emission Strength while retaining its
  non-negative and finite-value validation.
- Place Add, Apply, and Revert immediately below Atlas mode so the structural
  transaction remains accessible above long Interior Set lists.
- Retarget the live camera bridge after every successful structural rebuild so
  newly added Set materials receive camera position without a manual Restart.

## 0.1.14

- Replace the profile path field and three-step action row with two direct
  actions: Save Profile opens a Save dialog and writes the selected path;
  Load Profile opens an Open dialog and stages the selected file.
- Match Kit file exporter's real keyword callback contract, including its
  named `selections` argument.

## 0.1.13

- Add portable, human-readable `.orms` scene profiles containing the applied
  Interior Set UUIDs, priority, selectors, production paths, atlas mode, and
  complete material profiles.
- Load profiles into staged draft state without changing persistent settings,
  Session Layer state, or runtime output until `Apply Interior Sets`.
- Add profile path, Browse, Load to Draft, Save Applied, and Save Applied As
  controls below the global packaged-debug paths.
- Validate profile schema, identities, selector syntax, material types/ranges,
  and file suffix before staging, and save through an atomic local-file replace.

## 0.1.12

- Preserve every Interior Set block's collapsed state by immutable Set UUID
  across Add, Duplicate, Remove, reorder, Apply, revert, and runtime refresh.
- Preserve the Atlas mode block state alongside the already retained
  diagnostics state.
- Surface applied selector conflicts above the collapsed diagnostics panel,
  including the matched prim path, competing Set labels, and priority winner.
- Include full selector-conflict ownership details in runtime phase logs.

## 0.1.11

- Preserve the diagnostics collapsed state across safe frame rebuilds and let
  collapsed atlas panels release their layout height.
- Commit Production mode with per-family packaged fallback when a configured
  atlas directory is absent or invalid, while retaining its visible error.
- Prevent the legacy source-material x1 atlas from overriding the selected
  Default Interior Set resource.

## 0.1.10

- Make the production atlas browser select directories rather than validating
  a stale filename inside the chosen folder.
- Open the browser at the complete current directory without populating its
  filename input from the directory's final path component.

## 0.1.9

- Add one staged global atlas mode: Debug forces packaged x1-x4 families for
  every classified window, while Production uses Set-local families with
  matching packaged debug fallbacks.
- Rehydrate runtime resource records across exact-source reload boundaries so
  stale Python class identities cannot be mistaken for filesystem paths.
- Use the supported Kit 1.1.21 file-importer callback contract for production
  atlas directory browsing.

## 0.1.8

- Preserve the active ORMS tab and rebuild only Frame content after structural
  edits, avoiding window destruction during OmniUI callbacks.
- Restore the independent global x1-x4 packaged debug paths and clarify that
  Default is an unconditional fallback rather than a selector target.
- Recognise semantic window meshes below a composed `windows` container while
  retaining the legacy `Windows_Glass` and explicit opt-in boundaries.

## 0.1.7

- Bootstrap the packaged Python runtime before importing the ORMS service so
  registry installations do not depend on a neighbouring source checkout.

## 0.1.6

- Add ordered Interior Sets with immutable UUID identity, composed-path
  selectors, per-Set x1-x4 atlas families, and complete material profiles.
- Stage structural UI edits behind `Apply Interior Sets` while retaining live
  Set-scoped material controls and presentation-only renaming.
- Validate cross-family semantic variant manifests, report selector/resource
  diagnostics, and preserve source USD through transactional Session Layer
  rebuilds and persistent-settings rollback.

## 0.1.5

- Replace the redundant production root, asset-pattern, and variant-count
  controls with one external atlas directory for each x1–x4 family.
- Discover the single UDIM sequence in each configured directory and derive
  its `<UDIM>` path and consecutive variant count automatically.

## 0.1.4

- Make in-process Extension Manager upgrades version-safe by evicting cached
  ORMS runtime modules that originate from an earlier installed package.
- Put the current runtime root first in `sys.path` and the existing
  `tools.omniverse` namespace package paths before loading stage, assignment,
  settings, or reload modules.

## 0.1.3

- Added explicit `Start`, `Restart`, `Stop`, and
  `Restore Original Asset` lifecycle controls to the ORMS window.
- `Stop` now freezes the current Session Layer result while releasing live
  USD and camera callbacks; `Start` resumes that same result.
- `Restart` performs a clean runtime rebuild, while restore removes both
  runtime and automatic-assignment Session Layers.

## 0.1.2

- Skip classifier and runtime authoring when the active stage contains no
  mesh bound to an ORMS source material.

## 0.1.1

- Added registry-ready package metadata and local filesystem publication.

## 0.1.0

- Added portable ORMS MDL, Python runtime, and packaged debug atlases.
- Added Material Library registration and reversible `Windows_Glass`
  assignment.
- Added the dockable ORMS settings window and local registry distribution.
