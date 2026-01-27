# ADR 001: Naming Convention & Standards

## Status

Accepted

## Context

Inconsistent naming and documentation styles across files and repositories lead to pipeline friction. For **Room Map Shader RnD**, we need a standardised grammar to manage shader code, textures, and test scenes.

## Decision

We will enforce the following naming and operational rules:

### 1. Repository Naming

Format: `room_shader_rnd`

* **Example:** `room_shader_rnd` (this workspace).
* **Remote:** `https://github.com/MSP014/room_shader_rnd.git`

### 2. File Layers (Snake Case)

* `mdl_*` (Material Definition Language files)
* `tex_*` (Textures / Atlases)
* `sd_*` (Substance Designer files)
* `test_*` (Test scenes)

### 3. Extensions

* `.mdl`: Shader code.
* `.usda`: ASCII Test scenes.
* `.png`/`.exr`: Texture inputs (EDR preferred for depth).

### 4. Language Standards

* **Documentation**: All technical documentation and comments MUST be in **British English** (en-GB). Use `s` instead of `z` (e.g., *optimise*, *standardise*).
* **Commit Messages**: British English, imperative mood (e.g., "Add feature", not "Added feature").

### 5. Git Workflow

* **Branches**: `feature/description-of-change` or `fix/issue-id`.
* **Tags**: Use semantic versioning for milestones (e.g., `v1.0.0`).

## Consequences

* **Positive:** Predictable file system, clear separation of shader vs scene data, and consistent international documentation code.
* **Negative:** Requires initial setup discipline.
