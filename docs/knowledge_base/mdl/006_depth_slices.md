# Depth-Slice Cross-Atlas Material Contract

## Record

| Field | Value |
| --- | --- |
| Jira | KRM-89 — Depth Slices and Artist-Facing MDL Material Node |
| Implementation | `exts/msp.orms.runtime/data/mdl/room_map.mdl` |
| Automated evidence | `tests/test_room_map_slices.py` |
| Validation scene | `tests/test_room_map_slices.usda` |
| Evidence state | Renderer-validated |
| Last validated | 23 August 2026 |

## Purpose

The public `room_map` material extends the accepted five-face room with up to
four alpha-composited analytic depth slices while retaining one normalised test
window.

## Accepted contract

### Material inputs

| Input | Default | Contract |
| --- | --- | --- |
| `room_atlas` | empty | Cross-atlas containing five room faces and S1–S4 regions. |
| `room_depth` | `1` | Distance from the window plane to the back plane. |
| `window_shift` | `(0, 0)` | Normalised U/V offset applied before ray construction. |
| `enable_slice_1…4` | `true` | Enables the corresponding slice sample. |
| `slice_N_depth_percent` | `20`, `40`, `60`, `80` | Clamped position from window `0` to back plane `100`. |
| `slice_N_offset` | `(0, 0)` | Local U/V offset inside slice N. |
| `slice_N_scale` | `(1, 1)` | Local U/V scale inside slice N. |
| `fallback_colour` | magenta | Invalid room-frame diagnostic. |
| `camera_position_world` | `(0, 0, 0)` | Session Layer input maintained by the camera bridge. |
| `emission_strength` | `1` | Diagnostic visibility. |

Slice coordinates are `hit_uv * scale + offset`. Coordinates outside the unit
slice are discarded before sampling, and `tex::wrap_clip` prevents atlas-edge
sampling.

### Atlas and compositing

The five accepted room regions remain Back at centre, Left and Right at the
middle sides, Ceiling at top centre, and Floor at bottom centre. The four
corners are:

| Slice | Region | Default depth |
| --- | --- | --- |
| S1 | Bottom left | 20% |
| S2 | Top left | 40% |
| S3 | Top right | 60% |
| S4 | Bottom right | 80% |

Each enabled slice is intersected analytically with the view ray, clipped to
the room, sampled, and alpha-composited over farther slices and the room face.
Edited geometric depth, not slice number, determines front-to-back order.
Equal depths use a deterministic S4-to-S1 tie order.

This is analytic plane intersection and alpha compositing, not ray marching.
The shader performs one room-face lookup plus four possible slice lookups.

## Evidence

`tests/test_room_map_slices.usda` uses the green tile
`assets/_external/tex/room_map_debug/room_map_debug.1002.png`, making slice
work visually distinct from the red five-face baseline. Automated checks
retain the inputs, atlas regions, compositing source, and lookup budget.

## Reproduction

Open `tests/test_room_map_slices.usda`, start the camera bridge for
`/World/Looks/RoomMap/Shader.inputs:camera_position_world`, and check both RTX
Real-Time and RTX Interactive (Path Tracing):

1. disable all slices to recover the five-face baseline;
2. enable one slice at a time to confirm its corner region and alpha;
3. enable all slices at `20/40/60/80%`;
4. reorder at least two depth values and confirm the nearer slice stays in
   front;
5. change one offset and scale and confirm that only its slice changes.

## Validation record

On 23 August 2026, the material resolved in Material Graph and rendered in
both required modes. The green atlas confirmed all room faces and four alpha
slices. A second check with S1 `99%`, S2 `72%`, S3 `24%`, and S4 `9%`
confirmed geometric rather than numeric slice ordering.

## Boundary

This record remains limited to one normalised window, five room faces, and four
slices. It does not prove facade integration, physical aperture aspect,
multi-room variation, shared rooms, or performance against physical geometry.
