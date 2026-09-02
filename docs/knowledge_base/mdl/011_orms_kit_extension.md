# ORMS Kit Extension Integration

## Record

| Field | Value |
| --- | --- |
| Jira | KRM-91 |
| Implementation | `exts/msp.orms.runtime/`, `exts/msp.orms.runtime/msp/orms/runtime/lifecycle.py`, `exts/msp.orms.runtime/msp/orms/runtime/lifecycle_controls.py`, `exts/msp.orms.runtime/msp/orms/runtime/runtime_imports.py`, `exts/msp.orms.runtime/msp/orms/runtime/settings_window.py`, `tools/omniverse/runtime/assignment.py`, `tools/omniverse/runtime/resources.py`, `tools/omniverse/runtime/stage_visibility.py`, `tools/omniverse/shared_room/material_controls.py`, `tools/omniverse/shared_room/settings_panel.py`, `tools/package_orms_extension.py` |
| Automated evidence | `tests/kit_extension/`, `tests/kit_extension/lifecycle/`, `tests/kit_extension/runtime_imports/`, `tests/shared_room_runtime/runtime/test_assignment.py`, `tests/shared_room_runtime/runtime/test_resources.py`, `tests/shared_room_runtime/runtime/test_stage_visibility.py`, `tests/shared_room_runtime/shared_room/test_material_controls.py`, `tests/shared_room_runtime/room_run/test_classifier.py`, `tests/shared_room_runtime/shared_room/test_controller.py` |
| Validation assets | Empty Kit bootstrap stage; hydrated `assets/_external/usd/Moskovskiy_av_150/usd/Moskovskiy_av_150.usd`; `tests/building_150_runtime/test_room_map_building_150.usda` |
| Evidence state | KRM-91 accepted live on installed `msp.orms.runtime-0.1.5`: local-registry installation and AUTOLOAD, in-process upgrade, Material Library, Building 150, production and debug atlases, central settings, lifecycle controls, both RTX modes, and disable/re-enable teardown all passed |
| Last reviewed | 3 September 2026 |

## Purpose

KRM-91 turns the existing ORMS MDL and OpenUSD runtime into an installable Kit
extension. The task does not redesign the shader, the KRM-93 shared-room
classifier, or the KRM-98 Building 150 integration. It provides the product
boundary through which those accepted components can be discovered, assigned,
configured, started, and stopped inside a compatible Kit application.

The intended user path is:

1. install or expose the extension to Kit;
2. enable `msp.orms.runtime`;
3. find `Omniverse Room Map Shader` in the Material Library;
4. assign it manually to a valid ORMS mesh when required;
5. let the extension recognise eligible `Windows_Glass` meshes and apply ORMS
   by default;
6. use packaged public debug atlases or separately distributed production
   atlas families;
7. disable the extension and recover the source material bindings without
   rewriting the source USD.

The visible extension title is `Omniverse Room Map Shader`. The technical ID
remains `msp.orms.runtime` because it is already used by the Python package,
settings paths, tests, packaging, and launch commands. Removing `Runtime` from
the visible name therefore does not create an unnecessary identifier migration.

## Accepted contract

The items in this section are implemented and protected at source level. Live
acceptance remains limited to the states explicitly recorded under
`Validation record`.

### Extension responsibilities

The extension is deliberately split by ownership:

- `extension.py` is the minimal Kit `IExt` entry point;
- `service.py` owns lifecycle coordination, stage subscriptions, settings,
  startup ordering, and teardown ordering;
- `lifecycle.py` owns the runtime state machine and session transitions without
  importing Kit UI;
- `lifecycle_controls.py` owns only button presentation and delegates every
  command back to the service;
- `runtime_imports.py` owns versioned Python-module and namespace-path
  replacement during an in-process Extension Manager update;
- `resources.py` resolves source-checkout or packaged MDL content, bundled
  debug atlases, and separately configured production atlas families;
- `mdl_registration.py` owns portable MDL search-path registration and its
  symmetric cleanup;
- `material_visibility.py` owns the exact Material Library allow-list entry
  required by restrictive host applications;
- `material_library.py` composes MDL registration, Material Library
  registration, visibility, and teardown without taking ownership of stage
  assignment;
- `tools/omniverse/runtime/assignment.py` validates `Windows_Glass` meshes and
  owns only the reversible default material-binding opinions;
- the existing shared-room runtime continues to own classification, derived
  primvars, x1-x4 material families, diagnostics, and camera-dependent
  operation.

This separation keeps Kit UI integration, resource resolution, Session Layer
state, and shader/runtime behaviour independently readable and testable.

### Settings window and hidden runtime state

KRM-91 now provides one dockable `Window > ORMS` extension window with three
working
tabs:

- `ORMS Classifier` contains the existing room-family, composition, and
  geometric-tolerance settings;
- `Material Parameters` owns one persistent artist-facing value for every
  shared ORMS shader control;
- `Interior Atlases` displays the resolved packaged debug x1-x4 assets and
  provides one editable production-family directory for each of x1-x4.

The four x1-x4 materials are still distinct MDL instances because each atlas
family needs its own material and atlas binding. Their common artist controls
are no longer presented as four independent configurations. A material value
changed in the ORMS window is authored to every active family in the existing
runtime layer without reclassifying the building. Initial classification also
consumes the same persistent values, so a later runtime rebuild preserves the
central configuration.

