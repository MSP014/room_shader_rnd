# Omniverse Room Map Shader for OpenUSD Digital Twins

> An installable NVIDIA Omniverse Kit extension for scalable parallax interiors

**Status**: `msp.orms.runtime` 1.0.1 is the current accepted release.
Automated contracts cover the artist workflow, Interior Sets, source-safe
mesh-assignment overrides, reset controls, portable demo content, and quiet
production diagnostics. The installed package is accepted in RTX Real-Time
and RTX Interactive, and the local production libraries publish coherent
x1-x4 variant manifests. Performance evidence remains a separate
empirical-validation task.

**Project shorthand: ORMS — Omniverse Room Map Shader**

**ORMS (Omniverse Room Map Shader)** is delivered as the installable
`msp.orms.runtime` Kit extension around the OpenUSD / NVIDIA MDL implementation
described below. The underlying technique — Parallax Interior Mapping (PIM) —
is well established and predates this project.

Once installed, ORMS is enabled and configured through the ordinary Kit user
interface. It does not require users to copy Python into Script Editor or add
`--ext-folder` and `--enable` arguments to every application launch.

---

## The Problem

Urban digital twins face a fundamental visual challenge: **believable building
interiors at scale**.

A technically detailed city can still feel lifeless at street level when
hundreds of windows resolve to identical reflections, black glazing, simple
curtain textures, or another repetitive façade treatment. Each visible room
could instead contain furniture, wall art, lighting, and props, but that creates
a trade-off between visual detail, authoring effort, scene complexity, storage,
asset management, and potentially rendering cost:

- **Full interior geometry**: Hundreds of visible rooms can require thousands
  of placed furniture and prop instances, even when the asset library is
  efficiently instanced.
- **Black windows**: Cheap to render, but visibly break immersion.
- **Reflection-only or curtain fallbacks**: Acceptable from a distance, but
  unconvincing at street level.

> **How can a city-scale digital twin gain believable visible interiors without
> requiring full physical room geometry behind every window?**

The rendering technique already exists. The research problem is carrying it
cleanly through an artist-facing OpenUSD and NVIDIA MDL workflow.

---

## The Solution: Parallax Interior Mapping

**Parallax Interior Mapping (PIM)** renders interiors into specialised textures,
then uses shader mathematics to create a convincing 3D illusion. It is a
well-established technique for producing view-dependent depth perception from
2D data.

**How it works:**

1. Bake an interior into a cross-shaped atlas containing the room faces and
   optional depth slices.
2. Precompute a local coordinate frame for each window.
3. Use the camera direction in the material to select the correct atlas region
   and create view-dependent parallax.

**The intended production result**: large numbers of visually varied virtual
interiors evaluated on existing window surfaces rather than modelled as full
interior geometry.

**The challenge**: Build an artist-facing PIM material that carries the required
room-frame and camera data through OpenUSD, then evaluates the illusion
efficiently in NVIDIA MDL.

---

## This Research: Parallax Interior Mapping in MDL/OpenUSD

**Goal**: Develop ORMS as a native PIM material and artist-facing workflow for
NVIDIA MDL and OpenUSD, enabling Omniverse-based digital twins to use apparent
interiors without requiring every visible room to exist as full geometry.

**Why this matters:**

- **For Digital Twins**: Scalable urban interiors with reduced geometry and scene-complexity requirements
- **For NVIDIA**: Demonstrates MDL and OpenUSD capability for an advanced, artist-facing material workflow
- **For the industry**: Cross-DCC interoperability — workflows shouldn't be siloed by renderer choice

> [!NOTE]
> **On Technique vs. Implementation**
>
> **Parallax interior mapping** is a well-established rendering technique used across game engines (Unreal, Unity), shading languages (OSL, GLSL), and DCC tools. SideFX's Karma Room Map is an important VEX-based reference implementation, not the origin of the underlying algorithm.
>
> This research develops a native PIM implementation for MDL and OpenUSD. The SideFX workflow informs the reference geometry, frame-data, and atlas contracts; it is not copied or directly translated.
>
> No readily available public Omniverse/MDL Room Mapping implementation was
> found during this project's research. This is not a claim that ORMS is the
> first implementation of the technique in Omniverse or elsewhere.
>
> Credit to SideFX for their excellent documentation and implementation, which serve as an important reference for this work.

---

## Where ORMS Fits in an Urban Digital Twin

A city-scale digital twin may need several representations of the same building
depending on viewing distance, task, and simulation requirements:

```text
City massing
    ↓
Detailed exterior / façade
    ↓
Detailed façade + ORMS apparent interiors
    ↓
Full physical interior geometry where required
```

This is an illustrative representation hierarchy, not an official CityGML,
OpenUSD, or NVIDIA LOD specification. ORMS occupies the space between an
exterior-only building and a fully modelled interior: it adds believable
apparent depth and variation where the camera remains outside, while physical
geometry remains available wherever the rooms themselves matter.

## Relevant Urban Digital Twin Use Cases

