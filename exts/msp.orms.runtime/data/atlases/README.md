# ORMS Atlas Resource Boundary

The installable extension keeps only public diagnostic content beneath this
directory:

```text
data/atlases/debug/
|-- x1/room_map_debug.<UDIM>.png
|-- x2/room_map_debug_x2.<UDIM>.png
|-- x3/room_map_debug_x3.<UDIM>.png
`-- x4/room_map_debug_x4.<UDIM>.png
```

Each debug family contains tiles `1001` through `1008` and reports eight
variants. These textures are suitable for validation and examples, not as the
production interior library.

Production Room Map atlases do not live in this extension or in the public
repository. Install an independently licensed asset pack and point each
Interior Set family at the directory containing that family's textures:

```text
/persistent/exts/msp.orms.runtime/interior_sets/
  slots/<active_slot>/sets/<set_id>/atlases/xN/directory
```

The directory must contain exactly one continuous UDIM sequence beginning at
tile `1001`. ORMS derives the `<UDIM>` asset pattern and uses every consecutive
tile, so artists do not enter filenames or variant counts. A blank xN setting
retains the packaged debug family for that room size.

Each production directory also provides `orms_variants.json`:

```json
{
  "version": 1,
  "namespace": "production-library-id",
  "variant_ids": ["room-001", "room-002"]
}
```

The x1-x4 families used by one Interior Set must expose the same namespace and
ordered variant IDs. ORMS reports an incoherent production library instead of
rejecting unrelated structural edits. An invalid family uses its matching
packaged debug fallback; a cross-family corner whose identity cannot be proven
is decomposed into safe independent groups instead of showing mismatched room
sides. Legacy folders without manifests therefore remain usable for
single-family rooms while being reported as unverified.

Production atlases and Houdini authoring files remain outside this public
distribution boundary.