The window is operational extension UI, so it is registered beneath Kit's
`Window` menu rather than injected into the host application's Preferences.
The values themselves remain persistent `carb.settings`; moving the surface
does not move them into USD or make them window-lifetime state. The window is
registered once for the extension lifetime and survives stage replacement,
while classifier and material callbacks target only the active stage runtime.

The `ORMS Classifier` tab also exposes the current runtime state and four
commands:

- `Start` creates a runtime for an inactive compatible stage or resumes a
  stopped session without rebuilding its Session Layer;
- `Restart` tears down the active runtime and rebuilds assignment,
  classification, materials, and camera integration from current settings;
- `Stop` releases live USD notices and camera updates while preserving the
  last authored runtime layer, material bindings, textures, and camera value;
- `Restore Original Asset` removes both ORMS-owned Session sublayers and
  reveals the unmodified source asset bindings.

The visible states are `Inactive`, `Running`, `Stopped`, and `Failed`. The UI
does not own these transitions: it only sends commands. `service.py`
coordinates stage and assignment ownership, while `lifecycle.py` owns the
active classifier/camera session. Extension shutdown remains a complete
teardown even when the artist previously used `Stop`.

Production atlas edits are applied only by the explicit
`Apply atlas configuration` button. Text entry therefore does not reactivate
the stage on every character. Applying the completed configuration performs
one controlled stage-runtime rebuild so resource validation and x1-x4 atlas
selection use the new paths. Atlas apply does not mutate a stopped or inactive
scene; `Restart` is the explicit resource-rebuild command in that state.

`/__ORMSAutoAssignment` and `/__ORMSRuntime` remain necessary implementation
prims inside removable anonymous Session sublayers: the first owns the
reversible seed binding and the second owns derived primvars, family materials,
and bindings. Removing those prims would remove lifecycle ownership, not just
UI clutter. Their roots now carry Kit's native `hide_in_stage_window` metadata,
so they do not appear in the ordinary Stage tree while the underlying runtime
composition remains intact. Enabling Kit's diagnostic `Show Hidden Prims`
option can reveal them when implementation-level inspection is required.

### Version-safe runtime imports

Installed ORMS packages keep the stable Python names beneath
`tools.omniverse.*` while their source directories are versioned by Extension
Manager. Kit invokes the previous extension's shutdown during an update, but
Python can retain those module objects and namespace-package paths in the same
process. Merely prepending the new `data/runtime` directory to `sys.path` does
not replace a module already present in `sys.modules`.

`runtime_imports.py` now establishes the import boundary before settings,
assignment, stage inspection, or the runtime loader is imported. It:

- identifies only ORMS-owned modules whose source belongs to a different
  runtime root;
- removes those module identities and matching parent-package attributes;
- removes stale installed ORMS roots from `sys.path` and namespace
  `__path__` values;
- places the current runtime and package directories first;
- retains modules already loaded from the current runtime root.

It deliberately does not repeat lifecycle teardown. The outgoing service owns
callbacks and Session Layers and is shut down by Kit before the new extension
starts; the import boundary owns only stale Python identity and search paths.

### Resource and distribution zones

The extension recognises two texture zones:

- public labelled x1-x4 debug atlases belong under
  `data/atlases/debug/` in a packaged extension;
- full production atlas libraries do not live in the extension or public
  repository and are addressed through four persistent per-family
  `/persistent/exts/msp.orms.runtime/atlases/xN/directory` settings.

In a source checkout, `ResourceLayout` resolves the canonical `src/mdl/`
modules and hydrated debug atlas directories without duplicating them. The
standalone package builder copies only runtime Python, canonical MDL modules,
and the four public debug families. It does not package building assets,
production Room Map atlases, Houdini authoring files, or unrelated repository
content.

Each configured production directory must exist and contain exactly one UDIM
sequence with consecutive tiles beginning at `1001`. ORMS derives the
`<UDIM>` asset pattern and variant count from those files. A blank family path
retains that family's packaged debug atlas. An incomplete or ambiguous
configured directory rejects the production configuration and returns to the
complete debug set with a warning rather than producing a partially resolved
material.

### Material Library entry

On startup the extension registers:

| Field | Value |
| --- | --- |
| Display name | `Omniverse Room Map Shader` |
| Group | `ORMS` |
| MDL source asset | `room_map.mdl` |
| MDL subidentifier | `room_map` |

Some Kit applications restrict the Create Material menu through
`/exts/omni.kit.material.library/ui_show_list`. An empty list already exposes
all materials and must remain untouched. When the list is restrictive and no
existing wildcard or exact entry matches ORMS, `MaterialVisibilityOwner` adds
only `Omniverse Room Map Shader`. On stop it removes only the exact entry it
added and preserves host changes made while ORMS was active.

The extension does not force a synchronous Material Library menu refresh during
early application startup. Material Library 3.1.2 can be asked for its material
list before `mdl_list_cache` is complete, which reaches a vendor code path with
an uninitialised `is_private` local. ORMS instead relies on the Material
Library source-asset setting subscription and its normal application-ready or
asynchronous rebuild path.

### Portable MDL registration

Kit 110.1.2 normally registers extension MDL content by creating hard links in
`${omni.mdl}/search_paths/omniverse_exts`. A Windows drive letter is not enough
to prove that two paths share a filesystem. The current source checkout and
Kit build root both appear below the same drive letter but report different
`os.stat(...).st_dev` values, so a hard link is invalid.

