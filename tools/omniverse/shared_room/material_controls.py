"""Define the single persistent control set shared by all ORMS materials."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pxr import Gf

MATERIAL_SETTINGS_ROOT = "/persistent/exts/orms/material"


@dataclass(frozen=True)
class MaterialControl:
    """Describe one artist-facing value and its runtime shader input."""

    group: str
    label: str
    name: str
    kind: str
    default: object
    minimum: float | None = None
    maximum: float | None = None


MATERIAL_CONTROLS = (
    MaterialControl("Room", "Variation seed", "variation_seed", "int", 0),
    MaterialControl(
        "Room", "Room depth", "room_depth", "float", 1.0, 0.01, 100.0
    ),
    MaterialControl(
        "Room",
        "Uniform scale",
        "room_uniform_scale",
        "float",
        1.0,
        0.01,
        100.0,
    ),
    MaterialControl(
        "Window", "Window shift", "window_shift", "float2", (0.0, 0.0)
    ),
    MaterialControl(
        "Window",
        "Aperture scale",
        "window_aperture_scale",
        "float2",
        (1.0, 1.0),
        0.001,
        10.0,
    ),
    MaterialControl(
        "Window",
        "Aperture offset",
        "window_aperture_offset",
        "float2",
        (0.0, 0.0),
    ),
    *tuple(
        MaterialControl(
            "Depth slices",
            f"Enable slice {index}",
            f"enable_slice_{index}",
            "bool",
            True,
        )
        for index in range(1, 5)
    ),
    *tuple(
        MaterialControl(
            "Depth slices",
            f"Slice {index} depth (%)",
            f"slice_{index}_depth_percent",
            "float",
            float(index * 20),
            0.0,
            100.0,
        )
        for index in range(1, 5)
    ),
    *tuple(
        MaterialControl(
            "Depth slices",
            f"Slice {index} offset",
            f"slice_{index}_offset",
            "float2",
            (0.0, 0.0),
        )
        for index in range(1, 5)
    ),
    *tuple(
        MaterialControl(
            "Depth slices",
            f"Slice {index} scale",
            f"slice_{index}_scale",
            "float2",
            (1.0, 1.0),
            0.001,
            10.0,
        )
        for index in range(1, 5)
    ),
    MaterialControl(
        "Glass", "Roughness", "glass_roughness", "float", 0.1, 0.0, 1.0
    ),
    MaterialControl(
        "Glass",
        "Reflectivity",
        "glass_reflectivity",
        "float",
        0.04,
        0.0,
        1.0,
    ),
    MaterialControl("Glass", "Tint", "glass_tint", "colour3", (1.0, 1.0, 1.0)),
    MaterialControl(
        "Glass",
        "Transmission",
        "glass_transmission",
        "float",
        1.0,
        0.0,
        1.0,
    ),
    MaterialControl(
        "Diagnostics",
        "Fallback colour",
        "fallback_colour",
        "colour3",
        (1.0, 0.0, 1.0),
    ),
    MaterialControl(
        "Emission", "Enable emission", "enable_emission", "bool", False
    ),
    *tuple(
        MaterialControl(
            "Emission",
            f"Emission slice {index}",
            f"emission_slice_{index}",
            "bool",
            True,
        )
        for index in range(1, 5)
    ),
    MaterialControl(
        "Emission",
        "Strength",
        "emission_strength",
        "float",
        1.0,
        0.0,
        100.0,
    ),
    MaterialControl(
        "Emission",
        "Threshold",
        "emission_threshold",
        "float",
        0.8,
        0.0,
        1.0,
    ),
    MaterialControl(
        "Emission",
        "Softness",
        "emission_softness",
        "float",
        0.1,
        0.0,
        1.0,
    ),
)


def material_setting_path(name: str) -> str:
    """Return the persistent path for one shared material control."""

    return f"{MATERIAL_SETTINGS_ROOT}/{name}"


def ensure_material_setting_defaults() -> None:
    """Create typed Kit defaults without overwriting persistent choices."""

    import carb.settings

    settings = carb.settings.get_settings()
    for control in MATERIAL_CONTROLS:
        path = material_setting_path(control.name)
        if settings.get(path) is not None:
            continue
        if control.kind in {"float2", "colour3"}:
            settings.set_float_array(path, list(control.default))
        else:
            settings.set_default(path, control.default)


def material_input_values_from_mapping(
    values: Mapping[str, object],
) -> dict[str, object]:
    """Coerce persistent scalar and vector values to their USD input types."""

    result = {}
    for control in MATERIAL_CONTROLS:
        value = values.get(control.name, control.default)
        if control.kind == "bool":
            result[control.name] = bool(value)
        elif control.kind == "int":
            result[control.name] = int(value)
        elif control.kind == "float":
            result[control.name] = float(value)
        elif control.kind == "float2":
            result[control.name] = Gf.Vec2f(*value)
        elif control.kind == "colour3":
            result[control.name] = Gf.Vec3f(*value)
        else:
            raise ValueError(
                f"Unknown ORMS material control kind: {control.kind}"
            )
    return result


def material_input_values_from_kit() -> dict[str, object]:
    """Read the shared persistent values consumed by runtime materials."""

    import carb.settings

    ensure_material_setting_defaults()
    settings = carb.settings.get_settings()
    return material_input_values_from_mapping(
        {
            control.name: settings.get(material_setting_path(control.name))
            for control in MATERIAL_CONTROLS
        }
    )
