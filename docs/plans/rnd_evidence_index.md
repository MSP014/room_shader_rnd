# R&D Evidence Index

## Purpose

This document is the chronological evidence map for the Room Map Shader R&D.
It records what each completed stage established, where its reproducible result
is stored, and which artefacts can support a future technical breakdown,
presentation, or screen capture.

The index distinguishes between three evidence levels:

- **Renderer-validated**: observed in USD Composer in RTX Real-Time and RTX
  Interactive (Path Tracing).
- **Static contract**: checked through source, USD, or Python contract tests,
  but not a substitute for renderer validation.
- **Documented reference**: research findings or architecture decisions without
  a self-contained live capture scene in this workspace.

Paths under `assets/_external/` are local hydrated assets and are ignored by
Git. Confirm that they are present before recording. Public captures and their
diagnostic atlas copies are retained under `docs/img/`.

## Completed Stages at a Glance

| Stage | Jira | Result | Primary evidence |
| --- | --- | --- | --- |
| 1. Building 150 baseline | Project baseline | Established the Case 01 source asset and flat-window starting point | `assets/_external/usd/Moskovskiy_av_150/usd/Moskovskiy_av_150.usd` |
| 2. Houdini room-frame analysis | KRM-79 | Identified the geometry frame and grouping contract | `docs/knowledge_base/houdini/room_map_frame_sop.md` |
| 3. Houdini material and USD workflow analysis | KRM-80, KRM-81, KRM-82 | Recorded the reference atlas, material, binding, and baking workflow | `docs/knowledge_base/houdini/karma_room_map_workflow.md` |
| 4. Native MDL strategy | KRM-83, KRM-84 | Defined a clean native PIM architecture and translation boundary | `docs/adr/007-vop-to-mdl-parallax-logic.md` |
| 5. First hand-authored MDL material | KRM-85 | Proved MDL module resolution and USD material binding | `assets/_external/usd/hello_world_material.usda` |
| 6. MDL state-function diagnostics | KRM-86 | Established usable state values and rejected `state::direction()` as the view vector | `assets/_external/usd/test_grid/state_diagnostics.usda` |
| 7. Active-camera runtime bridge | KRM-86 | Supplied a camera-derived view direction through the USD Session Layer | `assets/_external/usd/test_grid/camera_direction_bridge.usda` |
| 8. Named USD primvar access | KRM-87 | Validated `roomP`, `tangentu`, and `tangentv` lookup in MDL | `assets/_external/usd/test_grid_attribs/primvar_access.usda` |
| 9. Single-room cross-atlas parallax | KRM-88 | Rendered five correctly oriented virtual room faces | `tests/test_room_map_single.usda` |
| 10. Depth slices and public material node | KRM-89 | Rendered four artist-controlled, depth-sorted alpha slices | `tests/test_room_map_slices.usda` |
| 11. Deterministic room variants across Omniverse-authored and DCC-exported geometry | KRM-90 | Selected shared UDIM interiors by `roomID` through a dedicated `roomUV` export contract | `tests/test_room_map_variants_houdini.usda` |
| 12. Window aperture scale and offset controls | KRM-94 | Preserved one centred virtual-room scale across square, landscape, and portrait apertures | `tests/test_room_map_apertures_houdini.usda` |

## 1. Building 150 Source Baseline

**Evidence level:** Documented reference.

**Result:** The Building 150 USD asset established the real Case 01 façade,
the scale of the window problem, and the visual starting point before room
frames, parallax interiors, and procedural variation.

**Primary capture artefact:**

- `assets/_external/usd/Moskovskiy_av_150/usd/Moskovskiy_av_150.usd`

**Existing evidence:**

- `docs/img/msk_150_omniverse.jpg` — retained overview of the source building
  in Omniverse.
- `README.md` — public problem statement and current production boundary.
- `docs/plans/project_rnd_room_map_shader.md` — original R&D objective and
  Case 01 relationship.

**Suggested capture:** Open the Building 150 asset and frame a façade with many
visible windows. Establish the visual problem by showing the flat glazing before
cutting to the diagnostic Room Map stages.

## 2. Houdini Room-Frame Geometry Analysis