`mdl_registration.py` therefore uses this policy:

- when source and target `st_dev` values match, delegate to
  `omni.mdl.neuraylib.register_extension_content`;
- when they differ, materialise managed copies beneath Kit's extension-owned
  MDL search root;
- track the exact registered files;
- on stop, delete only registered paths that remain beneath the resolved Kit
  search root and remove only empty child directories;
- never require the repository to move beside the Kit build and never require
  Windows Developer Mode or elevated symlink privileges.

### Default Windows Glass assignment

The automatic pass examines composed `UsdGeom.Mesh` prims whose own name
normalises to `WindowsGlass`. A source material with the same normalised name
remains a compatibility identity for older assets, but mesh identity is the
primary production contract because Building 150 inherits the generic
`base_lod00_mat`. It skips materials that already use the ORMS source asset. A
mesh is eligible only when:

- `roomID`, `roomP`, `tangentu`, `tangentv`, and `roomUV` are present;
- every face is a quad;
- `orms:autoAssign` is not explicitly authored as `false`.

The default binding and seed material live in an anonymous ORMS-owned sublayer
beneath the stage Session Layer. The shared-room runtime then publishes its own
`/__ORMSRuntime` state and x1-x4 family materials. Disabling the extension
removes both owned runtime state and the auto-assignment layer, revealing the
original source bindings.

The persistent setting
`/persistent/exts/msp.orms.runtime/autoAssignWindowsGlass` defaults to `true`.
The per-prim exclusion attribute is part of the accepted backend contract.

### Lifecycle and packaging

Startup must complete in this order:

1. resolve source-checkout or packaged resources;
2. register resolvable MDL content;
3. expose ORMS through any restrictive Material Library allow-list;
4. register the Material Library source-asset entry;
5. install stage-open and stage-close subscriptions;
6. activate auto-assignment for the current stage and start the shared-room
   runtime only when the composed stage contains a mesh bound to an ORMS source
   material.

Shutdown reverses owned state: stop the stage runtime, detach the assignment
layer, release stage subscriptions, restore Material Library visibility,
remove the Material Library entry, and deregister linked or copied MDL content.
Source USD layers and external production packs remain outside this lifecycle.
Artist `Stop` is deliberately narrower than shutdown: it pauses the classifier
and camera bridge but retains their owned Session Layer. Artist restore is
deliberately stage-scoped: it removes runtime and assignment state without
uninstalling the extension or its Material Library registration.

## Evidence

### Retained implementation

The current vertical slice includes:

- an installable `exts/msp.orms.runtime/config/extension.toml` manifest;
- a visible title without `Runtime` while retaining the stable technical ID;
- checkout and packaged resource discovery;
- x1-x4 debug atlas and external production-root selection;
- portable same-filesystem link and cross-filesystem copy registration;
- reversible Material Library allow-list ownership;
- a Material Library source-asset entry for `room_map.mdl::room_map`;
- one dockable three-tab ORMS window with central material and atlas settings;
- a separate lifecycle state machine and state-aware command controls;
- frozen-session resume, clean restart, and source-asset restoration paths;
- live central material fan-out to x1-x4 without classifier restart;
- hidden Stage-window presentation for both ORMS implementation roots;
- valid `Windows_Glass` evaluation decisions and reversible Session Layer
  assignment;
- stage lifecycle integration with the existing shared-room runtime;
- a deterministic standalone extension package builder.

### Automated evidence

The initial KRM-91 source-level vertical slice completed 42 focused tests. The
latest registration and visibility correction set completes 11 focused tests
covering:

- same-filesystem delegation to Kit MDL registration;
- cross-filesystem managed copies;
- cleanup confinement to Kit's MDL search root;
- exact Material Library registration and removal;
- restricted, unrestricted, and wildcard Material Library filters;
- preservation of host filter changes during ORMS ownership;
- extension manifest title and dependency declarations.

The final repository-wide quality gate is deliberately reserved for the
pre-commit boundary.

The settings-window and room-family correction completes 31 focused tests.
They cover the `Window > ORMS` contract, direct scalar and item-model
callbacks, separation of debug and production atlas settings, live material
fan-out without reclassification, x4-to-x1 fallback, runtime source loading,
and the extension manifest's menu and settings-widget dependencies. Earlier
focused sets also cover typed persistent vectors and both hidden implementation
roots.

### Live evidence retained so far

After the cross-filesystem correction, Kit 110.1.2 recorded:

```text
[ORMS] MDL source and Kit search paths use different filesystems;
materialising managed copies instead of hard links
Registering MDL using USD Source Asset: room_map.mdl Sub-Identifier: room_map
[ORMS] Runtime extension started
[ext: msp.orms.runtime-0.1.0] started
```

The earlier empty bootstrap stage reported:

```text
[ORMS] Windows Glass auto-assignment: assigned=0, examined=0
```

This proved extension discovery, dependency resolution, Python startup,
portable MDL registration, and source-asset registration, but the subsequent
zero-mesh classifier run was unnecessary. Version `0.1.2` now keeps extension
registration and the ORMS window alive while skipping classifier and runtime
authoring until auto-assignment or an existing binding exposes a mesh using
`room_map.mdl` or `room_map_single.mdl`. The gate is based on composed USD
content rather than the private `World0.usd` identifier, so enabling ORMS over
an already open compatible building still activates the runtime.