| Digital-twin context | Where ORMS can add value |
| --- | --- |
| Urban planning and masterplanning | Street- and neighbourhood-scale reviews where façade realism matters but users do not need to enter every room. |
| Smart-city operational visualisation | A more believable inhabited context for traffic, transit, sensor, CCTV, utility, flood, and public-space dashboards whose operational data is not room topology. |
| Transportation, pedestrian, and logistics twins | Street-level context for roads, deliveries, public transit, curbside operations, and outdoor pedestrian flows. |
| Geospatial and GIS city twins | An apparent-interior layer for photogrammetry, procedural cities, 3D Tiles, and aggregated OpenUSD buildings that otherwise end at flat glazing. |
| Architecture and real estate | Exterior neighbourhood walkthroughs where modelling hundreds of secondary interiors would add little functional value. |
| Public communication | Planning reviews, exhibitions, consultations, executive demonstrations, and presentation material where visual plausibility supports comprehension. |
| Exterior-focused simulation | A presentation layer around urban airflow, flooding, traffic, outdoor sensor, or telecom visualisation. ORMS must remain separate from the physical simulation ground truth. |

## Where ORMS Is Not a Substitute for Geometry

**ORMS is a visual representation technique, not a substitute for physical
interior geometry when that geometry participates in simulation, navigation,
collision, engineering analysis, or operational state.**

Physical interiors remain necessary for indoor robotics and navigation;
evacuation and indoor pedestrian simulation; CFD and HVAC analysis; RF and
wireless propagation; BIM/FM workflows that require rooms and equipment;
interior collision or physics; physically correct sensor simulation; and any
workflow where walls, doors, furniture, or internal topology are simulation
inputs rather than presentation content.

---

## Visual Baseline and Transformation Path

This RnD begins with a digital replica of Building 150 on Moskovsky Avenue in
Saint Petersburg, prepared as a USD asset for Omniverse. As the screenshot
shows, its windows currently read as identical mirror-like polygons that do
little more than repeat the surrounding HDRI reflection across the facade. The
result is mechanically uniform: every opening responds in much the same way,
with no suggestion of the spaces or activity behind the glass.

The goal of this RnD remains to create a native MDL Room Map material and carry
it through to production applicability. The renderer-validated technical core
now establishes the material, OpenUSD data contract, runtime classification,
and retained DCC-to-Omniverse evidence. That result has been applied to the
real Building 150 asset: ORMS replaces the repetitive mirrored-window baseline
with view-dependent interiors while preserving the building's non-window
materials and avoiding physical geometry for every room.

![Starting asset — Building 150 on Moskovsky Avenue in Omniverse](docs/img/msk_150_omniverse.jpg)

*Starting asset: the Omniverse USD building before room-frame data, MDL
parallax mapping, and interior variation are introduced.*

### First MDL Parallax Proof

The first functional MDL vertical slice uses a one-by-one test window to sample
a labelled cross-atlas and form a view-dependent virtual room. The diagnostic
texture makes every face assignment readable, while the applied material views
show how the visible walls change as the camera moves.

| Baseline test plane | Diagnostic cross-atlas |
| --- | --- |
| <img src="docs/img/krm88/krm88_01.png" alt="Unshaded one-by-one test window plane in USD Composer" height="320"> | <img src="docs/img/krm88/roommap_debug.1001.png" alt="Labelled Room Map debug cross-atlas" height="320"> |

*The diagnostic cross-atlas defines the five virtual room faces. S1–S4 are
reserved depth-slice markers and are not sampled by this first vertical slice.*

| Head-on room view | Oblique room view |
| --- | --- |
| ![Head-on view of the labelled virtual room](docs/img/krm88/krm88_02.png) | ![Oblique view of the labelled virtual room](docs/img/krm88/krm88_03.png) |

*The changing visible faces demonstrate the parallax response while the
labelled atlas exposes any incorrect face assignment or orientation.*

### MDL Depth-Slice Proof

The public `room_map` material extends the five-face room with four
alpha-composited virtual planes. The green diagnostic atlas separates this
validation from the red single-room baseline: S1–S4 are sampled from the four
corner regions and positioned by editable percentages of room depth.

| Depth-slice test room | Depth-slice diagnostic cross-atlas |
| --- | --- |
| <img src="docs/img/krm89/krm89_01.png" alt="Green Room Map test room with four labelled depth slices" height="320"> | <img src="docs/img/krm89/roommap_debug.1002.png" alt="Green Room Map cross-atlas with S1 to S4 slice regions" height="320"> |

*The green cross-atlas retains the five room faces and uses its four corner
regions as alpha-capable S1–S4 slice tiles.*

| Oblique RTX Real-Time view | Oblique RTX Interactive (Path Tracing) view |
| --- | --- |
| <img src="docs/img/krm89/krm89_02.png" alt="Room Map depth slices under an oblique RTX Real-Time view" height="320"> | <img src="docs/img/krm89/krm89_03.png" alt="Room Map depth slices under an oblique RTX Interactive Path Tracing view" height="320"> |

*The changing camera angle exposes the virtual depth planes. The material
sorts their alpha contribution by edited geometric depth, rather than by fixed
S1–S4 order.*

### Deterministic Room Variation Across Omniverse-Authored and DCC-Exported Geometry

The following completed stage stored three diagnostic interiors in one UDIM
sequence and selected them inside MDL from an integer `roomID` and
material-level seed.
Disconnected windows carrying the same identifier retain the same green, red,
or blue room without requiring separate material bindings.

| Omniverse-authored test scene — RTX Real-Time | Omniverse-authored test scene — RTX Interactive |
| --- | --- |
| <img src="docs/img/krm90/krm90_01.png" alt="Six disconnected windows showing deterministic green, red, and blue Room Map variants in RTX Real-Time" height="320"> | <img src="docs/img/krm90/krm90_02.png" alt="Six disconnected windows showing deterministic Room Map variants in RTX Interactive Path Tracing" height="320"> |

