# Parallax Interior Mapping for NVIDIA Omniverse

> Bringing Houdini's Room Map Shader to NVIDIA MDL for scalable Urban Digital Twins

**Status**: MDL parallax and depth-slice baselines validated • Production integration in progress

---

## The Problem

Urban Digital Twins face a fundamental challenge: **realistic building interiors at scale**.

A single city block contains hundreds of windows. Each window reveals an
interior — furniture, wall art, lighting fixtures. At façade scale, direct
interior geometry creates a trade-off between scene detail, authoring effort,
and runtime budgets:

- **Interior geometry at façade scale**: A façade containing hundreds of visible rooms can require thousands of placed furniture and prop instances even when the underlying asset library is efficiently reused through instancing. Room mapping investigates whether that interior scene complexity can be replaced by material-evaluated virtual rooms on the existing window surfaces.
- ❌ **Black windows**: Unrealistic, breaks immersion in high-fidelity Digital Twins
- ❌ **Reflective/curtain fallback**: Works for distant views, fails at street level

**The solution exists** — but in the wrong ecosystem.

---

## The Solution: Parallax Interior Mapping

Houdini's **Room Map Shader** solves this elegantly: render interiors into specialized textures, then use shader math to create a convincing 3D illusion. The technique is called **parallax mapping** — view-dependent depth perception from 2D data.

**How it works:**

1. Bake interior scenes into a cross-shaped texture atlas (walls, ceiling, floor + depth slices)
2. Geometry preprocessing computes per-window tangent space
3. Fragment shader uses view direction to sample correct texture region, creating parallax effect

**The intended production result**: large numbers of visually varied virtual
interiors evaluated on existing window surfaces rather than modelled as full
interior geometry.

