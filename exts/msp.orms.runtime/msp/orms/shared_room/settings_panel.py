# SPDX-FileCopyrightText: 2026 Maksim Pospelkov
# SPDX-License-Identifier: MIT
"""Build the tabbed artist controls embedded in the ORMS Kit window."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from functools import partial

from .material_controls import MATERIAL_CONTROLS, material_setting_path
from .settings import classifier_setting_path
from .ui_buttons import selection_button
from .ui_sections import collapsable_frame
from .ui_tooltips import with_wrapped_tooltip

SETTINGS_TAB_LABELS = (
    "ORMS Classifier",
    "Material Parameters",
    "Interior Atlases",
)

_ROOM_FAMILY_HELP = (
    "x1 is always available. Disabling x2, x3, or x4 reclassifies those "
    "rooms through x1 fallback; window geometry is not removed."
)

ModelCallback = Callable[[object, Callable[[], None]], None]


class _SettingsPanelBuilder:
    """Build rows while retaining the Kit models that back their widgets."""

    def __init__(
        self,
        *,
        atlas_paths: Mapping[str, str],
        classifier_changed: Callable[[], None],
        material_changed: Callable[[], None],
        apply_atlases: Callable[[], None],
        build_lifecycle_controls: Callable[[], None],
        watch_model: ModelCallback,
        build_assignment_panel: Callable[[], tuple[object, ...]] | None = None,
        build_material_panel: Callable[[], tuple[object, ...]] | None = None,
        build_atlas_panel: Callable[[], tuple[object, ...]] | None = None,
        active_tab_index: int = 0,
        tab_changed: Callable[[int], None] | None = None,
        debug_atlases_collapsed: bool = False,
        debug_atlases_collapsed_changed: Callable[[bool], None] | None = None,
        section_collapsed: Callable[[str, bool], bool] | None = None,
        section_collapsed_changed: Callable[[str, bool], None] | None = None,
    ) -> None:
        self._atlas_paths = atlas_paths
        self._classifier_changed = classifier_changed
        self._material_changed = material_changed
        self._apply_atlases = apply_atlases
        self._build_lifecycle_controls = build_lifecycle_controls
        self._watch_model = watch_model
        self._build_assignment_panel = build_assignment_panel
        self._build_material_panel = build_material_panel
        self._build_atlas_panel = build_atlas_panel
        self._active_tab_index = max(
            0,
            min(active_tab_index, len(SETTINGS_TAB_LABELS) - 1),
        )
        self._tab_changed = tab_changed
        self._debug_atlases_collapsed = debug_atlases_collapsed
        self._debug_atlases_collapsed_changed = debug_atlases_collapsed_changed
        self._section_collapsed = section_collapsed
        self._section_collapsed_changed = section_collapsed_changed
        self._models: list[object] = []

    @property
    def models(self) -> tuple[object, ...]:
        """Retain models for as long as the containing window exists."""

        return tuple(self._models)

    @staticmethod
    def _label(text: str) -> None:
        import omni.ui as ui

        ui.Label(
            text,
            width=ui.Percent(45),
            word_wrap=True,
            name="title",
        )

    def _setting_row(
        self,
        label: str,
        path: str,
        setting_type: object,
        *,
        changed: Callable[[], None] | None = None,
        enabled: bool = True,
        minimum: float | None = None,
        maximum: float | None = None,
        tooltip: str | None = None,
    ) -> None:
        import omni.ui as ui
        from omni.kit.widget.settings import create_setting_widget

        kwargs: dict[str, object] = {"enabled": enabled}
        if minimum is not None and maximum is not None:
            kwargs.update(
                {
                    "range_from": minimum,
                    "range_to": maximum,
                    "hard_range": True,
                }
            )
        row = ui.HStack(height=24)
        with_wrapped_tooltip(row, tooltip)
        with row:
            self._label(label)
            _widget, model = create_setting_widget(
                path,
                setting_type,
                **kwargs,
            )
        self._models.append(model)
        if changed is not None:
            self._watch_model(model, changed)

    def _combo_row(
        self,
        label: str,
        path: str,
        items: list[str],
    ) -> None:
        import omni.ui as ui
        from omni.kit.widget.settings import create_setting_widget_combo

        with ui.HStack(height=24):
            self._label(label)
            _widget, model = create_setting_widget_combo(
                path,
                items,
                setting_is_index=False,
            )
        self._models.append(model)
        self._watch_model(model, self._classifier_changed)

    def _section_frame(
        self,
        ui: object,
        title: str,
        section_id: str,
        *,
        collapsed: bool = False,
    ) -> object:
        """Build one content-sized section with retained state."""

        current = (
            self._section_collapsed(section_id, collapsed)
            if self._section_collapsed is not None
            else collapsed
        )
        changed = (
            (
                lambda value: self._section_collapsed_changed(
                    section_id,
                    value,
                )
            )
            if self._section_collapsed_changed is not None
            else None
        )
        return collapsable_frame(
            ui,
            title,
            collapsed=current,
            collapsed_changed=changed,
        )

    def _build_classifier(self) -> None:
        import omni.ui as ui
        from omni.kit.widget.settings import SettingType

        self._build_lifecycle_controls()

        if self._build_assignment_panel is not None:
            with self._section_frame(
                ui,
                "Automatic mesh assignments",
                "classifier:auto_assignments",
            ):
                with ui.VStack(spacing=6):
                    self._models.extend(self._build_assignment_panel())

        with self._section_frame(
            ui,
            "Room families",
            "classifier:room_families",
        ):
            with ui.VStack():
                for size in (2, 3, 4):
                    self._setting_row(
                        f"Enable x{size} rooms",
                        classifier_setting_path(f"enable_x{size}"),
                        SettingType.BOOL,
                        changed=self._classifier_changed,
                        tooltip=_ROOM_FAMILY_HELP,
                    )
                self._setting_row(
                    "Partition seed",
                    classifier_setting_path("partition_seed"),
                    SettingType.INT,
                    changed=self._classifier_changed,
                )

        with self._section_frame(
            ui,
            "USD composition",
            "classifier:usd_composition",
        ):
            with ui.VStack():
                self._combo_row(
                    "Instance policy",
                    classifier_setting_path("instance_policy"),
                    ["Preserve", "Session de-instance"],
                )
                self._combo_row(
                    "Stage metrics",
                    classifier_setting_path("metrics_mode"),
                    ["Auto from stage", "Local override"],
                )
                self._combo_row(
                    "Local up axis",
                    classifier_setting_path("local_up_axis"),
                    ["Y", "Z"],
                )
                self._setting_row(
                    "Local metres per unit",
                    classifier_setting_path("local_meters_per_unit"),
                    SettingType.FLOAT,
                    changed=self._classifier_changed,
                )

        with self._section_frame(
            ui,
            "Geometric tolerances",
            "classifier:geometric_tolerances",
        ):
            with ui.VStack():
                for label, name in (
                    ("Row snap (metres)", "floor_tolerance_metres"),
                    (
                        "Minimum vertical overlap",
                        "minimum_vertical_overlap",
                    ),
                    (
                        "Facade angle snap (degrees)",
                        "facade_angle_snap_degrees",
                    ),
                    (
                        "Maximum local spacing ratio",
                        "maximum_local_spacing_ratio",
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
                    self._setting_row(
                        label,
                        classifier_setting_path(name),
                        SettingType.FLOAT,
                        changed=self._classifier_changed,
                    )

    def _build_materials(self) -> None:
        import omni.ui as ui
        from omni.kit.widget.settings import SettingType

        if self._build_material_panel is not None:
            self._models.extend(self._build_material_panel())
            return
        kind_types = {
            "bool": SettingType.BOOL,
            "int": SettingType.INT,
            "float": SettingType.FLOAT,
            "float2": SettingType.DOUBLE2,
            "colour3": SettingType.COLOR3,
        }
        groups = tuple(
            dict.fromkeys(control.group for control in MATERIAL_CONTROLS)
        )
        for group in groups:
            with self._section_frame(
                ui,
                group,
                f"material:legacy_group:{group.casefold()}",
            ):
                with ui.VStack():
                    for control in MATERIAL_CONTROLS:
                        if control.group != group:
                            continue
                        self._setting_row(
                            control.label,
                            material_setting_path(control.name),
                            kind_types[control.kind],
                            changed=self._material_changed,
                            minimum=control.minimum,
                            maximum=control.maximum,
                        )

    def _build_atlases(self) -> None:
        import omni.ui as ui
        from omni.kit.widget.settings import SettingType

        if self._build_atlas_panel is not None:
            self._models.extend(self._build_atlas_panel())
            return

        frame = collapsable_frame(
            ui,
            "Packaged debug atlas fallback (global)",
            collapsed=self._debug_atlases_collapsed,
            collapsed_changed=self._debug_atlases_collapsed_changed,
        )
        with frame:
            with ui.VStack():
                for room_size in range(1, 5):
                    self._setting_row(
                        f"x{room_size} asset",
                        self._atlas_paths["debug_asset"].format(
                            room_size=room_size
                        ),
                        SettingType.STRING,
                        enabled=False,
                    )

        with self._section_frame(
            ui,
            "Production atlas override",
            "atlases:legacy_production_override",
        ):
            with ui.VStack():
                ui.Label(
                    "Choose one folder per room family. Each folder must "
                    "contain one continuous UDIM sequence beginning at 1001; "
                    "ORMS uses every consecutive texture in that sequence.",
                    word_wrap=True,
                    height=0,
                )
                for room_size in range(1, 5):
                    self._setting_row(
                        f"x{room_size} production folder",
                        self._atlas_paths["production_directory"].format(
                            room_size=room_size
                        ),
                        SettingType.STRING,
                    )
                ui.Spacer(height=8)
                ui.Button(
                    "Apply atlas configuration",
                    clicked_fn=self._apply_atlases,
                    height=28,
                )

    def build(self) -> None:
        """Build all tabs into the current OmniUI parent."""

        import omni.ui as ui

        tab_frames = []
        tab_buttons = []

        def select_tab(index: int) -> None:
            self._active_tab_index = index
            for item_index, frame in enumerate(tab_frames):
                frame.visible = item_index == index
            for item_index, button in enumerate(tab_buttons):
                button.selected = item_index == index
            if self._tab_changed is not None:
                self._tab_changed(index)

        with ui.VStack(height=0, spacing=6):
            with ui.HStack(height=32):
                for index, label in enumerate(SETTINGS_TAB_LABELS):
                    tab_buttons.append(
                        selection_button(
                            ui,
                            label,
                            selected=index == self._active_tab_index,
                            clicked=partial(select_tab, index),
                        )
                    )
            with ui.ZStack(height=0):
                for index, build_tab in enumerate(
                    (
                        self._build_classifier,
                        self._build_materials,
                        self._build_atlases,
                    )
                ):
                    frame = ui.VStack(
                        visible=index == self._active_tab_index,
                        height=0,
                        spacing=6,
                    )
                    tab_frames.append(frame)
                    with frame:
                        build_tab()


def build_settings_panel(
    *,
    atlas_paths: Mapping[str, str],
    classifier_changed: Callable[[], None],
    material_changed: Callable[[], None],
    apply_atlases: Callable[[], None],
    build_lifecycle_controls: Callable[[], None],
    watch_model: ModelCallback,
    build_assignment_panel: Callable[[], tuple[object, ...]] | None = None,
    build_material_panel: Callable[[], tuple[object, ...]] | None = None,
    build_atlas_panel: Callable[[], tuple[object, ...]] | None = None,
    active_tab_index: int = 0,
    tab_changed: Callable[[int], None] | None = None,
    debug_atlases_collapsed: bool = False,
    debug_atlases_collapsed_changed: Callable[[bool], None] | None = None,
    section_collapsed: Callable[[str, bool], bool] | None = None,
    section_collapsed_changed: Callable[[str, bool], None] | None = None,
) -> tuple[object, ...]:
    """Build the panel and return models owned by the containing window."""

    builder = _SettingsPanelBuilder(
        atlas_paths=atlas_paths,
        classifier_changed=classifier_changed,
        material_changed=material_changed,
        apply_atlases=apply_atlases,
        build_lifecycle_controls=build_lifecycle_controls,
        watch_model=watch_model,
        build_assignment_panel=build_assignment_panel,
        build_material_panel=build_material_panel,
        build_atlas_panel=build_atlas_panel,
        active_tab_index=active_tab_index,
        tab_changed=tab_changed,
        debug_atlases_collapsed=debug_atlases_collapsed,
        debug_atlases_collapsed_changed=(debug_atlases_collapsed_changed),
        section_collapsed=section_collapsed,
        section_collapsed_changed=section_collapsed_changed,
    )
    builder.build()
    return builder.models