*The six grids created for the Omniverse test scene make repeated `roomID`
pairs directly comparable, while the labelled faces and S1–S4 slices expose
orientation or tile-selection errors.*

The second scene uses 15-window test geometry exported through a standard
OpenUSD workflow. Houdini is the specific DCC used for this retained asset and
procedurally authors a dedicated `roomUV` primvar. The model's ordinary UV
layout remains independent from the Room Map projection.

| DCC-exported test geometry — RTX Real-Time | DCC-exported test geometry — RTX Interactive |
| --- | --- |
| <img src="docs/img/krm90/krm90_03.png" alt="DCC-exported fifteen-window test geometry with deterministic Room Map variants in RTX Real-Time" height="320"> | <img src="docs/img/krm90/krm90_04.png" alt="DCC-exported fifteen-window test geometry with deterministic Room Map variants in RTX Interactive Path Tracing" height="320"> |

*The facade keeps its original material while one shared MDL material drives
all windows. Spatially separated windows with the same `roomID` remain
visually consistent in both RTX renderers.*

### Runtime-Classified Shared Rooms on a Houdini-Exported Building

The runtime classifier derives neighbouring windows directly from the composed
OpenUSD stage and maps each supported group into one coherent x1-x4 virtual
room. The retained Houdini-derived fixture combines flat runs, different
aperture sizes, faceted bays, a fully angled bay, and bounded 90-degree corners
without rewriting the source building asset.

| Shared-room fixture — RTX Real-Time | Shared-room fixture — RTX Interactive |
| --- | --- |
| <img src="docs/img/krm93/krm93_01.png" alt="Houdini-exported building with runtime-classified x1-x4 Room Map interiors, bays, and corners in RTX Real-Time" height="320"> | <img src="docs/img/krm93/krm93_02.png" alt="Houdini-exported building with runtime-classified x1-x4 Room Map interiors, bays, and corners in RTX Interactive Path Tracing" height="320"> |

*The labelled debug interiors expose room-family selection, wall orientation,
depth slices, and deterministic variation in one overview. Flat windows,
faceted bays, and right-angle facade turns retain one continuous room
perspective in both RTX renderer modes.*

### Five Interior Sets: Diagnostic Assignment to Production Interiors

KRM-92 extends the same global classifier from one atlas and material profile
to five selector-driven Interior Sets. The forced-debug view makes the Set and
room-family assignments readable across the complete building; the production
view replaces those diagnostic atlases with the independently configured room
libraries without changing the source USD asset.

| Forced packaged-debug assignment | Production Interior Sets |
| --- | --- |
| <img src="docs/img/krm92/krm-92_01.png" alt="Building 150 with five selector-driven Interior Sets displayed through labelled packaged debug atlases in RTX Interactive" height="320"> | <img src="docs/img/krm92/krm-92_02.png" alt="Building 150 with five production Interior Set atlas libraries in RTX Interactive Path Tracing" height="320"> |

*The two overview states use the same classified windows and shared-room
layout. Debug mode exposes routing and x1-x4 family selection; production mode
shows the artist-facing result.*

| Production facade overview | Production oblique facade view |
| --- | --- |
| <img src="docs/img/krm92/krm-92_03.png" alt="Production ORMS interiors distributed across the front facade of Building 150" height="320"> | <img src="docs/img/krm92/krm-92_04.png" alt="Production ORMS interiors viewed obliquely across adjacent facades of Building 150" height="320"> |

*Distinct room libraries remain visually legible across repeated windows while
one runtime preserves the shared classifier, stable Set identities, and
source-safe Session Layer ownership.*

| Near-field production rooms | Shared rooms around a curved facade |
| --- | --- |
| <img src="docs/img/krm92/krm-92_05.png" alt="Near-field RTX Interactive view of two detailed production ORMS interiors" height="320"> | <img src="docs/img/krm92/krm-92_06.png" alt="Production ORMS rooms maintaining view-dependent depth around the curved facade of Building 150" height="320"> |

*The retained close views expose the parallax depth, depth-slice furnishing,
curtains, lighting, and cross-window room continuity that replace physical
interior geometry. The visible performance HUD records this validation session
only; it is not a substitute for the planned controlled benchmark.*

### Current Validated Boundary

#### Validated now

- A common centred virtual-room scale across square `1 × 1`, landscape `2 × 1`,
  and portrait `1 × 2` windows in Omniverse-authored and Houdini-exported
  test assets.
- Five virtual room faces: Back, Left, Right, Ceiling, and Floor.
- Four alpha-composited virtual depth slices: S1, S2, S3, and S4.
- Named USD frame primvars: `roomP`, `tangentu`, and `tangentv`.
- Dedicated face-varying `roomUV` coordinates that do not replace the model's
  ordinary UV layout.
- Eight deterministic UDIM room variants selected from `roomID` and
  `variation_seed` through one material binding.
- Active-camera runtime bridge and cross-atlas mapping.
- Editable uniform room scale plus aperture scale and offset controls.
- Editable per-slice enable, depth, offset, and scale controls.
- Correct face assignment, orientation, and depth sorting in RTX Real-Time and
  RTX Interactive (Path Tracing).
- Shared coherent room volumes across automatically classified flat, bay, and
  right-angle window groups in both Omniverse-authored and Houdini-exported
  validation fixtures.
- Production validation on all 232 Building 150 window apertures with adaptive
  floor- and façade-local classification across x1–x4 families while retaining
  the source asset and every non-window material binding.
