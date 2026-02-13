# Knowledge Base — Karma Room Map Shader to MDL

This knowledge base provides reference links and analysis for translating Houdini's Karma Room Map Shader (VEX) to NVIDIA MDL.

> **Note**: Full documentation copies are maintained locally in `houdini/` directory (gitignored) for research purposes. Public repository contains only references to official sources.

---

## 📚 Official Documentation Sources

### Houdini / SideFX Documentation

**Houdini Version**: 21.0
**Last Verified**: 2026-02-13

#### Core Documentation

1. **[Karma Room Map Shader - Workflow Guide](https://www.sidefx.com/docs/houdini/solaris/support/karma_room_map.html)** ★ Start Here
   - Complete tutorial with setup instructions
   - Single-window, multi-window, and curved surface workflows
   - Troubleshooting guide
   - MaterialX integration examples

2. **[Karma Room Map VOP](https://www.sidefx.com/docs/houdini/nodes/vop/kma_roommap.html)**
   - Core shader node reference
   - Cross-shaped texture layout specification
   - Slice system for depth layering
   - UDIM support for randomization

3. **[Room Map Frame SOP](https://www.sidefx.com/docs/houdini/nodes/sop/roommapframe.html)**
   - Geometry setup node (critical!)
   - Generates primitive attributes: `tangentu`, `tangentv`, `roomN`, `roomP`
   - Defines local coordinate basis for projection

4. **[Karma Room Lens VOP](https://www.sidefx.com/docs/houdini/nodes/vop/kma_roomlens.html)**
   - Baking tool for generating interior maps
   - Not directly relevant for MDL translation (Houdini-specific)

### Images

Documentation images are stored in [`houdini/images/`](./houdini/images/) with descriptive filenames.

> **⚠️ TODO**: Download images from SideFX documentation and save to `images/` directory.
> See individual `.md` files for list of required images.

---

## 🔗 External Sources

All external documentation sources with URLs and retrieval dates are tracked in [`_sources.md`](./_sources.md).

---

## 🎯 Translation Strategy

For the VEX to MDL translation strategy document, see:

**[`../vex_to_mdl_strategy.md`](../vex_to_mdl_strategy.md)** (To be created)

This document will synthesize findings from the knowledge base into actionable translation steps.

---

## 📝 Quick Reference

### Key VEX Concepts

- **Primitive Attributes**: `tangentu`, `tangentv`, `roomN`, `roomP`
- **Cross-Shaped Texture Layout**: Walls + ceiling + floor + 4 slices
- **UDIM Support**: For randomization across windows
- **Parallax Projection**: Creates 3D illusion from 2D texture

### MDL Translation Challenges

1. **Primitive attributes** → USD primvars or `state::` functions
2. **Local coordinate basis** → Manual matrix construction
3. **Cross-shaped UV layout** → Custom texture coordinate math
4. **Parallax offset** → Standard parallax algorithms

See [Karma Room Map VOP - Technical Notes](./houdini/karma_room_map_vop.md#technical-notes-for-vex-mdl-translation) for detailed analysis.

---

## 📊 Documentation Status

| Document | Status | Images | Notes |
| -------- | ------ | ------ | ----- |
| Workflow Guide | ✅ Complete | ⚠️ Pending | Comprehensive tutorial |
| Room Map VOP | ✅ Complete | ⚠️ Pending | Node reference |
| Room Lens VOP | ✅ Complete | ⚠️ Pending | Baking tool |

> **Note**: Full workflow examples and detailed parameter descriptions are available in the official SideFX documentation above.

### Technical Implementation Details

#### Critical VEX Concepts for Translation

**Primitive Attributes** (from Room Map Frame SOP):

- `tangentu`, `tangentv` — Local UV basis vectors
- `roomN` — Surface normal
- `roomP` — Reference position

**Texture Layout**:

- Cross-shaped pattern (center = back wall, left/right = side walls, top = ceiling, bottom = floor)
- 4 corner slices for depth-layered props

**UDIM Support**:

- Randomization across multiple windows
- Offset parameters for procedural variation

#### Implementation Challenges for MDL

| VEX Feature                                          | MDL Approach                              | Complexity |
| ---------------------------------------------------- | ----------------------------------------- | ---------- |
| Primitive attributes                                 | USD primvars or `state::` functions       | Medium     |
| Cross-shaped UV layout                               | Custom texture coordinate math            | Low        |
| Parallax projection                                  | Standard parallax algorithms              | Medium     |
| UDIM support                                         | `tex::lookup_*()` with UDIM               | Low        |

---

## 📊 Research Status

| Phase | Status | Notes |
| ----- | ------ | ----- |
| Documentation Research | ✅ Complete | 4 core SideFX pages identified |
| Local Knowledge Base | ✅ Complete | Detailed notes maintained locally |
| VEX → MDL Strategy | 🔴 Not Started | Next step |

---

## � Additional Resources

- [NVIDIA MDL Documentation](https://raytracing-docs.nvidia.com/mdl/introduction/index.html)
- [USD Primvars Specification](https://graphics.pixar.com/usd/release/api/class_usd_geom_primvar.html)
- [MaterialX Standard Surface](https://materialx.org)
