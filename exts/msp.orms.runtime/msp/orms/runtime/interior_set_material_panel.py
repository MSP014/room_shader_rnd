"""Build repeatable Set-scoped material controls."""

from __future__ import annotations

from collections.abc import Callable

from tools.omniverse.shared_room.material_controls import MATERIAL_CONTROLS
from tools.omniverse.shared_room.ui_sections import collapsable_frame

from .interior_set_controller import InteriorSetController
from .interior_set_fields import material_field

MaterialChanged = Callable[[str, str, object], None]
SectionCollapsed = Callable[[str, bool], bool]
SectionCollapsedChanged = Callable[[str, bool], None]


def build_interior_set_material_panel(
    controller: InteriorSetController,
    material_changed: MaterialChanged,
    section_collapsed: SectionCollapsed | None = None,
    section_collapsed_changed: SectionCollapsedChanged | None = None,
) -> tuple[object, ...]:
    """Build one complete material profile for every visible draft Set."""

    import omni.ui as ui

    models = []
    groups = tuple(dict.fromkeys(item.group for item in MATERIAL_CONTROLS))
    for item in controller.draft.sets:
        set_section_id = f"material:set:{item.set_id}"
        set_frame = collapsable_frame(
            ui,
            controller.draft.label_for(item.set_id),
            collapsed=(
                section_collapsed(set_section_id, False)
                if section_collapsed is not None
                else False
            ),
            collapsed_changed=(
                (
                    lambda collapsed, section_id=set_section_id: (
                        section_collapsed_changed(section_id, collapsed)
                    )
                )
                if section_collapsed_changed is not None
                else None
            ),
        )
        with set_frame:
            with ui.VStack(spacing=4):
                values = item.material_mapping()
                for group in groups:
                    group_section_id = (
                        f"{set_section_id}:group:{group.casefold()}"
                    )
                    group_frame = collapsable_frame(
                        ui,
                        group,
                        collapsed=(
                            section_collapsed(group_section_id, False)
                            if section_collapsed is not None
                            else False
                        ),
                        collapsed_changed=(
                            (
                                lambda collapsed, section_id=group_section_id: (
                                    section_collapsed_changed(
                                        section_id,
                                        collapsed,
                                    )
                                )
                            )
                            if section_collapsed_changed is not None
                            else None
                        ),
                    )
                    with group_frame:
                        with ui.VStack(spacing=3):
                            for control in MATERIAL_CONTROLS:
                                if control.group != group:
                                    continue
                                with ui.HStack(height=24):
                                    ui.Label(
                                        control.label,
                                        width=ui.Percent(45),
                                        word_wrap=True,
                                        name="title",
                                    )

                                    def changed(
                                        value: object,
                                        *,
                                        set_id: str = item.set_id,
                                        name: str = control.name,
                                    ) -> None:
                                        material_changed(set_id, name, value)

                                    models.extend(
                                        material_field(
                                            control.kind,
                                            values.get(
                                                control.name,
                                                control.default,
                                            ),
                                            changed,
                                            control.minimum,
                                            control.maximum,
                                        )
                                    )
    return tuple(models)
