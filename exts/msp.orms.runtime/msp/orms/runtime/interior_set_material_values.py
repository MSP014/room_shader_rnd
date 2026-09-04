"""Validate Set-scoped material values at every external boundary."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from tools.omniverse.shared_room.material_controls import MATERIAL_CONTROLS

_CONTROLS_BY_NAME = {control.name: control for control in MATERIAL_CONTROLS}


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{label} must be finite")
    return converted


def normalise_material_value(control: object, value: object) -> object:
    """Coerce and range-check one artist value."""

    label = f"Material value {control.name!r}"
    if control.kind == "bool":
        if not isinstance(value, bool):
            raise ValueError(f"{label} must be boolean")
        return value
    if control.kind == "int":
        number = _number(value, label)
        if not number.is_integer():
            raise ValueError(f"{label} must be an integer")
        converted: object = int(number)
    elif control.kind == "float":
        converted = _number(value, label)
    elif control.kind in {"float2", "colour3"}:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
            raise ValueError(f"{label} must be an array")
        expected = 2 if control.kind == "float2" else 3
        if len(value) != expected:
            raise ValueError(f"{label} must contain {expected} numbers")
        converted = tuple(
            _number(component, f"{label}[{index}]")
            for index, component in enumerate(value)
        )
    else:
        raise ValueError(f"Unsupported material kind: {control.kind!r}")

    components = converted if isinstance(converted, tuple) else (converted,)
    if control.minimum is not None and any(
        item < control.minimum for item in components
    ):
        raise ValueError(f"{label} is below {control.minimum}")
    if control.maximum is not None and any(
        item > control.maximum for item in components
    ):
        raise ValueError(f"{label} is above {control.maximum}")
    return converted


def normalise_material_changes(
    values: Mapping[str, object],
) -> dict[str, object]:
    """Validate a partial material update without inventing defaults."""

    unknown = tuple(sorted(set(values) - set(_CONTROLS_BY_NAME)))
    if unknown:
        raise ValueError(f"Unknown material controls: {unknown}")
    return {
        name: normalise_material_value(_CONTROLS_BY_NAME[name], value)
        for name, value in values.items()
    }


def normalise_material_profile(
    values: Mapping[str, object],
) -> tuple[tuple[str, object], ...]:
    """Validate a complete profile, filling omitted values from defaults."""

    unknown = tuple(sorted(set(values) - set(_CONTROLS_BY_NAME)))
    if unknown:
        raise ValueError(f"Unknown material controls: {unknown}")
    return tuple(
        (
            control.name,
            normalise_material_value(
                control,
                values.get(control.name, control.default),
            ),
        )
        for control in MATERIAL_CONTROLS
    )


def material_defaults_for_group(
    group: str | None,
) -> dict[str, object]:
    """Return factory defaults for one group or a complete Set profile."""

    selected = tuple(
        control
        for control in MATERIAL_CONTROLS
        if group is None or control.group == group
    )
    if group is not None and not selected:
        raise ValueError(f"Unknown material group: {group}")
    return {control.name: control.default for control in selected}
