# ORMS Atlas Resource Boundary

The installable extension keeps only public diagnostic content beneath this
directory:

```text
data/atlases/debug/
├── x1/room_map_debug.<UDIM>.png
├── x2/room_map_debug_x2.<UDIM>.png
├── x3/room_map_debug_x3.<UDIM>.png
└── x4/room_map_debug_x4.<UDIM>.png
```

Each debug family contains tiles `1001` through `1008` and reports eight
variants. These textures are suitable for validation and examples, not as the
production interior library.

Production Room Map atlases do not live in this extension or in the public
repository. Install an independently licensed asset pack and point each room
family setting at the directory containing that family's textures:

```text
/persistent/exts/msp.orms.runtime/atlases/xN/directory
```

The directory must contain exactly one continuous UDIM sequence beginning at
tile `1001`. ORMS derives the `<UDIM>` asset pattern and uses every consecutive
tile, so artists do not enter filenames or variant counts. A blank xN setting
retains the packaged debug family for that room size.

The production pack manifest and final filenames belong to KRM-96. Houdini
authoring files remain outside both distribution zones.