- Independent per-Interior-Set material profiles, including one-surface glass
  roughness, reflectivity, tint, and artistic transmission controls.
- Five selector-driven Interior Sets on Building 150, each with independent
  production x1–x4 atlas locations and global packaged-debug fallbacks.
- Luminance-selected interior emission with threshold, softness, strength, and
  independent depth-slice eligibility, validated in both RTX renderer modes.
- Installable `msp.orms.runtime` 0.1.20 packaging, publication, installation,
  enablement, and AUTOLOAD through a local Kit extension registry.
- Automatic assignment of contract-valid `Windows_Glass` meshes through a
  reversible ORMS-owned Session sublayer, with source restoration on teardown.
- Material Library creation and manual binding without Script Editor code.
- A dockable `Window > ORMS` panel with lifecycle controls, per-Set material
  parameters, staged repeatable Interior Set blocks, debug/production mode,
  and portable `.orms` scene profiles.
- One-click opening of the bundled Building 150 demo scene, with an automatic
  relative-path demo profile on a factory-clean first run.
- Version-aware in-process extension upgrades, with 1.0.1 enablement,
  demo-scene loading, and source-safe ownership accepted from the installed
  runtime log.

#### Remaining boundaries

- Optional ORMS 2.0 glass contamination and parallax art-direction controls.
- A geometry-versus-Room-Map performance benchmark.

---

## Extension Architecture

The Kit extension is the product boundary; shader maths, OpenUSD
classification, runtime state, resource resolution, and UI wiring remain
separate implementation zones:

```text
Extension Manager / AUTOLOAD
    -> extension.py                 minimal Kit entry point
       -> service.py                lifecycle and stage coordination
          -> materials/             MDL + Material Library registration
          -> assignments/           reversible Windows_Glass assignment
          -> interior_sets/         staged configuration and resolution
          -> lifecycle state machine
             -> shared-room classifier and Session Layer authoring
             -> active-camera material bridge
          -> ui/                     Window > ORMS and its three settings tabs
```

| Component | Responsibility |
| --- | --- |
| `extension.py` | Starts and stops the extension without owning runtime logic. |
| `service.py` | Coordinates stage events, assignment, lifecycle, settings, startup, and teardown. |
| `lifecycle.py` | Owns the `Inactive`, `Running`, `Stopped`, and `Failed` state transitions. |
| `runtime/assignments/` | Owns automatic mesh-assignment inspection, overrides, and presentation. |
| `runtime/interior_sets/` | Owns staged set configuration, persistence, transactions, and atlas resolution. |
| `runtime/profiles/` | Owns portable `.orms` profiles and their save/load workflow. |
| `runtime/materials/` | Owns MDL registration, atlas manifests, Material Library integration, and update feedback. |
| `runtime/ui/` | Owns the dockable `Window > ORMS` shell and artist-facing controls. |
| `msp/orms/shared_room/settings_panel.py` | Builds the classifier, material, and atlas controls embedded in that shell. |
| `msp/orms/shared_room/material_controls.py` | Defines the single persistent artist value for every shared shader control. |
| `runtime/resources.py` | Resolves canonical MDL, packaged debug atlases, and external production families. |
| `msp/orms/scene/source_loader.py` | Reloads the exact extension-owned runtime graph and cleans up live callback owners. |
| `msp/orms/scene/assignment.py` | Validates compatible window meshes and owns reversible default bindings. |
| `msp/orms/classification/` | Performs deterministic, Kit-independent x1–x4 room classification. |
| `msp/orms/shared_room/` | Interprets composed OpenUSD and authors derived runtime state in an anonymous Session sublayer. |

Automatic assignment and generated ORMS state use separate anonymous Session
sublayers. Their implementation prims are hidden from the ordinary Stage tree,
and removing those layers restores the source asset without rewriting its USD
files. Common material parameters are presented once in the ORMS window and
fanned out to the active x1–x4 materials.

---

## Install and Use the Kit Extension

The currently accepted distribution path is a local filesystem Kit registry.
Publishing and installation are separate responsibilities.

### Publish to the Registry — Developer or Distributor

The registry owner publishes the standalone extension from this repository
into a configured Kit App Template registry:

```powershell
python tools/publish_orms_local_registry.py `
    --kit-app-root E:\path\to\kit-app-template