The obsolete `msp.orms.stage_load_probe` package was subsequently removed
from the Blackwell Rig Viewer dependencies and extension search surface. It
duplicated the runtime-owned diagnostic observer, referenced its retired
pre-refactor source path, and exposed an internal R&D tool as a user-facing
extension. Stage-load diagnostics remain owned internally by
`msp.orms.runtime` and no longer require a second Extension Manager entry.

The 20:23 Building 150 run in the latest retained log is clean: the extension
started in 114 ms, the USD opened in 0.04 seconds, automatic assignment found
one eligible `Windows_Glass` mesh, and the single building classification
submitted in 1.906 seconds. It extracted 232 apertures and authored x1=98,
x2=33, x3=12, and x4=8 groups. No Python, MDL, or ORMS error followed. The
visible x4 checkbox edit produced no `trigger=settings_change` record, proving
that the old Preferences event bridge did not notify the runtime.

## Reproduction

### Implementation plan and current status

| Step | Status | Acceptance evidence |
| --- | --- | --- |
| 1. Define extension identity and module ownership | Complete | Manifest, minimal entry point, lifecycle service, and separate resource/material/assignment owners exist. |
| 2. Separate debug and production texture zones | Live accepted | Packaged debug x1-x4 families passed; installed `0.1.5` discovered the external x1 production sequence as `room_map.<UDIM>.png` with 56 variants while x2-x4 retained their eight-variant debug families. |
| 3. Register MDL content portably | Live startup accepted | The initial hard-link failure is replaced by tested `st_dev` routing and managed-copy cleanup. |
| 4. Add the ORMS Material Library entry | Live create-and-bind accepted | The `ORMS` group is visible, the material is created beneath `/World/Looks`, the selected mesh receives its binding, and a plain mesh retains the visible magenta fallback. |
| 5. Add reversible `Windows_Glass` assignment | Live accepted | Source Building 150 produced `assigned=1`, `examined=1`, and `windows_glass_contract_valid`; the binding remained Session-layer-owned. |
| 6. Integrate the supported stage lifecycle | Live accepted | Empty-stage suppression, compatible-stage activation, `Start`, frozen `Stop`, clean `Restart`, source restore, stage replacement, disable/re-enable, and non-duplicating reactivation passed in installed Kit. |
| 7. Build and publish a relocatable extension package | Live accepted | `msp.orms.runtime-0.1.5` passed Kit verification, was published to the v2 local registry, installed through Extension Manager, and started through AUTOLOAD without command-line extension arguments. |
| 8. Consolidate the ORMS window and hide implementation roots | Live accepted | `Window > ORMS`, all three tabs, direct callbacks, central x1-x4 material fan-out, explicit atlas apply, and hidden implementation roots passed in installed Kit. |
| 9. Validate both RTX modes and teardown | Live accepted | Building 150 passed camera-following parallax, orientation, material stability, RTX Real-Time, RTX Interactive Path Tracing, source restore, clean disable, and duplicate-free re-enable. |

### Accepted live validation — 2–3 September 2026

Kit 110.1.2 accepted the full required sequence below on the installed
`msp.orms.runtime-0.1.5` package. The package was verified, published to the
local filesystem registry, installed through Extension Manager, and retained
through AUTOLOAD. Its archive contains runtime Python, MDL, x1-x4 debug
atlases, lifecycle modules, the version-safe import boundary, and the
four-folder production contract without production atlases or building
assets. The publisher removed its temporary
`release/exts/msp.orms.runtime` staging directory after publication.

The live `0.1.4` to `0.1.5` update removed nine cached modules rooted in the
previous installed runtime and loaded classifier, camera, and diagnostic code
from `0.1.5`. Building 150 produced one initial `manual_start` classification
for all 232 apertures. Three later `settings_change` runs were deliberate x2,
x3, and x4 family toggles: group counts changed from 151 to 184, 208, and 232,
confirming local fallback to x1 rather than renderer-triggered repetition.

The x1 production folder resolved to `room_map.<UDIM>.png` with 56 variants;
x2-x4 retained packaged debug atlases with eight variants each. No invalid
production configuration, unresolved texture, Python exception, MDL error, or
extension-startup failure followed. The artist also confirmed parallax and
material stability in RTX Real-Time and RTX Interactive Path Tracing, full
source restoration, clean disable, and duplicate-free re-enable. Invalid or
ambiguous production folders retain source-level regression coverage; the
accepted live path used valid content.

1. Publish ORMS from the repository root with
   `python tools/publish_orms_local_registry.py --kit-app-root <kit-app>`.
   Launch the Kit application normally, without `--ext-folder` or `--enable`.
2. In Extension Manager, find `Omniverse Room Map Shader`, press `INSTALL`,
   enable it, and select `AUTOLOAD`. Restart once and confirm ORMS starts
   without command-line extension arguments.
3. Confirm the managed-copy message, Material Library source-asset
   registration, successful extension startup, and no ORMS traceback.
4. Confirm Extension Manager exposes `msp.orms.runtime` without a separate
   `ORMS Scene Load Probe` entry.
5. Open `Create > Material` and confirm the `ORMS` group and
   `Omniverse Room Map Shader` entry after Material Library reaches its ready
   state.