**Jira:** KRM-79 — Geometry Context Analysis (SOP).

**Evidence level:** Documented reference.

**Result:** The analysis identified the geometry-preprocessing contract behind
the reference workflow: `roomP`, `tangentu`, `tangentv`, and `roomN` establish
the room frame, while `roomID` and `primbasis` group multi-polygon rooms and
select a stable reference primitive.

**Primary evidence:**

- `docs/knowledge_base/houdini/room_map_frame_sop.md`

**Supporting artefacts:**

- `hip/room map test 001.hiplc` — retained Houdini development scene.
- `hip/room map test 002.hiplc` — second retained Houdini development state.
- `hip/room map test 003.hiplc` — retained development history.
- `hip/room map test 004.hiplc` — later extended as the canonical KRM-90
  DCC-export validation source.
- `docs/knowledge_base/houdini/images/01 Create Room ID Attribute - 01.png`
- `docs/knowledge_base/houdini/images/01 Create Room ID Attribute - 02.png`
- `docs/knowledge_base/houdini/images/01 Create Room ID Attribute - 03.png`
- `docs/knowledge_base/houdini/images/02 RoomMapFrame Attributes - 01.png`
- `docs/knowledge_base/houdini/images/02 RoomMapFrame Attributes - 02.png`
- `docs/knowledge_base/houdini/images/02 RoomMapFrame Attributes - 03.png`
- `docs/knowledge_base/houdini/images/02 RoomMapFrame Attributes - 04.png`
- `docs/adr/006-hybrid-geometry-context.md` — historical architecture record
  for precomputed versus dynamically constructed frames.

**Suggested capture:** Show the `roomID` authoring and Room Map Frame SOP vector
visualisation in Houdini: horizontal tangent, vertical tangent, and normal.
Inspect `room map test 001.hiplc` and `room map test 002.hiplc` before recording
to identify the cleanest network state; the exact stage-to-file mapping is not
yet documented. Use the retained screenshots as the reference for the intended
attributes and viewport evidence.

## 3. Houdini Material, USD Binding, and Atlas Analysis

**Jira:** KRM-80 — Material Context Analysis; KRM-81 — Application Layer: USD
Binding; KRM-82 — Shader Internals.

**Evidence level:** Documented reference.

**Result:** The reference analysis established the cross-atlas layout, the
five room faces, four slice regions, MaterialX integration, USD material
binding, UDIM-offset concept, and the distinction between the Room Map shader
and the Room Lens baking workflow.

**Primary evidence:**

- `docs/knowledge_base/houdini/karma_room_map_workflow.md`

**Supporting artefacts:**

- `hip/room map test 001.hiplc`
- `hip/room map test 002.hiplc`
- `docs/knowledge_base/houdini/karma_room_map_vop.md`
- `docs/knowledge_base/houdini/karma_room_lens_vop.md`
- `docs/knowledge_base/houdini/images/03 kma_roommap_signature.png.png`
- `docs/knowledge_base/houdini/room_map_frame_sop.md`

**Suggested capture:** Use the retained Houdini network and signature images to
explain the reference inputs and atlas contract. If the original Houdini scene
contains the documented networks, capture the SOP frame attributes, Material
Library, material binding, and labelled atlas in one short sequence. Confirm
the contents of the two distinct retained `.hiplc` states before assigning one
as the canonical capture scene.

## 4. Native MDL Parallax Strategy

**Jira:** KRM-83 — Initial Documentation and Knowledge Base Setup; KRM-84 —
Final VEX-to-MDL Strategy.

**Evidence level:** Accepted architecture.

**Result:** The project chose a clean native implementation of established
Parallax Interior Mapping rather than a direct shader translation. The design
separates Houdini geometry preparation from MDL room-space ray construction,
analytic plane intersection, cross-atlas mapping, depth slices, variation, and
surface integration.

**Primary evidence:**

- `docs/adr/007-vop-to-mdl-parallax-logic.md`

**Supporting artefacts:**

- `docs/adr/006-hybrid-geometry-context.md`
- `docs/plans/project_rnd_room_map_shader.md`
- `docs/knowledge_base/houdini/karma_room_map_workflow.md`
- `README.md` — current public explanation of the native MDL/OpenUSD boundary.