**The catch**: This technique is written in **VEX** (Houdini's procedural language), tightly coupled to Houdini's production renderer. NVIDIA Omniverse uses **MDL** (Material Definition Language).

---

## This Research: VEX → MDL Translation

**Goal**: Adapt Houdini's Room Map approach to NVIDIA MDL, enabling Omniverse-based Digital Twins to benefit from lightweight interior rendering.

**Why this matters:**

- **For Digital Twins**: Scalable urban interiors with reduced geometry and scene-complexity requirements
- **For NVIDIA**: Demonstrates MDL's capability to handle advanced procedural techniques from other ecosystems
- **For the industry**: Cross-DCC interoperability — workflows shouldn't be siloed by renderer choice

> [!NOTE]
> **On Technique vs. Implementation**
>
> **Parallax interior mapping** is a well-established rendering technique used across game engines (Unreal, Unity), shading languages (OSL, GLSL), and DCC tools. SideFX's contribution is their specific **VEX implementation** for Karma, not the invention of the underlying algorithm.
>
> This research focuses on **adapting the concept** to NVIDIA MDL — studying how to achieve similar results using MDL's architecture, not copying proprietary code. The goal is cross-ecosystem knowledge transfer, enabling Omniverse users to benefit from proven techniques regardless of their origin.
>
> Credit to SideFX for their excellent documentation and implementation, which serves as the reference for this translation work.

---

## Visual Baseline and Transformation Path

This RnD begins with a digital replica of Building 150 on Moskovsky Avenue in
Saint Petersburg, prepared as a USD asset for Omniverse. The work will evolve
its flat glazing into a scalable parallax-interior system for the Case 01 Urban
Digital Twin.

![Starting asset — Building 150 on Moskovsky Avenue in Omniverse](docs/img/msk_150_omniverse.jpg)

*Starting asset: the Omniverse USD building before Room Map geometry context,
MDL parallax mapping, and interior variation are introduced.*

### First MDL Parallax Proof

The first functional MDL vertical slice uses a one-by-one test window to sample
a labelled cross-atlas and form a view-dependent virtual room. The baseline and
diagnostic texture establish the test contract; the applied material views then
show the changing visible faces in USD Composer with RTX Interactive (Path
Tracing).

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

### Current Prototype Boundary

#### Validated now

- One normalised `1 × 1` test window.
- Five virtual room faces: Back, Left, Right, Ceiling, and Floor.
- Four alpha-composited virtual depth slices: S1, S2, S3, and S4.
- Named USD frame primvars: `roomP`, `tangentu`, and `tangentv`.
- Active-camera runtime bridge and cross-atlas mapping.
- Editable per-slice enable, depth, offset, and scale controls.
- Correct face assignment, orientation, and depth sorting in RTX Real-Time and
  RTX Interactive (Path Tracing).

#### Not implemented yet

- Multi-room or UDIM variation.
- Production glass integration.
- Arbitrary real-world window dimensions and aspect handling.
- Full Building 150 façade integration.
- A geometry-versus-Room-Map performance benchmark.

---

## Technical Challenge: No Direct Translation Path

Houdini's original workflow and the MDL port meet different geometry, material,
and runtime constraints:

### 1. **Room Frame Data in MDL**

Houdini exports `roomP`, `tangentu`, and `tangentv` as named USD `float3`
primvars. The validated MDL baseline reads them with
`nvidia::support_definitions::data_lookup_float3()`, constructing the room
frame from the exported data rather than transporting it through texture
coordinate channels.

`nvidia::support_definitions` is an Omniverse-specific dependency of this
implementation. The named-primvar path has been visually validated in RTX
Real-Time and RTX Interactive (Path Tracing); the detailed evidence is in the
[primvar access diagnostic](docs/knowledge_base/mdl/004_primvar_access.md).

Dynamic frame construction with `state::texture_tangent_u()` and
`state::normal()`, or explicitly assigned texture-coordinate channels, remain
compatibility options for environments that cannot provide the NVIDIA support
definitions module. They are not the current primary path.

---

### 2. **Camera Position Runtime Bridge**

`state::direction()` was tested and does not provide the material view direction
required for Room Map. Instead, `tools/omniverse/camera_position_bridge.py`
obtains the active Kit or Composer camera world position and writes it to the
`camera_position_world` material input in the USD **Session Layer**. Camera
motion therefore does not become a permanent edit to the source USD scene.

The diagnostic view vector is
`camera_position_world - surface_position_world`. The Room Map material
transforms both positions into the room frame before constructing its ray. See
the [state-function diagnostics](docs/knowledge_base/mdl/002_state_functions.md)
and [camera bridge contract](docs/knowledge_base/mdl/003_camera_position_bridge.md)
for the detailed validation record.

---

### 3. **Current Five-Face Analytic Parallax Baseline**

`room_map_single.mdl` currently performs a single-room analytic projection:

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

## Research Progress

### Phase 1: Documentation & Analysis — Complete

The [Knowledge Base](docs/knowledge_base/) and ADRs document the Houdini
reference, the Room Map coordinate contract, and the MDL translation decisions.

### Phase 2: MDL / USD Integration Strategy — Baseline validated

The validated integration contracts now include:

- Houdini-exported USD frame primvars.
- MDL named `float3` primvar lookup.
- Active-camera runtime bridge.
- Room-space view-ray construction.
- Cross-atlas face projection.

### Phase 3: Prototype Implementation — In progress

The renderer-validated prototype supports:

- One normalised test window.
- Five virtual room faces:
  - Back
  - Left
  - Right
  - Ceiling
  - Floor
- Four alpha-composited S1–S4 depth slices with editable depth, offset, and
  scale controls.
- Cross-atlas sampling and view-dependent parallax.
- RTX Real-Time validation.
- RTX Interactive (Path Tracing) validation.

---

## Planned Performance Validation

This benchmark is planned; no performance result is claimed yet. Building 150
will be the fixed test asset, with approximately 250 visible windows or
apparent rooms. A conventional reference will use procedurally distributed
instanced proxy interior assets whose geometry budgets are derived from
representative real-time or low-poly furniture assets. The Room Map version
will use the same building and camera path.

The comparison will record GPU frame time or FPS, VRAM, scene load time, and
USD prim or instance count.

---

## Repository Structure

```text
docs/
├── adr/                    # Architecture Decision Records
├── img/                    # Visual proof captures and diagnostic atlas
└── knowledge_base/
    └── mdl/                # MDL diagnostics and implementation contracts

src/
└── mdl/                    # Room Map prototype and diagnostic MDL modules

tests/                      # USD validation scenes and Python contract tests

tools/
└── omniverse/              # Runtime camera-position bridge
```

**Key Documentation**:

- [Knowledge Base](docs/knowledge_base/) — Start here for context
- [ADRs](docs/adr/) — Design decisions and trade-offs

---

## For NVIDIA Recruiters

The project now includes a renderer-validated MDL parallax prototype: a
single normalised window projects a five-face virtual room from a labelled
cross-atlas in both supported RTX validation modes. Production façade
integration and performance measurement remain separate planned work.

This project demonstrates:

✅ **Cross-ecosystem thinking** — Bridging Houdini ↔ Omniverse workflows
✅ **Technical depth** — MDL internals, USD primvars, shader optimization
✅ **Problem-solving focus** — Digital Twin use case drives technical choices
✅ **Research methodology** — Documentation-first, validate assumptions, iterate

**Current skills showcased**:

- NVIDIA MDL shader development
- USD/Omniverse pipeline integration
- Cross-DCC workflows (Houdini ↔ Omniverse)
- Technical documentation and knowledge synthesis

---

## Getting Started

**For developers**: See [Knowledge Base](docs/knowledge_base/) for technical deep dive

**For researchers**: Check `docs/adr/` for design rationale

**Validation baseline**: Open `tests/test_room_map_single.usda` in USD
Composer and follow the [single-room parallax contract](docs/knowledge_base/mdl/005_single_room_parallax.md).

---

## 📜 Technical Stack

- **Python**: 3.10
- **NVIDIA MDL**: Core shader language
- **USD**: 23.11+ (primvars, stage composition)
- **Houdini**: 21.0 (VEX reference implementation)
- **NVIDIA Omniverse**: 2024.x (MDL runtime, validation)

**Development Tools**:

- Pre-commit hooks (markdown linting, Python formatting)
- pytest (validation framework)
- Git LFS (for binary assets, if needed)

---

## 💖 Support This Research

If you find this work valuable:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/maxspell)

Your support funds:

- Continued VEX → MDL translation research
- Prototype shader development and testing
- Quality documentation and tutorials

---

## 📜 Changelog

* **Week of 17 August, 2026:** Re-inventoried the RnD workspace with Omniverse MCP reference helpers, updated validation and dependency configuration, and renewed the MDL and USD research baseline.
* **Week of 2 March, 2026:** Defined the hybrid USD primvar and dynamic-frame strategy, then formalised native MDL parallax-interior mapping, cross-layout projection, depth slices, instance variation, and surface integration.
* **Week of 16 February, 2026:** Refined the public project narrative, knowledge base, technical stack, support information, and privacy boundary for a clearer recruiter and engineer reading path.
* **Week of 9 February, 2026:** Added safer Jira-plan synchronisation and consolidated repository naming conventions for repeatable research delivery.
* **Week of 2 February, 2026:** Established the Room Map Shader RnD foundation with public research documentation, architecture decisions, isolated Python tooling, security guardrails, a test baseline, and reusable asset-hydration structure.


---

**Part of [NVIDIA Omniverse Showreel](https://github.com/MSP014/dt-omniverse-showreel-case01-msk) | Research by Max Spell**