6. On a disposable stage, create a plain mesh and bind the material. Confirm
   the menu action, `/World/Looks` authoring, MDL source asset, and
   subidentifier. The mesh must remain visible with the magenta invalid-frame
   fallback; disappearance is a failed safety check, not accepted behaviour.
7. Treat the plain-mesh check only as Material Library and fail-safe evidence.
   It cannot demonstrate Room Map rendering because it has no source primvars.
8. Open `Window > ORMS`. Confirm that one dockable ORMS window opens with the
   `ORMS Classifier`,
   `Material Parameters`, and `Interior Atlases` tabs and that switching tabs
   neither closes the window nor changes the stage. Confirm that ORMS is no
   longer listed in `Edit > Preferences`.
9. Open the hydrated Building 150 source USD rather than the wrapper that
   already overrides `Windows_Glass`. Without using Script Editor, confirm
   `assigned=1`, `examined=1`, and the `windows_glass_contract_valid` decision.
   Confirm that neither `__ORMSAutoAssignment` nor `__ORMSRuntime` appears in
   the ordinary Stage tree.
10. Confirm the lifecycle status reads `Running`, then test the four commands:
    - press `Stop`, move the viewport camera, and confirm the last rendered
      room state remains frozen with no new camera or classifier updates;
    - press `Start` and confirm the same runtime layer resumes without a new
      source reload;
    - press `Restart` and confirm one clean teardown and rebuild from current
      settings;
    - press `Restore Original Asset` and confirm both ORMS-owned layers are
      removed and the original `Windows_Glass` binding returns; then press
      `Start` to activate ORMS again.
11. In `ORMS Classifier`, clear `Enable x4 rooms`. Confirm exactly one new
   classifier run with `trigger=settings_change`; its subsets must list only
   x1, x2, and x3, while the four available materials remain alive. Windows
   previously classified as x4 must use x1 rather than retaining x4. Restore
   the checkbox and confirm one run restores the x4 subset without destroying
   or recompiling the x4 material.
12. In `Material Parameters`, change `Glass > Roughness`. Confirm the visible
   windows update and the log contains no new classifier run caused by that
   material edit. Reopen the ORMS window and confirm the value persisted.
13. In `Interior Atlases`, confirm four read-only packaged debug paths and four
   editable production folders. Enter the directory containing the real x1
   sequence `room_map.1001.png` through `room_map.1056.png`, then press
   `Apply atlas configuration` once. Confirm ORMS derives
   `room_map.<UDIM>.png`, reports 56 variants, uses production x1, and retains
   debug x2-x4. A missing tile or a second sequence in the same directory must
   warn and fall back to the complete debug set.
14. Optionally enable Kit's `Show Hidden Prims` diagnostic setting and inspect
   `RoomMapX1` through `RoomMapX4`; disable it again for the normal workflow.
15. Validate camera-following parallax, orientation, stable room grouping, and
   absence of error materials in RTX Real-Time and RTX Interactive Path
   Tracing.
16. Disable the extension and confirm removal of ORMS-owned runtime roots,
   restoration of source `Windows_Glass`, absence of source-layer dirtiness,
   Material Library removal, and MDL registration cleanup.
17. Re-enable the extension, open another stage, and confirm that assignments,
   callbacks, Material Library entries, and runtime roots are not duplicated.

## Validation record

### Live issue chronology — 2 September 2026

#### 1. Extension Manager reported a dependency failure

The first visible symptom was a red Extension Manager state and the tooltip
`Failed to solve extension dependency`. The detailed log showed that
`omni.usd`, `omni.mdl.neuraylib`, and `omni.kit.material.library` had resolved
and started. The actual failure happened inside ORMS Python startup when
`register_extension_content` attempted its first MDL hard link.

The source checkout and Kit MDL search directory exposed different `st_dev`
values even though their paths shared a Windows drive letter. `mklink /h`
therefore failed with the cross-volume error and Kit returned an empty
registration list. `MaterialLibraryRegistration` then raised
`Could not register the ORMS MDL content path`.

The correction introduced `mdl_registration.py`, with official hard links on
one filesystem and managed copies across filesystems. Cleanup is constrained
to the resolved Kit MDL search root. The next live run started the extension in
33 ms without the previous registration error.

#### 2. The visible extension name contained `Runtime`

The manifest initially exposed `Omniverse Room Map Shader Runtime`. The visible
title is now `Omniverse Room Map Shader`. The technical ID remains unchanged to
avoid breaking settings, package imports, tests, and launch commands.

#### 3. The Material Library backend registered ORMS but the menu hid it

The successful startup log contained the expected source-asset registration,
but `Create > Material` showed only the application's standard entries. The
host application defines a restrictive `ui_show_list` containing OmniPBR,
OmniGlass, OmniSurface, USD Preview Surface, and OpenPBR Surface. Material
Library applied that filter after accepting the ORMS backend entry.

The correction introduced `MaterialVisibilityOwner`. It recognises empty
allow-lists and matching wildcards, appends the exact ORMS display name only
when required, and removes only its own addition during teardown.

#### 4. An explicit early menu refresh reached a Kit vendor bug

The first visibility correction also called
`material_list_refresh()` synchronously during ORMS startup. At that point
Material Library 3.1.2 had not completed `mdl_list_cache`. Kit first warned:

```text
get_mdl_list: mdl_list_cache is not complete
```

It then failed inside its own `get_material_list` implementation:

```text
UnboundLocalError: cannot access local variable 'is_private'
where it is not associated with a value
```

