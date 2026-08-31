"""Manual Kit Preferences page for the shared-room classifier.

Kit imports stay inside functions so the persistent-settings contract remains
inspectable and testable in an ordinary OpenUSD Python environment.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

KIT_SETTINGS_ROOT = "/persistent/exts/orms/classifier"

SETTING_DEFAULTS: dict[str, object] = {
    "enable_x2": True,
    "enable_x3": True,
    "enable_x4": True,
    "partition_seed": 0,
    "instance_policy": "Preserve",
    "metrics_mode": "Auto from stage",
    "local_up_axis": "Y",
    "local_meters_per_unit": 1.0,
    "edge_gap_tolerance_metres": 0.65,
    "floor_tolerance_metres": 0.25,
    "minimum_vertical_overlap": 0.5,
    "maximum_turn_degrees": 100.0,
    "corner_turn_threshold_degrees": 60.0,
}

_page: Any | None = None
_subscriptions: list[Any] = []


def setting_path(name: str) -> str:
    """Return one persistent, user-local ORMS classifier setting path."""

    return f"{KIT_SETTINGS_ROOT}/{name}"


def ensure_setting_defaults() -> None:
    """Declare persistent local defaults and migrate early R&D token labels."""

    import carb.settings

    settings = carb.settings.get_settings()
    for name, default in SETTING_DEFAULTS.items():
        settings.set_default(setting_path(name), default)

    label_migrations = {
        "instance_policy": {
            "preserve": "Preserve",
            "session_deinstance": "Session de-instance",
        },
        "metrics_mode": {
            "auto": "Auto from stage",
            "local_override": "Local override",
        },
    }
    for name, migrations in label_migrations.items():
        path = setting_path(name)
        current = settings.get(path)
        if current in migrations:
            settings.set(path, migrations[current])


def _create_page() -> object:
    import omni.ui as ui
    from omni.kit.window.preferences import PreferenceBuilder, SettingType

    class ORMSClassifierPreferences(PreferenceBuilder):
        def __init__(self) -> None:
            super().__init__("ORMS Classifier")

        def build(self) -> None:
            with ui.VStack(height=0):
                with self.add_frame("Room families"):
                    with ui.VStack():
                        for size in (2, 3, 4):
                            self.create_setting_widget(
                                f"Enable x{size} rooms",
                                setting_path(f"enable_x{size}"),
                                SettingType.BOOL,
                            )
                        self.create_setting_widget(
                            "Partition seed",
                            setting_path("partition_seed"),
                            SettingType.INT,
                        )

                with self.add_frame("USD composition"):
                    with ui.VStack():
                        self.create_setting_widget_combo(
                            "Instance policy",
                            setting_path("instance_policy"),
                            ["Preserve", "Session de-instance"],
                        )
                        self.create_setting_widget_combo(
                            "Stage metrics",
                            setting_path("metrics_mode"),
                            ["Auto from stage", "Local override"],
                        )
                        self.create_setting_widget_combo(
                            "Local up axis",
                            setting_path("local_up_axis"),
                            ["Y", "Z"],
                        )
                        self.create_setting_widget(
                            "Local metres per unit",
                            setting_path("local_meters_per_unit"),
                            SettingType.FLOAT,
                        )

                with self.add_frame("Geometric tolerances"):
                    with ui.VStack():
                        for label, name in (
                            ("Edge gap (metres)", "edge_gap_tolerance_metres"),
                            ("Floor band (metres)", "floor_tolerance_metres"),
                            (
                                "Minimum vertical overlap",
                                "minimum_vertical_overlap",
                            ),
                            (
                                "Maximum facade turn (degrees)",
                                "maximum_turn_degrees",
                            ),
                            (
                                "Corner turn threshold (degrees)",
                                "corner_turn_threshold_degrees",
                            ),
                        ):
                            self.create_setting_widget(
                                label,
                                setting_path(name),
                                SettingType.FLOAT,
                            )

    return ORMSClassifierPreferences()


def register(on_change: Callable[[], None] | None = None) -> object | None:
    """Register the page and live setting subscriptions when Kit provides it."""

    global _page, _subscriptions
    if _page is not None:
        return _page

    try:
        import carb.settings
        import omni.kit.app
        import omni.kit.window.preferences as preferences
    except ModuleNotFoundError:
        return None

    ensure_setting_defaults()
    _page = preferences.register_page(_create_page())

    def setting_changed(_item: object, event_type: object) -> None:
        if event_type != carb.settings.ChangeEventType.CHANGED:
            return
        # Preference widgets are already bound to carb.settings. Rebuilding the
        # whole Preferences window here runs inside the widget's draw callback
        # and Kit rejects the resulting child insertion. The page layout is
        # static, so only the classifier needs to react to the changed value.
        if on_change is not None:
            on_change()

    _subscriptions = [
        omni.kit.app.SettingChangeSubscription(
            setting_path(name),
            setting_changed,
        )
        for name in SETTING_DEFAULTS
    ]
    return _page


def unregister() -> None:
    """Remove only the ORMS page and release its setting subscriptions."""

    global _page, _subscriptions
    _subscriptions = []
    if _page is None:
        return
    try:
        import omni.kit.window.preferences as preferences

        preferences.unregister_page(_page)
    except ModuleNotFoundError:
        pass
    _page = None