**Suggested capture:** Present the cross-atlas and a compact room-space diagram
while summarising the chosen analytic path: frame construction, camera ray,
nearest room-plane hit, atlas remapping, and bounded texture sampling. This is
an architecture stage rather than a live renderer stage.

## 5. First Hand-Authored MDL Material

**Jira:** KRM-85 — MDL Hello World.

**Evidence level:** Renderer-validated on 18 August 2026; static USD binding
contract retained.

**Result:** A minimal MDL 1.7 material resolved through a relative USD asset
path, bound to a cube, and rendered as a red diffuse surface in both supported
RTX modes. This isolated module loading and material binding before any Room
Map mathematics was introduced.

**Primary capture artefact:**

- `assets/_external/usd/hello_world_material.usda`

**Supporting artefacts:**

- `src/mdl/hello_world.mdl`
- `tests/test_hello_world_material.py`
- `docs/knowledge_base/mdl/001_hello_world.md`

**Suggested capture:** Open the USD stage, select the bound material, show the
relative MDL source asset, and switch between RTX Real-Time and RTX Interactive
while the cube remains red.

## 6. MDL State-Function Diagnostics

**Jira:** KRM-86 — MDL State Functions.

**Evidence level:** Renderer-validated on 18 August 2026; static source and USD
contracts retained.

**Result:** Four diagnostic materials visualised `state::normal()`,
`state::position()`, `state::direction()`, and
`state::texture_coordinate(0)`. The decisive negative result was that
`state::direction()` remained static during viewport camera motion and could
not supply the material view vector required for PIM.

**Primary capture artefact:**

- `assets/_external/usd/test_grid/state_diagnostics.usda`

**Supporting artefacts:**

- `assets/_external/usd/test_grid/test_grid.usd`
- `src/mdl/diagnostics/normal_as_colour.mdl`
- `src/mdl/diagnostics/position_as_colour.mdl`
- `src/mdl/diagnostics/direction_as_colour.mdl`
- `src/mdl/diagnostics/uv0_as_colour.mdl`
- `tests/test_state_diagnostics.py`
- `docs/knowledge_base/mdl/002_state_functions.md`

**Suggested capture:** Frame all four diagnostic grids, orbit the viewport
camera, and emphasise that the direction grid remains unchanged while the
normal, position, and UV encodings retain their expected gradients.

## 7. Active-Camera Runtime Bridge

**Jira:** KRM-86 — MDL State Functions, runtime follow-up.

**Evidence level:** Renderer-validated on 18 August 2026; static bridge and
Session Layer contracts retained.

**Result:** Because MDL did not provide the required material view vector, the
runtime bridge began writing the active camera world position into a material
input in the USD Session Layer. The diagnostic material derived
`camera_position_world - surface_position_world`, and its colour changed with
camera motion without persisting camera updates to the source layer.

**Primary capture artefact:**

- `assets/_external/usd/test_grid/camera_direction_bridge.usda`

**Supporting artefacts:**

- `src/mdl/diagnostics/camera_direction_as_colour.mdl`
- `tools/omniverse/runtime/camera_position_bridge.py`
- `tests/shared_room_runtime/runtime/test_camera_position_bridge.py`
- `tools/omniverse/runtime/status_log.py`
- `tests/shared_room_runtime/runtime/test_status_log.py`
- `docs/knowledge_base/mdl/003_camera_position_bridge.md`

**Suggested capture:** Open the diagnostic scene, start the bridge using the
documented Script Editor procedure, then orbit the camera and record the grid
colour changing continuously. If useful, show that the authored value appears
in the Session Layer rather than the source USD.

## 8. Named USD Primvar Access

**Jira:** KRM-87 — MDL Primvar Access.

**Evidence level:** Renderer-validated on 18 August 2026; static export,
binding, and lookup contracts retained.

**Result:** The Houdini export carried `roomP`, `tangentu`, and `tangentv` as
unindexed vertex `float3` primvars. MDL read them by name through
`nvidia::support_definitions::data_lookup_float3()`. Three grids displayed the
expected encoded values without falling back to magenta.

**Primary capture artefact:**

- `assets/_external/usd/test_grid_attribs/primvar_access.usda`