The stack confirmed that ORMS called the refresh from
`material_library.py::start` before the Material Library cache was ready. The
current correction removes the synchronous refresh. Registering or removing
the USD source-asset entry already changes Material Library's observed setting;
Kit can rebuild through its own application-ready or asynchronous reload path.

This correction passes the 11 focused registration and visibility tests. A
clean Kit restart subsequently confirmed the `ORMS` group, the
`Omniverse Room Map Shader` entry, material creation beneath `/World/Looks`,
and binding to the selected mesh.

#### 5. A plain validation Plane disappeared after manual assignment

The Material Library smoke test originally said to assign ORMS to any prim but
did not distinguish create-and-bind evidence from functional Room Map output.
The selected `/World/Plane` and its material remained in the stage, and the log
confirmed the binding and connected MDL outputs without compiler or RTX
errors. The runtime correctly extracted zero apertures because the plain mesh
had none of the required `roomID`, `roomP`, `tangentu`, `tangentv`, or `roomUV`
primvars.

The mesh nevertheless should have remained renderable through the documented
magenta invalid-frame fallback. `room_map.mdl` selected `fallback_colour` for
the invalid mapping but still evaluated physical aperture cutout with default
runtime inputs. For a Plane at the origin this produced zero cutout opacity and
removed the whole mesh from the viewport.

The correction makes cutout fail open whenever `frame_is_valid` is false.
Invalid manually bound meshes therefore remain opaque and diagnostic, while
valid ORMS mappings retain the existing physical, front-exit, and depth-slice
cutouts. Stage extraction now also emits `MISSING_SOURCE_PRIMVARS` with the
missing names instead of silently skipping such a manually bound mesh.

#### 6. Building 150 was not assigned automatically

The first Building 150 source-stage run reported `assigned=0, examined=0` even
though the runtime snapshot already contained all 29 production meshes. The
detector incorrectly treated the bound material name as the only Windows Glass
identity. In the production asset the mesh is
`/Moskovskiy_av_150/geo/render/Windows_Glass`, while all 29 meshes inherit
`/Moskovskiy_av_150/mtl/base_lod00_mat`.

The extension therefore started its classifier correctly but authored no seed
binding, leaving zero apertures and zero runtime materials. Restarting the
standalone development loader from Script Editor after a manual binding made
the result visible, but that is not an acceptable extension workflow.

The correction recognises the mesh prim name first and retains material-name
recognition only for compatibility. Auto-assignment still requires all five
source primvars, quad topology, and no explicit exclusion. Its structured log
now includes each examined prim and decision reason. Focused coverage opens
the actual Building 150 source USD, identifies exactly one candidate, applies
the reversible Session Layer binding over inherited `base_lod00_mat`, exposes
all 232 apertures to the runtime, and restores the source binding on stop. A
separate controller regression proves that a later manual ORMS binding also
reclassifies without runtime reload or Script Editor.

The clean extension run on Building 150 subsequently accepted this workflow:
the extension reported one `windows_glass_contract_valid` decision, authored
the automatic binding, and produced the expected x1-x4 debug result without a
Script Editor bootstrap.

#### 7. Kit renderer resyncs repeatedly restarted the classifier

The first successful automatic Building 150 run still took roughly a minute
to settle. The stage itself opened in `0.01 s`, assignment followed in about
`0.13 s`, and the first complete ORMS run took about `2.09 s`. The classifier
then ran approximately 26 unnecessary additional times while Kit created and
updated renderer-owned prims such as:

```text
/OmniKit_Viewport_LightRig
/Render
/Render/OmniverseKit/HydraTextures
/Render/OmniverseKit/HydraTextures/omni_kit_widget_viewport_ViewportTexture_0
```

The notice filter ended with a permissive rule that accepted every resynced
prim not rejected earlier. It therefore treated renderer housekeeping as an
ORMS geometry invalidation and repeatedly classified all 232 apertures and
submitted all four MDL materials.

The correction replaces that fallback with an explicit dependency boundary.
Resyncs are accepted only when they can affect an established ORMS source
mesh, its building hierarchy, or its bound source-material network. The
extraction contract retains source mesh and material paths even when a bound
mesh is missing required primvars, so later corrective edits can still enter
classification. A newly bound ORMS mesh is also recognised without requiring
a runtime reload. Unrelated renderer topology, primvars, bindings, materials,
and resyncs remain outside classifier ownership.

Focused change-filter, controller, extraction, pipeline, and authoring tests
pass. The accepted `0.1.5` Building 150 log later confirmed one initial
`manual_start` classification. Its three subsequent runs were explicit
`settings_change` family toggles rather than viewport or renderer resyncs.

#### 8. Runtime implementation scopes polluted the artist Stage tree

The first successful Building 150 run exposed both
`/__ORMSAutoAssignment` and `/__ORMSRuntime` as ordinary top-level Stage
folders. They were not duplicate user configurations: one scope owned the
reversible source-material override and the other owned generated classifier
state. Nevertheless, showing them as normal scene content incorrectly made
internal lifecycle state part of the artist workflow and exposed four copies
of settings that should be controlled once.

The correction keeps both anonymous-layer scopes but marks their roots with
Kit's `hide_in_stage_window` metadata. Common shader parameters now live under
the `Material Parameters` tab in the ORMS window and fan out to all active x1-x4
families without classification. Texture locations live under
`Interior Atlases`, with resolved debug paths separated from editable
production directories. Focused tests pass, and the installed `0.1.5`
acceptance subsequently confirmed the three tabs, hidden roots, live material
update, and explicit atlas apply.