```

This is a release operation. Artists installing ORMS from an already
configured registry do not run the publication script.

### Install and Run — Artist or Extension User

Once the application is connected to a registry containing ORMS, use the
normal Kit workflow:

1. Launch the application normally; for a Kit App Template checkout, use
   `./repo.sh launch` on Linux or `.\repo.bat launch` on Windows.
2. Open `Window > Extensions` and find `Omniverse Room Map Shader`.
3. Select `Install`, enable the extension, and select `AUTOLOAD`.
4. On later launches, start the Kit application normally. ORMS is discovered
   from the registry and starts without repository-specific command-line
   arguments.

Open `Window > ORMS` to access lifecycle controls and the `ORMS Classifier`,
`Material Parameters`, and `Interior Atlases` tabs. Compatible
`Windows_Glass` meshes are recognised and assigned automatically. The same
material remains available for manual assignment through
`Create > Material > ORMS > Omniverse Room Map Shader`.

`Start` activates an eligible stage, `Stop` freezes its current calculated
result, `Restart` rebuilds the ORMS runtime, and `Restore Original Asset`
removes ORMS-owned Session Layer state and reveals the source material binding.
Disabling the extension performs the same source-safe teardown.

The installed package contains public x1–x4 debug atlases. Production atlases
remain external content and are selected independently for each room family in
the `Interior Atlases` tab.

The repository stores its bundled demo binaries with Git LFS. Source users
should install Git LFS before cloning, or run `git lfs install` followed by
`git lfs pull` in an existing checkout. For GitHub-generated ZIP downloads,
the repository owner must enable **Include Git LFS objects in archives**;
otherwise the archive can contain LFS pointer files instead of the demo
assets.

For package construction and local-registry administration, see the
[extension README](exts/msp.orms.runtime/README.md).

---

## Upstream Room Map Content Factory

The material-side R&D is complemented by an existing Houdini content-generation
workflow. A procedural Solaris / Karma XPU / PDG / Copernicus pipeline can
generate Room Map libraries by varying wallpaper, lighting, curtains, props,
and depth-slice content. This content factory is a separate upstream authoring
system, not part of the MDL shader itself. Building 150 now exercises five
selector-driven production libraries across x1–x4 room sizes, while packaged
labelled debug families remain available as a global diagnostic mode and
per-family fallback. The five local production libraries publish versioned
semantic variant manifests with aligned x1-x4 identity sequences.

## Production Validation Path

The technical R&D core, first production-building integration, installable Kit
extension, and KRM-92 artist workflow are complete. The remaining validation
path scales the accepted contract from one building to an urban digital-twin
context and adds controlled performance evidence.

### Stage 1: Building 150 Integration — Complete

1. Applied the ORMS material contract to the real Building 150 USD asset
   without modifying its source layers.
2. Validated all 232 window apertures, hierarchy, orientation, adaptive room
   grouping, and material-binding isolation.
3. Integrated the 56-variant real x1 atlas and retained correctly bounded debug
   families for x2–x4 until their real content exists.
4. Added independent one-surface glass and luminance-selected emission without
   breaking the PIM result or increasing its five-lookup budget.
5. Accepted exterior camera motion and both RTX renderer modes with stable room
   identity, parallax, reflections, and source materials.
6. Retained the fixed Building 150 fixture for a future performance benchmark;
   no geometry-versus-ORMS result is claimed by this integration milestone.

### Stage 2: Urban Digital-Twin Scale — Planned

1. Apply the accepted workflow to a family of several building assets.
2. Assemble those buildings into multiple city blocks.
3. Validate repeatable setup, visual variation, runtime ownership, and camera
   response across the combined scene.
4. Measure the geometry-versus-ORMS trade-off at representative street and
   neighbourhood viewpoints.

---

## Technical Challenge: Native MDL/OpenUSD Implementation

The SideFX reference workflow and this native MDL/OpenUSD implementation meet
different geometry, material, and runtime constraints:

### 1. **Room Frame Data in MDL**

Houdini exports `roomP`, `tangentu`, and `tangentv` as named USD `float3`
primvars. The validated MDL material reads them with
`nvidia::support_definitions::data_lookup_float3()` and constructs the local
room frame from the exported data. A separate face-varying `roomUV` primvar
provides normalised window coordinates without replacing the model's ordinary
packed UV layout.

`nvidia::support_definitions` is an Omniverse-specific dependency of this
implementation. The named-primvar path has been visually validated in RTX
Real-Time and RTX Interactive (Path Tracing); the detailed evidence is in the
[primvar access diagnostic](docs/knowledge_base/mdl/004_primvar_access.md).

This named-primvar route is the current validated production contract. Dynamic
frame construction for environments without the NVIDIA support definitions
module remains a possible compatibility path, not a demonstrated capability.

---

### 2. **Camera Position Runtime Bridge**

`state::direction()` was tested and does not provide the material view direction
required for PIM. Instead, `msp/orms/scene/camera_position_bridge.py`
obtains the active Kit or Composer camera world position and writes it to the
`camera_position_world` material input in the USD **Session Layer**. Camera
motion therefore does not become a permanent edit to the source USD scene.

The diagnostic view vector is
`camera_position_world - surface_position_world`. The PIM material
transforms both positions into the room frame before constructing its ray. See
the [state-function diagnostics](docs/knowledge_base/mdl/002_state_functions.md)
and [camera bridge contract](docs/knowledge_base/mdl/003_camera_position_bridge.md)
for the detailed validation record.

---

### 3. **First Five-Face Analytic Parallax Baseline**

The retained `room_map_single.mdl` proof established the single-room analytic
projection:

1. Construct the local room frame from `roomP`, `tangentu`, and `tangentv`.
2. Transform camera and surface positions into that room frame.
3. Build the view ray through the window.
4. Intersect the ray with the Back, Left, Right, Ceiling, and Floor planes.
5. Select the nearest positive intersection.
6. Convert the hit point into the corresponding cross-atlas region.
7. Sample that region with `tex::lookup_float4()`.

This baseline uses one atlas lookup and has no depth-slice composition.

---

### 4. **Validated Depth-Slice Extension**

`room_map.mdl` retains the five-face analytic trace, then intersects the same
view ray with up to four slice planes. Each plane is positioned from zero per
cent at the window to one hundred per cent at the back wall, samples its
corresponding S1–S4 atlas corner, and alpha-composites over the room result.
The contribution order follows the edited geometric depths, so artists can
reorder slices without changing their S1–S4 identifiers.

The prototype exposes enable, depth, offset, and scale controls for each slice
and has been visually validated in RTX Real-Time and RTX Interactive (Path
Tracing). See the [depth-slice contract](docs/knowledge_base/mdl/006_depth_slices.md)
for its parameter and validation boundary.

---

### 5. **Deterministic UDIM Room Variation**

The public `room_map.mdl` material reads an integer `roomID`, combines it with
`variation_seed`, and selects one complete interior from a tiled UDIM atlas.
Disconnected windows with the same identifier receive the same room, while a
seed change redistributes the variants without adding per-window materials or
texture lookups.

The six-grid Omniverse-authored scene proves the selection logic. The
15-window DCC-exported scene proves that `roomID`, the room frame, and the
dedicated `roomUV` coordinates survive the authored USD workflow. See the
[room-variant contract](docs/knowledge_base/mdl/007_room_variants.md) for the
mapping, export requirements, and retained validation scenes.

---

### 6. **Window Aperture Scale and Offset Controls**

KRM-94 separates the physical aperture from the centred virtual room. Square,
landscape, and portrait windows therefore retain one stable room scale while
artist-facing aperture scale and offset controls describe how each opening
reveals that room. The accepted contract preserves the five room faces, depth
slices, frame primvars, and ordinary mesh UVs in both Omniverse-authored and
Houdini-exported geometry.

See the
[window-aperture contract](docs/knowledge_base/mdl/008_window_apertures.md) for
the parameter, coordinate-space, and renderer-validation record.

---

### 7. **Runtime-Classified Shared Rooms and USD Composition**

KRM-93 derives neighbouring apertures from the composed OpenUSD stage and maps
supported flat runs, rigid faceted bays, and bounded right-angle corners into
coherent x1-x4 virtual rooms. The runtime authors derived world-space primvars
and specialised material bindings in the Session Layer, leaving the source USD
asset unchanged. It also preserves deterministic eight-way room variation,
physical aperture controls, four depth slices, and stable camera response.

The retained fixtures cover Omniverse-authored and Houdini-exported geometry,
including referenced instanceable components. `Preserve` keeps source
instanceability and uses the x1 material fallback where descendant overrides
are unavailable; `Session de-instance` creates reversible ORMS-owned Session
Layer opinions for coherent shared rooms. Atlas-family settings, missing-family
fallbacks, stage replacement, runtime stop/reload, and subscription ownership
are part of the accepted lifecycle contract.

See the
[shared-room contract](docs/knowledge_base/mdl/009_shared_multi_window_rooms.md)
for the classification, primvar, fallback, instancing, and renderer evidence.

---

### 8. **Production Kit Extension and Artist Workflow**

[`exts/msp.orms.runtime`](exts/msp.orms.runtime/) is now a standalone,
installable Kit extension rather than a manual runtime launcher. Its manifest,
Python package, MDL resources, public debug atlases, icons, changelog, and
Extension Manager documentation are materialised into one non-overwriting
release bundle and published through Kit's ordinary extension-registry flow.

Installed versions through 0.1.18 have exercised the local-registry workflow,
AUTOLOAD, Material Library creation, reversible automatic assignment, five
Interior Sets, independent x1–x4 runtime material families, and source-safe
Session Layer ownership. Version 0.1.20 is published and accepted in RTX
Real-Time and RTX Interactive; its final log also confirms clean
disable/re-enable ownership.

The canonical module ownership and Session Layer flow are described once in
[Extension Architecture](#extension-architecture). This milestone section
records the installed result rather than repeating that architecture.

The [KRM-91 integration record](docs/knowledge_base/mdl/011_orms_kit_extension.md)
contains the architecture, failure history, and installed acceptance evidence.
The [KRM-92 delivery record](docs/knowledge_base/mdl/012_orms_ui_and_artist_workflow.md)
records the completed artist-facing implementation and installed acceptance
without reopening the accepted extension runtime.

---

### 9. **Geometry-versus-ORMS Performance Benchmark**

The final production argument requires measured evidence, not an assumed
performance claim. A controlled benchmark will compare ORMS against real or
representative instanced interior geometry using the same building assets,
camera path, renderer settings, and visual target. It will record GPU frame
time or FPS, VRAM, scene load time, USD prim or instance count, and practical
geometry statistics before the workflow is presented as a city-scale
optimisation.

The draft [geometry-versus-ORMS VRAM benchmark](docs/knowledge_base/mdl/013_geometry_vs_orms_vram_benchmark.md)
predicts approximately **15-34x lower texture residency for ORMS** under its
primary like-for-like assumptions. This is an unverified analytical hypothesis,
not an empirical performance result: it does not yet prove an equivalent FPS
gain, load-time reduction, or measured renderer-memory ratio.

---

## Research Progress

### Phase 1: Documentation & Analysis — Complete

The [Knowledge Base](docs/knowledge_base/) and ADRs document the SideFX
reference workflow, the PIM coordinate contract, and the native MDL/OpenUSD
implementation decisions.

### Phase 2: MDL / USD Integration Strategy — Validated

The validated integration contracts now include:

- Houdini-exported USD frame primvars.
- MDL named `float3` primvar lookup.
- Active-camera runtime bridge.
- Room-space view-ray construction.
- Cross-atlas face projection.
- Dedicated `roomUV` transport from DCC geometry.
- Deterministic `roomID`-to-UDIM variant selection.

### Phase 3: Renderer-Validated Technical Core — Complete

The renderer-validated implementation supports:

- A common centred virtual-room scale across square, landscape, and portrait
  windows in Omniverse-authored and Houdini-exported test geometry.
- Five virtual room faces and four alpha-composited S1–S4 depth slices.
- Editable slice depth, offset, and scale controls.
- Eight deterministic UDIM room variants shared by repeated `roomID` values.
- A dedicated `roomUV` export contract that leaves ordinary mesh UVs intact.
- View-dependent parallax in RTX Real-Time and RTX Interactive (Path Tracing).
- Automatic shared-room classification for flat, bay, and right-angle window
  groups without permanent edits to source USD assets.
- Physical aperture scale and offset controls across differing window sizes.
- Reversible Preserve and Session de-instance policies for referenced
  instanceable components.
- Deterministic family fallback, central ORMS settings, and runtime lifecycle
  behaviour validated in retained Omniverse-authored and Houdini-exported
  fixtures and in the installed extension.
- Adaptive floor- and façade-local room classification on Building 150 with
  source-safe x1–x4 bindings and no building-specific spacing constant.
- Independent glass roughness, reflectivity, tint, and artistic transmission.
- A real 56-variant x1 atlas and luminance-selected emission with independent
  per-depth-slice eligibility in both required renderer modes.
- One classifier assigning five ordered Interior Sets before room grouping,
  with independent x1–x4 resources and material profiles per stable Set ID.
- Staged structural editing, live per-Set material controls, and portable
  `.orms` scene-profile save/load.

The remaining work no longer concerns the core PIM mathematics, the Kit
extension boundary, or KRM-92. It concerns controlled performance evidence and
urban-scale validation.

### Phase 4: Productionisation — In progress

The production phase has completed Building 150 integration and the installed
Kit extension boundary. ORMS now has repeatable packaging, local-registry
publication, Extension Manager installation, AUTOLOAD, configuration,
diagnostics, and controlled lifecycle behaviour. Its remaining scope will:

- scale the workflow to a family of buildings assembled into several city
  blocks; and
- complete the controlled geometry-versus-ORMS performance benchmark.

---

## Planned Performance Validation

This benchmark is planned; no performance result is claimed yet. ORMS is
designed to reduce the amount of physical interior geometry and scene
complexity required for exterior-facing urban visualisation. Building 150 is
the fixed test asset, with 232 validated window apertures. A conventional
reference will use procedurally distributed instanced proxy interior assets
whose geometry budgets are derived from representative real-time or low-poly
furniture assets. The PIM version will use the same building, camera path, and
render settings.

The comparison will record GPU frame time or FPS, VRAM, scene load time, and
USD prim or instance count, plus geometry statistics where practical.

---

## Repository Structure

```text
exts/msp.orms.runtime/              # Canonical source and installable package
├── config/extension.toml           # Kit package metadata
├── data/mdl/                       # Production and diagnostic MDL
└── msp/orms/
    ├── classification/             # Kit-independent x1–x4 classification
    ├── interior_sets/              # Set identity, selectors, and resources
    ├── scene/                      # Reusable stage and Kit infrastructure
    ├── shared_room/                # OpenUSD runtime authoring
    └── runtime/                    # Extension service and reload entry
        ├── assignments/            # Mesh-assignment overrides and UI
        ├── interior_sets/          # Transactional atlas configuration
        ├── materials/              # MDL and Material Library integration
        ├── profiles/               # Portable scene profiles
        └── ui/                     # Window shell and artist controls