**Supporting artefacts:**

- `assets/_external/usd/test_grid_attribs/test_grid_attribs.usd`
- `src/mdl/diagnostics/primvar_as_colour.mdl`
- `tests/test_primvar_access.py`
- `docs/knowledge_base/mdl/004_primvar_access.md`

**Suggested capture:** Show the three diagnostic grids and their distinct
colours, then inspect the USD primvars or material input names. The absence of
magenta is the immediate visual proof that the named lookups resolved.

## 9. Single-Room Cross-Atlas Parallax

**Jira:** KRM-88 — Single Debug Room: Cross-Atlas Parallax.

**Evidence level:** Renderer-validated on 23 August 2026; static scene,
material, and one-lookup contracts retained.

**Result:** A one-by-one test window constructed its room frame from the named
primvars, transformed the camera ray into normalised room space, intersected
the Back, Left, Right, Ceiling, and Floor planes, and sampled the corresponding
labelled cross-atlas region with one texture lookup. Face assignment and
orientation were accepted in both RTX modes.

**Primary capture artefact:**

- `tests/test_room_map_single.usda`

**Supporting artefacts:**

- `src/mdl/room_map_single.mdl`
- `assets/_external/tex/room_map_debug/room_map_debug.1001.png`
- `tests/test_room_map_single.py`
- `docs/knowledge_base/mdl/005_single_room_parallax.md`
- `docs/img/krm88/roommap_debug.1001.png` — retained public atlas copy.

**Existing visual evidence:**

- `docs/img/krm88/krm88_01.png` — baseline test window.
- `docs/img/krm88/krm88_02.png` — head-on virtual room view.
- `docs/img/krm88/krm88_03.png` — oblique virtual room view.
- `docs/img/krm88/krm88_04.png` — additional RTX Interactive validation view.

**Suggested capture:** Start the camera bridge for the Room Map material, begin
head-on, and orbit to reveal the labelled Left, Right, Ceiling, and Floor faces.
Keep the atlas visible in a brief cut so orientation errors are easy to read.

## 10. Depth Slices and Artist-Facing Material Node

**Jira:** KRM-89 — Depth Slices and Artist-Facing MDL Material Node.

**Evidence level:** Renderer-validated on 23 August 2026; static scene,
material-input, atlas, and lookup-count contracts retained.

**Result:** The public `room_map` material retained the accepted five-face room
and added four alpha-composited slice planes. Artists can enable each slice and
edit its depth percentage, offset, and scale. Contribution order follows
geometric depth rather than fixed S1-S4 numbering, and the implementation uses
bounded analytic intersections rather than ray marching.

**Primary capture artefact:**

- `tests/test_room_map_slices.usda`

**Supporting artefacts:**

- `src/mdl/room_map.mdl`
- `assets/_external/tex/room_map_debug/room_map_debug.1002.png`
- `tests/test_room_map_slices.py`
- `docs/knowledge_base/mdl/006_depth_slices.md`
- `docs/img/krm89/roommap_debug.1002.png` — retained public atlas copy.

**Existing visual evidence:**

- `docs/img/krm89/krm89_01.png` — green diagnostic room with four slices.
- `docs/img/krm89/krm89_02.png` — oblique RTX Real-Time result.
- `docs/img/krm89/krm89_03.png` — oblique RTX Interactive result.

**Suggested capture:** Start with all slices disabled to show the five-face
baseline. Enable S1-S4 individually, then together. Change at least two depth
values so their numeric order differs from their geometric order and record the
closer slice remaining visually in front. Finish by changing one slice offset
or scale in the Material Graph.

## 11. Deterministic Room Variants Across Omniverse-Authored and DCC-Exported Geometry

**Jira:** KRM-90 — Automatic Debug Room Variant Selection.

**Evidence level:** Renderer-validated on 26 August 2026 in both RTX Real-Time
and RTX Interactive; Omniverse-authored and DCC-export static contracts
retained. Houdini is the specific DCC source used by the exported test asset.