#### 9. The x4 checkbox changed visually but did not reach the runtime

The earlier Preferences surface correctly persisted the visible checkbox but
its settings subscription emitted no `trigger=settings_change` record. As a
result, unchecking `Enable x4 rooms` left both the x4 material and all existing
x4 groups untouched. This was a UI-to-runtime notification failure, not an MDL
or renderer failure.

The correction moves the controls into the dockable `Window > ORMS` surface
and subscribes directly to the scalar and item models returned by Kit's
settings widgets. Classifier edits are coalesced into one reclassification;
material edits still fan out without classification. Geometry classification
now establishes stable natural x1-x4 groups first. Any disabled or unavailable
x2-x4 group degrades locally to x1, so disabling x4 cannot silently retain x4
or repartition neighbouring windows into a different multi-window family.
Focused window, classifier, controller, loader, and manifest tests pass. Live
Kit acceptance subsequently confirmed one run per explicit family edit and
the expected local fallback to x1.

#### 10. Re-enabling x4 exposed the building interior

The first live callback correction proved that the classifier and subset
authoring were correct, but disabling x4 also removed its MDL material. The
log then recorded `Destroying MdlShadeNode` for `RoomMapX4/Shader`. Re-enabling
x4 rebound 32 faces while RTX was recreating and loading that material, so the
cutout-enabled faces rendered transparent and exposed the building interior.

The correction keeps one material for every available atlas family alive for
the full stage-runtime lifetime. Family checkboxes now change classification
and subset indices only. They do not add or remove MDL materials. This retains
the central four-family material configuration and avoids renderer compilation
gaps during x1-x4 UI changes.

The installed acceptance toggled x2, x3, and x4 in sequence. Group counts
changed from 151 to 184, 208, and 232 without destroying the four live
materials or exposing the building interior.

#### 11. AUTOLOAD classified the empty Kit bootstrap stage

The first installed-registry restart correctly started ORMS through AUTOLOAD,
but `service.start()` treated every non-null `omni.usd` stage as user content.
Kit had already created an anonymous empty `World0.usd`, so ORMS ran the full
classifier lifecycle with zero meshes and zero material families before the
user opened Building 150.

Version `0.1.2` adds a composed-stage capability gate in the shared-room stage
boundary. Auto-assignment may first bind an eligible `Windows_Glass` mesh; the
classifier then starts only when at least one mesh is bound to
`room_map.mdl` or `room_map_single.mdl`. An empty or unrelated stage keeps the
extension, Material Library entry, settings window, and stage subscriptions
alive without creating runtime USD state. Detailed diagnostic tracing remained
enabled through KRM-91 acceptance as a non-blocking troubleshooting facility.

#### 12. Extension enablement had no explicit stage-runtime controls

The installed extension previously started automatically and offered settings,
but the artist could not deliberately freeze, resume, rebuild, or remove ORMS
from the current asset without disabling the whole extension. Reusing the
existing teardown for `Stop` would have been incorrect because it removes the
runtime Session Layer and restores the source binding rather than retaining
the last calculated window state.

Version `0.1.3` separates lifecycle logic from both the service and OmniUI.
`lifecycle.py` owns session state and transitions; `lifecycle_controls.py`
owns the visible controls; `service.py` coordinates full activation and the
independent assignment layer. `SharedRoomClassifier` and
`CameraPositionBridge` now expose symmetric pause/resume operations. Focused
tests prove that pause releases subscriptions without detaching the runtime
layer, resume reuses the same classification, and restore performs teardown
exactly once. Installed `0.1.4` and `0.1.5` runs subsequently accepted all four
commands and full disable/re-enable teardown.

#### 13. Updating 0.1.1 to 0.1.3 reused the old Python runtime

Extension Manager successfully installed `msp.orms.runtime-0.1.3` and started
its new `service.py`, but startup imported
`tools.omniverse.shared_room.stage` from the still-cached `0.1.1` package. The
traceback proved the mixed-version process explicitly:

```text
ImportError: cannot import name 'stage_has_room_map_source_mesh'
from .../msp.orms.runtime-0.1.1/data/runtime/tools/omniverse/shared_room/stage.py
```

`stage_has_room_map_source_mesh` was introduced after `0.1.1`, so the new
service failed before its exact-source runtime loader could replace the old
module. The same boundary also applied to assignment, settings, and loader
modules. The outgoing runtime cleanup stopped lifecycle callbacks but did not
remove module objects from `sys.modules`; the incoming service only prepended
its new runtime root to `sys.path`, which cannot replace an already-imported
module. Repeated enable attempts therefore produced the same startup failure.

The garbled Russian lines around MDL registration represented successful
`Created hard link` messages, not the cause. Material Library rebuild warnings
were consequences of each failed startup and cleanup cycle.

Version `0.1.4` introduces the extension-local `runtime_imports.py` boundary
described above. Its regression fixture models `0.1.1` and `0.1.4` installed
roots in one Python process, verifies removal of the old module and package
paths, imports the current source, and separately proves that a current-version
module is retained. A complete Kit restart remains a workaround for `0.1.3`,
but must not be required after updating to `0.1.4`.

