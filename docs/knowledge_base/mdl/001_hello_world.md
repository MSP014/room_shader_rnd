# MDL Hello World in Omniverse

## Purpose

`src/mdl/hello_world.mdl` is the minimal material-authoring proof for the
Room Map Shader RnD. It exports `hello_world`, a red diffuse material written
against MDL 1.7.

`assets/_external/usd/hello_world_material.usda` is a self-contained USD stage that
bounds a cube to this material. The MDL source asset is addressed relative to
the test stage, so the scene remains portable inside this repository.

## Material contract

The material deliberately has one artist-facing parameter:

| Parameter | Type | Default | Purpose |
| --- | --- | --- | --- |
| `diffuse_colour` | `color` | `(1.0, 0.0, 0.0)` | Confirms that a hand-authored MDL module is resolved and rendered. |

The material uses `df::diffuse_reflection_bsdf` with zero roughness. It has no
textures, primvars, or Room Map logic; those belong to later tasks.

## Assigning the material in Omniverse

1. Open `assets/_external/usd/hello_world_material.usda` in USD Composer.
2. Confirm that `/World/Cube` has the material binding
   `/World/Looks/HelloWorld`.
3. Select the material's `Shader` prim. Its source asset must resolve to
   `../../../src/mdl/hello_world.mdl`, with `hello_world` as the subidentifier.
4. In Render Settings, select **RTX - Real-Time** and confirm the illuminated
   cube is red.
5. Select **RTX - Interactive (Path Tracing)** and confirm the cube remains
   red after accumulation.

## Known gotchas

- MDL modules must be reachable through the USD asset resolver. Keep the test
  stage and `src/mdl/hello_world.mdl` in their repository-relative locations.
- The USD material connection uses `outputs:mdl:surface`; a generic
  `outputs:surface` connection is not the MDL renderer contract used here.
- A diffuse material requires scene illumination. The test stage includes a
  `DomeLight` for this reason.
- If the module or subidentifier does not resolve, inspect the Shader prim's
  `info:mdl:sourceAsset` and `info:mdl:sourceAsset:subIdentifier` fields
  before changing the material code.

## Validation record

The stage and its material binding are checked by
`tests/test_hello_world_material.py`.

Visual validation completed on 18 August 2026:

- **RTX - Real-Time:** the illuminated cube rendered red.
- **RTX - Interactive (Path Tracing):** the illuminated cube remained red
  during path-tracing accumulation.