**Result:** One public MDL material deterministically maps repeated integer
`roomID` values to three complete diagnostic UDIM room variants. Disconnected
windows with the same identifier retain the same interior during camera motion
and renderer switching. The DCC-exported component adds a dedicated
face-varying `roomUV` channel, so the shader does not require the building's
ordinary packed UV layout to be replaced.

**Primary capture artefact:**

- `tests/test_room_map_variants_houdini.usda`

**Supporting artefacts:**

- `tests/test_room_map_variants.usda` — six-grid Omniverse-authored test scene.
- `hip/room map test 004.hiplc` — canonical Houdini source.
- `assets/_external/usd/test_grid_wins/test_grid_wins.usd` — exported
  component root; its payload, geometry, and material layers are retained in
  the same directory.
- `src/mdl/room_map.mdl`
- `assets/_external/tex/room_map_debug/room_map_debug.1001.png`
- `assets/_external/tex/room_map_debug/room_map_debug.1002.png`
- `assets/_external/tex/room_map_debug/room_map_debug.1003.png`
- `tests/test_room_map_variants.py`
- `tests/test_room_map_variants_houdini.py`
- `docs/knowledge_base/mdl/007_room_variants.md`

**Existing visual evidence:**

- `docs/img/krm90/krm90_01.png` — Omniverse-authored test scene in RTX Real-Time.
- `docs/img/krm90/krm90_02.png` — Omniverse-authored test scene in RTX Interactive.
- `docs/img/krm90/krm90_03.png` — DCC-exported test geometry in RTX Real-Time.
- `docs/img/krm90/krm90_04.png` — DCC-exported test geometry in RTX Interactive.

**Suggested capture:** Open the Houdini wrapper, start the camera bridge, and
orbit across the 15-window grid. Hold on spatially separated windows sharing
the same diagnostic colour, then switch the seed and show the distribution
changing without breaking same-`roomID` consistency. Finish with the same view
in RTX Real-Time and RTX Interactive.

## 12. Window Aperture Scale and Offset Controls

**Jira:** KRM-94 — Window Aperture Scale and Offset Controls.

**Evidence level:** Renderer-validated on 26 August 2026 in both RTX Real-Time
and RTX Interactive (Path Tracing); isolated and Houdini-export static
contracts retained.

**Result:** The MDL material separates the physical aperture dimensions from a
uniform virtual-room extent. Square, landscape, and portrait openings retain
one centred, proportionate interior room instead of stretching the cross-atlas.
The material preserves five room-face and four slice lookups, supports an
editable uniform room scale and independent aperture scale and offset inputs,
and retains the camera bridge, room-frame, and UDIM-variant contracts.

**Primary capture artefacts:**

- `tests/test_room_map_apertures.usda`
- `tests/test_room_map_apertures_houdini.usda`

**Supporting artefacts:**

- `hip/room map test 005.hiplc` — canonical Houdini source.
- `assets/_external/usd/test_grid_wins_diff/test_grid_wins_diff.usd` —
  exported component root; its payload, geometry, and material layers are
  retained in the same directory.
- `src/mdl/room_map.mdl`
- `tests/test_room_map_apertures.py`
- `tests/test_room_map_apertures_houdini.py`
- `docs/knowledge_base/mdl/008_window_apertures.md`

## Known Capture Gaps

- The early Houdini analysis includes several `.hiplc` development states, but
  the exact mapping of files 001 through 003 to the earliest analysis steps is
  not recorded. File 004 is now the canonical KRM-90 DCC-export validation
  source.
- The reproducible USD assets for KRM-85 through KRM-87 are under
  `assets/_external/` and therefore depend on the local hydrated asset set.
- KRM-85 through KRM-87 have recorded validation notes but no dedicated public
  screenshot set equivalent to `docs/img/krm88/` and `docs/img/krm89/`.
- The camera bridge still uses the Script Editor R&D bootstrap. Packaging it as
  a Kit extension belongs to KRM-91 and is not a completed milestone.
- Shared room volumes across non-coplanar windows, material-node UX refinement,
  Building 150 integration, and performance measurement remain outside this
  completed-stage index.

## Maintenance Rule

Add a new stage only after its acceptance evidence exists. Record the exact
capture scene, implementation source, diagnostic assets, static contract, and
renderer-validation boundary. Do not describe a planned capability as a
completed result.
