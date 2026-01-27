# Room Map Shader RnD: Parallax Interior Mapping (MDL)

> [!WARNING]
> **Work in Progress:** This project is currently under active development. This is a research component for the NVIDIA Showreel (Case 01).

---

> **Role:** Graphics Research (Shader RnD)
> **Stack:** NVIDIA MDL, Houdini (Karma), Python 3.10
> **Persona:** Quentin (Sr. Graphics Research Engineer)

---

## 📋 Project Overview

This repository hosts the **Research & Development** efforts for a custom **Parallax Interior Mapping** solution using NVIDIA MDL. The goal is to create a high-performance, view-dependent depth slicing shader for simulating complex interior spaces in Urban Digital Twins (specifically for [Case 01: Moskovsky Av](https://github.com/MSP014/dt-omniverse-showreel-case01-msk)).

**Key Research Objective:**
To implement a "Window Box" effect that accurately simulates room interiors behind building facades without the geometry overhead, utilizing **View-Dependent Depth Slicing** and **texture-bombing** for randomization.

**Project Focus:**

- **Performance:** Minimizing texture lookups while maximizing visual fidelity.
- **Portability:** Creating a generic MDL module usable across Omniverse apps.
- **Proceduralism:** Generating compatible texture atlases via Houdini (Karma/VEX).

---

## 🎯 Technical Highlights

*This R&D module supports the "Smart Urban Fabric" initiative by providing lightweight visual complexity.*

- **MDL Architecture:** Custom functions for parallax correction and layer blending.
- **Houdini Pipeline:** Tools to bake room slices and depth maps into optimized atlases.
- **Verification:** Unit testing shader logic via `.usda` scenes and Python-driven validation.

---

## 🏗️ Architecture & Decisions

This project follows the **Nvidia Showreel Standard** to ensure consistency and reliability.

- [**View Architecture Decision Records (ADR)**](docs/adr/) – Design notes on Naming Conventions, QA/Security Guardrails, and Dependency Locking.

### Core Components

| Component | Description |
| :--- | :--- |
| **src/mdl/** | The core MDL shader definitions. |
| **src/houdini/** | VEX snippets and HDA logic for atlas generation. |
| **docs/plans/** | Technical implementation details and debt tracking. |

---

## 📂 Repository Structure

```text
.
├── docs/        # ADRs, Research Notes, and Plans
├── src/         # Source code (MDL, Python, VEX)
├── tests/       # Validation scenes (*.usda) and pytest scripts
├── tools/       # Pipeline tools (Jira, Automation)
└── requirements.txt # Locked dependencies (Python 3.10)
```

---

## 🛠️ Setup & Installation

1. **Clone:** `git clone https://github.com/MSP014/room_shader_rnd.git`
2. **Env:** Create conda env: `conda create -n shader_rnd python=3.10`
3. **Deps:** `pip install -r requirements.txt`
4. **Hooks:** `pre-commit install`

---

## 📜 Changelog

- **2026-01-27:** Initial repository bootstrap. Established **Nvidia Showreel Standard** (ADRs, Pre-commit, strict PEP 8).
