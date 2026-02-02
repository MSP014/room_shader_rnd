# ADR 005: Asset Life Cycle & Hydration

## Status

Accepted

## Context

We deal with heavy texture atlases (EXR/PNG sequences) and USD caches that are unsuitable for Git storage. We need a reliable way to "hydrate" the repository with these heavy assets while protecting our internal procedural source code (`.hip` flows).

## Decision

We will implement a **Hydration Protocol** to reconstruct the operational environment:

1. **Structure**: The repository contains a pre-built skeleton at `assets/_external/` (anchored by `.gitkeep` files).
    * `assets/_external/usd/`
    * `assets/_external/tex/`
    * `assets/_external/hdri/`
2. **External Storage**: Runtime assets (USD, Textures) are hosted on external storage (One Drive / S3).
3. **Prohibited Items**: Proprietary source files (Houdini `.hip`, Nuke Scripts) are **EXCLUDED** from public distribution. They are for internal use only.
4. **Hydration**: The user downloads the Asset Pack and extracts it directly into the existing `assets/_external/` directory.
5. **Relative Path Integrity**: Every USD reference and Python script path MUST use relative paths (e.g., `../assets/_external/usd/asset.usd`). Absolute paths are strictly forbidden.

## Consequences

* **Positive:** "It Just Works" experience for the user (no manual mkdir), strict IP protection for source files.
* **Negative:** User must download a large ZIP file before the scene works.