tests/
├── kit_extension/                  # Extension and lifecycle seams
├── shared_room_runtime/            # Classifier and OpenUSD fixtures
└── building_150_runtime/           # Production-building integration fixture
docs/
├── adr/                            # Architecture decisions
├── img/                            # Retained visual evidence
└── knowledge_base/mdl/             # Ordered implementation records
tools/                              # Repository utilities only
├── mcp/                            # Local documentation clients
├── package_orms_extension.py       # Standalone package builder
└── publish_orms_local_registry.py  # Registry publication workflow
```

This is a directory inventory, not a second architecture specification. Module
ownership and runtime flow are defined in
[Extension Architecture](#extension-architecture). The manual reload entry
point remains a development tool rather than the user launch path.

**Key Documentation**:

- [Knowledge Base](docs/knowledge_base/) — Start here for context
- [ADRs](docs/adr/) — Design decisions and trade-offs

---

## Engineering Evidence

The project includes a renderer-validated MDL parallax implementation with five
room faces, four depth slices, deterministic UDIM variation, and coherent
virtual rooms shared across flat, bay, and right-angle window groups. The same
runtime contract is retained in isolated Omniverse-authored and Houdini-exported
fixtures. A dedicated `roomUV` contract preserves ordinary asset UVs, while the
runtime classifier derives shared-room mappings without permanent edits to
source USD assets. Building 150 production integration now adds adaptive
x1–x4 grouping, real x1 content, independent glass controls, and selective
interior emission. The same system is packaged as an installable Kit extension
with registry installation, AUTOLOAD, Material Library integration, reversible
automatic assignment, central controls, external production-atlas routing,
version-safe upgrades, and symmetric teardown. Multi-building profiling and
controlled performance evidence remain separate boundaries; KRM-92 installed
acceptance is complete.

The retained evidence demonstrates:

✅ **Cross-ecosystem thinking** — Relating a Houdini reference workflow to a native OpenUSD/MDL implementation
✅ **Technical depth** — MDL internals, USD primvars, shader optimisation
✅ **Problem-solving focus** — Digital Twin use case drives technical choices
✅ **Research methodology** — Documentation-first, validate assumptions, iterate

**Technical areas covered**:

- NVIDIA MDL shader development
- USD/Omniverse pipeline integration
- Houdini, OpenUSD, and Omniverse interoperability
- Technical documentation and knowledge synthesis

---

## Getting Started

**For artists and extension users**: In a Kit application already connected to
the ORMS registry, install `Omniverse Room Map Shader` through Extension
Manager, enable `AUTOLOAD`, and open `Window > ORMS`. Artists do not run the
registry publication tool. The complete workflow is described in
[Install and Use the Kit Extension](#install-and-use-the-kit-extension).

**For extension developers and distributors**: See the
[extension README](exts/msp.orms.runtime/README.md), the publication section
above, the
[KRM-91 integration record](docs/knowledge_base/mdl/011_orms_kit_extension.md),
and the [KRM-92 delivery record](docs/knowledge_base/mdl/012_orms_ui_and_artist_workflow.md).

**For shader and OpenUSD developers**: See the
[Knowledge Base](docs/knowledge_base/) for the technical contracts.

**For researchers**: Check `docs/adr/` for design rationale

**First parallax baseline**: Open `tests/test_room_map_single.usda` in USD
Composer and follow the
[single-room parallax contract](docs/knowledge_base/mdl/005_single_room_parallax.md).

**Retained multi-window proof**: Open
`tests/shared_room_runtime/test_room_map_shared_rooms_omniverse.usda` and follow the
[shared-room contract](docs/knowledge_base/mdl/009_shared_multi_window_rooms.md).

**Current production integration**: Follow the
[Building 150 integration record](docs/knowledge_base/mdl/010_building_150_integration.md)
for the external-asset boundary, fixture, renderer evidence, material controls,
and completed validation sequence.

---

## Licensing

ORMS uses a mixed-licence distribution boundary:

- software and technical documentation are open source under the MIT License;
- the packaged x1–x4 debug atlases are reusable under CC BY 4.0;
- the Building 150 scene and reduced eight-tile demo atlas are source-available
  under the MSP Asset Evaluation License 1.0, which permits non-commercial
  evaluation, education, demonstrations, and attributed portfolio renders but
  not commercial use or standalone asset redistribution;
- the bundled Poly Haven HDRI remains available under CC0 1.0; and
- full production atlases and Houdini authoring sources are not distributed.

See [`LICENSE.md`](LICENSE.md) for the exact path-by-path scope,
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for provenance, and the
texts and references in [`LICENSES/`](LICENSES/). Public repository access does
not change the separate terms applied to demo and third-party assets.

---

## 📜 Technical Stack

- **Python**: 3.12 (repository baseline and Kit 110.1.2 embedded runtime)
- **NVIDIA MDL**: Core shader language
- **USD**: 23.11+ minimum compatibility baseline (primvars, stage composition)
- **Houdini**: 20.0+ (VEX reference implementation and OpenUSD export)
- **NVIDIA Omniverse Kit**: 110.1.2 (custom Kit application, MDL runtime, and RTX validation)

**Development Tools**:

- Pre-commit hooks (source hygiene, Python formatting, security, and tests)
- pytest (validation framework)
- Git LFS (for binary assets, if needed)

---

## 💖 Support This Research

If you find this work valuable:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/maxspell)

Your support funds:

- Continued parallax-interior mapping research
- Prototype shader development and testing
- Quality documentation and tutorials

---

## 📜 Changelog

* **Week of 31 August, 2026:** Completed the renderer-validated ORMS technical
  core and Building 150 production integration: adaptive x1–x4 rooms across
  232 apertures, source-safe material bindings, a 56-variant real x1 atlas,
  independent one-surface glass controls, luminance-selected per-slice
  emission, and accepted RTX Real-Time and RTX Interactive evidence; packaged
  the result as installable `msp.orms.runtime` with local-registry
  publication, Extension Manager installation, AUTOLOAD, Material Library,
  reversible automatic assignment, central ORMS controls, lifecycle commands,
  external production-atlas routing, clean source restoration, and the
  completed five-Set architecture with per-Set x1–x4 atlases, material
  profiles, staged editing, portable `.orms` scene profiles, and a canonical
  extension-owned Python and MDL source tree; followed through `1.0.1` with
  the bundled Building 150 demo, relative demo-profile resources, quiet
  production diagnostics, and an explicit mixed-licence distribution boundary.
* **Week of 24 August, 2026:** Extended the renderer-validated MDL parallax room from its named-primvar, camera-bridge, five-face, depth-slice, and UDIM baselines to automatically classified shared volumes across flat, bay, and right-angle Omniverse window groups.
* **Week of 17 August, 2026:** Re-inventoried the RnD workspace with Omniverse MCP reference helpers, updated validation and dependency configuration, and renewed the MDL and USD research baseline.
* **Week of 2 March, 2026:** Defined the hybrid USD primvar and dynamic-frame strategy, then formalised native MDL parallax-interior mapping, cross-layout projection, depth slices, instance variation, and surface integration.
* **Week of 16 February, 2026:** Refined the public project narrative, knowledge base, technical stack, support information, and privacy boundary for a clearer recruiter and engineer reading path.
* **Week of 9 February, 2026:** Added safer Jira-plan synchronisation and consolidated repository naming conventions for repeatable research delivery.
* **Week of 2 February, 2026:** Established the Room Map Shader RnD foundation with public research documentation, architecture decisions, isolated Python tooling, security guardrails, a test baseline, and reusable asset-hydration structure.


---

**Part of [NVIDIA Omniverse Showreel](https://github.com/MSP014/dt-omniverse-showreel-case01-msk)**