The live 2 September update from `0.1.3` to `0.1.4` then exercised that exact
boundary in one Kit process. The incoming service reported removal of nine
cached modules rooted in the installed `0.1.3` runtime, loaded classifier,
camera, and probe modules from `0.1.4`, automatically assigned Building 150,
and classified all 232 apertures. `Stop`, `Restart`, `Restore Original Asset`,
and `Start` completed without Python, MDL, or extension-startup errors.

#### 14. Production atlas settings exposed packaging details

The first `Interior Atlases` form required a common production root, a relative
`<UDIM>` asset pattern, and a manually entered variant count for every room
family. Those values describe runtime implementation rather than an artist's
choice, and the empty root field gave no useful way to select separately
distributed x1-x4 content.

Version `0.1.5` replaces that contract with four persistent production-folder
fields, one for each x1-x4 family. Each folder must contain exactly one
continuous UDIM sequence beginning at `1001`. `resources.py` derives the
`<UDIM>` pattern and variant count from the files, while a blank field retains
the packaged debug family of the same size. Source validation resolves the
hydrated x1 `room_maps` directory as `room_map.<UDIM>.png` with 56 variants;
installed `0.1.5` then accepted the same production family while retaining
eight-variant packaged debug fallbacks for x2-x4.

### Current troubleshooting summary

| Symptom | Actual cause | Current correction | State |
| --- | --- | --- | --- |
| Extension Manager suggested an unresolved dependency | MDL hard-link creation crossed filesystems after dependencies had resolved | Route by `st_dev`; use managed copies with confined cleanup when links are impossible | Live startup accepted |
| Visible title included `Runtime` | Manifest display title used an implementation-oriented name | Visible title changed; stable extension ID retained | Accepted live in Extension Manager |
| ORMS missing from `Create > Material` | Host `ui_show_list` filtered out the registered display name | Reversible allow-list owner adds the exact ORMS name only when required | Live menu accepted |
| `get_mdl_list` cache warnings followed by `UnboundLocalError` | ORMS forced a synchronous menu rebuild before Material Library readiness | Remove early refresh and rely on the library's own observed-setting rebuild | Live startup and menu accepted |
| Plain mesh disappeared after manual ORMS assignment | Invalid mapping selected the fallback colour but still ran physical cutout with default runtime inputs | Invalid frames now fail open with opacity 1.0; extraction reports missing source primvars | Live fallback accepted in RTX Real-Time |
| Building 150 produced `assigned=0, examined=0` | Detector matched only the inherited material name, while production identity is the `Windows_Glass` mesh prim | Match mesh identity first, retain material identity for compatibility, and log decision reasons | Live automatic assignment accepted without Script Editor |
| Building 150 took roughly a minute to settle | The notice filter accepted every unknown resync, including Kit `/Render` and viewport housekeeping | Track source geometry and material dependencies; reject resyncs outside that boundary | Accepted live: one initial run; later runs matched explicit settings edits |
| Two ORMS implementation folders appeared as artist scene content | Reversible assignment and generated material state used necessary top-level Session-layer scopes without Stage-window hiding | Hide both roots with Kit metadata; expose one central material configuration and atlas locations in the three-tab ORMS window | Accepted live |
| Clearing `Enable x4 rooms` changed the checkbox but not the building | The former Preferences subscription did not deliver a live settings callback; geometry grouping also needed an explicit family fallback policy | Direct Kit model callbacks; one debounced reclassification; disabled x2-x4 groups degrade locally to x1 | Accepted live |
| Re-enabling x4 exposed the building interior | Disabling x4 destroyed its MDL material; re-enabling rebound faces while RTX recreated the cutout material | Keep all available atlas-family materials alive; toggle only classification and subset indices | Accepted live |
| AUTOLOAD ran ORMS against empty `World0.usd` | Startup activated every non-null Kit stage before user content was opened | Require a composed mesh bound to an ORMS source material before starting classifier/runtime authoring | Accepted live |
| No explicit start, frozen stop, restart, or source restore commands | Extension lifetime and current-stage runtime lifetime were exposed as one operation | Separate state machine, UI controls, component pause/resume, clean rebuild, and removal of both owned Session Layers | Accepted live through `0.1.5` |
| Updating the enabled extension loaded `0.1.3` service with `0.1.1` runtime modules | Shutdown stopped callbacks but retained versioned `tools.omniverse.*` identities and package paths in the same Python process | Replace only modules from another ORMS runtime root before any runtime import; prioritise current namespace paths | Live in-process update accepted in `0.1.4` |
| Production atlas form required root, pattern, and count internals | UI exposed redundant packaging details instead of the four artist-selected family locations | Four x1-x4 folder settings with automatic UDIM pattern and count discovery | Accepted live in installed `0.1.5` |
| Repeated `ROOM MAP SCENE LOAD PROBE` warnings | Runtime diagnostic tracing uses warning-visible records during integration validation | Remove the obsolete standalone probe extension while retaining the runtime diagnostic records | Accepted, non-blocking diagnostic behaviour |

## Boundary

KRM-91 is complete. The installed local-registry extension passed AUTOLOAD,
Material Library creation and binding, invalid-frame fallback, automatic
assignment, hidden Session-layer state, direct settings callbacks, debug and
production atlas routing, both required RTX modes, version-safe in-process
upgrades, all four lifecycle controls, source restoration, stage replacement,
and clean disable/re-enable without duplicated runtime ownership.
