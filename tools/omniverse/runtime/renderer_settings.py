"""Own and restore renderer settings required by the manual ORMS runtime."""

from __future__ import annotations

from typing import Any

from .status_log import log_room_map_warning

_RTX_OPACITY_OVERRIDE_SETTING = "/rtx/material/omniRtxEnableOpacityOverride"
_RTX_CUTOUT_OPT_IN_ATTRIBUTE = "omni:rtx:enableCutoutOpacity"

_previous_rtx_opacity_override: bool | None = None
_owns_rtx_opacity_override_setting = False


def _enable_rtx_cutout_opacity(
    settings_interface: Any | None = None,
) -> None:
    """Enable RTX's explicit custom-material cutout contract for ORMS."""

    global _previous_rtx_opacity_override
    global _owns_rtx_opacity_override_setting
    if _owns_rtx_opacity_override_setting:
        return
    if settings_interface is None:
        import carb.settings

        settings_interface = carb.settings.get_settings()
    previous_value = settings_interface.get(_RTX_OPACITY_OVERRIDE_SETTING)
    _previous_rtx_opacity_override = (
        None if previous_value is None else bool(previous_value)
    )
    settings_interface.set(_RTX_OPACITY_OVERRIDE_SETTING, True)
    _owns_rtx_opacity_override_setting = True
    log_room_map_warning(
        owner="SHARED ROOM CLASSIFIER",
        process="RUNTIME CUTOUT OPACITY",
        state="ENABLED",
        details={
            "setting": _RTX_OPACITY_OVERRIDE_SETTING,
            "previous_value": _previous_rtx_opacity_override,
            "runtime_value": True,
            "material_attribute": _RTX_CUTOUT_OPT_IN_ATTRIBUTE,
            "restored_on_stop": True,
        },
    )


def _restore_rtx_cutout_opacity(
    settings_interface: Any | None = None,
) -> None:
    """Restore the custom-material opacity override owned by ORMS."""

    global _previous_rtx_opacity_override
    global _owns_rtx_opacity_override_setting
    if not _owns_rtx_opacity_override_setting:
        return
    if settings_interface is None:
        import carb.settings

        settings_interface = carb.settings.get_settings()
    # Absent and explicit false have the same renderer semantics.  The
    # carb.settings Python API differs across supported Kit builds in how an
    # item is removed, so restore that semantic state explicitly.
    restored_value = bool(_previous_rtx_opacity_override)
    settings_interface.set(_RTX_OPACITY_OVERRIDE_SETTING, restored_value)
    _previous_rtx_opacity_override = None
    _owns_rtx_opacity_override_setting = False
    log_room_map_warning(
        owner="SHARED ROOM CLASSIFIER",
        process="RUNTIME CUTOUT OPACITY",
        state="RESTORED",
        details={
            "setting": _RTX_OPACITY_OVERRIDE_SETTING,
            "restored_value": restored_value,
        },
    )
