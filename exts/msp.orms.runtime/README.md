# Omniverse Room Map Shader

`msp.orms.runtime` is the installable Kit boundary around the existing ORMS MDL
and OpenUSD runtime. The modules deliberately have separate ownership:

- `extension.py` is only the Kit entry point;
- `service.py` coordinates lifecycle and stage events;
- `resources.py` resolves packaged debug content and external production packs;
- `material_library.py` owns MDL and Material Library registration;
- `tools/omniverse/runtime/assignment.py` validates `Windows_Glass` meshes and
  owns their reversible Session Layer bindings.

## Installation

Publish the standalone package to a configured Kit extension registry. In
Extension Manager, install `Omniverse Room Map Shader`, enable it, and select
`AUTOLOAD`. Later application launches do not require `--ext-folder` or
`--enable`. The extension registers its material in Kit's Material Library and
can assign it to compatible ORMS window meshes.

By default, a mesh prim named `Windows_Glass` is assigned ORMS when it has the
complete `roomID`, `roomP`, `tangentu`, `tangentv`, and `roomUV` contract and
quad topology. A source material named `Windows_Glass` remains a compatibility
identity for older assets. The opinion lives in an ORMS-owned Session Layer,
so disabling the extension restores the source material. Authoring
`orms:autoAssign = false` on a mesh excludes it from the default pass.

The source-checkout extension uses `src/mdl/` and hydrated debug atlases without
copying them. A release bundle will materialise those canonical resources under
the extension's `data/` directory.

Build a standalone, non-overwriting extension directory with:

```powershell
conda run -n shader_rnd python tools/package_orms_extension.py `
  --output <new-output-directory>/msp.orms.runtime
```

The build copies only runtime Python, the two canonical MDL materials, and the
four public debug families. It emits `data/bundle_manifest.json` with SHA-256
digests and explicitly records that production atlases are not included.

A Kit App Template configured with a local filesystem registry can package and
publish ORMS directly:

```powershell
python tools/publish_orms_local_registry.py `
  --kit-app-root E:\path\to\kit-app-template
```

## Texture boundary

Public diagnostic x1–x4 atlases belong under `data/atlases/debug/`. Full
production atlases remain in a separately licensed external pack. Four
persistent x1–x4 directory settings point at those external families. ORMS
discovers each UDIM asset pattern and its consecutive tiles automatically.
See [data/atlases/README.md](data/atlases/README.md) for the exact contract.
