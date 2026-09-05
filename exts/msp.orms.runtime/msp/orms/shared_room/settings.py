# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Translate persistent Kit values into validated classifier settings."""

from __future__ import annotations

from collections.abc import Mapping

from .contracts import (
    INSTANCE_POLICY_PRESERVE,
    INSTANCE_POLICY_SESSION_DEINSTANCE,
    KIT_SETTINGS_ROOT,
    METRICS_MODE_AUTO,
    METRICS_MODE_LOCAL_OVERRIDE,
    RuntimeClassifierSettings,
)

CLASSIFIER_SETTING_DEFAULTS: dict[str, object] = {
    "enable_x2": True,
    "enable_x3": True,
    "enable_x4": True,
    "partition_seed": 0,
    "instance_policy": INSTANCE_POLICY_PRESERVE,
    "metrics_mode": METRICS_MODE_AUTO,
    "local_up_axis": "Y",
    "local_meters_per_unit": 1.0,
    "floor_tolerance_metres": 0.25,
    "minimum_vertical_overlap": 0.5,
    "facade_angle_snap_degrees": 5.0,
    "maximum_local_spacing_ratio": 2.0,
    "maximum_turn_degrees": 100.0,
    "corner_turn_threshold_degrees": 60.0,
}


def classifier_setting_path(name: str) -> str:
    """Return one persistent classifier setting path."""

    return f"{KIT_SETTINGS_ROOT}/{name}"


def ensure_classifier_setting_defaults() -> None:
    """Declare classifier defaults without replacing persistent choices."""

    import carb.settings

    settings = carb.settings.get_settings()
    for name, default in CLASSIFIER_SETTING_DEFAULTS.items():
        settings.set_default(classifier_setting_path(name), default)


def settings_from_mapping(
    values: Mapping[str, object],
) -> RuntimeClassifierSettings:
    """Build validated settings from a Kit-like mapping for tests and scripts."""

    enabled_sizes = {1}
    for size in (2, 3, 4):
        if bool(values.get(f"enable_x{size}", True)):
            enabled_sizes.add(size)
    instance_policy_value = str(
        values.get("instance_policy", INSTANCE_POLICY_PRESERVE)
    )
    instance_policy = {
        "preserve": INSTANCE_POLICY_PRESERVE,
        "session de-instance": INSTANCE_POLICY_SESSION_DEINSTANCE,
        "session_deinstance": INSTANCE_POLICY_SESSION_DEINSTANCE,
    }.get(instance_policy_value.strip().lower(), INSTANCE_POLICY_PRESERVE)
    metrics_mode_value = str(values.get("metrics_mode", METRICS_MODE_AUTO))
    metrics_mode = {
        "auto": METRICS_MODE_AUTO,
        "auto from stage": METRICS_MODE_AUTO,
        "local override": METRICS_MODE_LOCAL_OVERRIDE,
        "local_override": METRICS_MODE_LOCAL_OVERRIDE,
    }.get(metrics_mode_value.strip().lower(), METRICS_MODE_AUTO)
    return RuntimeClassifierSettings(
        enabled_room_sizes=frozenset(enabled_sizes),
        partition_seed=int(values.get("partition_seed", 0)),
        instance_policy=instance_policy,
        metrics_mode=metrics_mode,
        local_up_axis=str(values.get("local_up_axis", "Y")),
        local_meters_per_unit=float(values.get("local_meters_per_unit", 1.0)),
        floor_tolerance_metres=float(
            values.get("floor_tolerance_metres", 0.25)
        ),
        minimum_vertical_overlap=float(
            values.get("minimum_vertical_overlap", 0.5)
        ),
        facade_angle_snap_degrees=float(
            values.get("facade_angle_snap_degrees", 5.0)
        ),
        maximum_local_spacing_ratio=float(
            values.get("maximum_local_spacing_ratio", 2.0)
        ),
        maximum_turn_degrees=float(values.get("maximum_turn_degrees", 100.0)),
        corner_turn_threshold_degrees=float(
            values.get("corner_turn_threshold_degrees", 60.0)
        ),
    )


def settings_from_kit() -> RuntimeClassifierSettings:
    """Read persistent local ORMS values without authoring them into USD."""

    import carb.settings

    settings = carb.settings.get_settings()
    ensure_classifier_setting_defaults()
    values = {}
    for name in CLASSIFIER_SETTING_DEFAULTS:
        values[name] = settings.get(classifier_setting_path(name))
    return settings_from_mapping(values)
