"""Build local OmniUI fields without writing staged values to Kit settings."""

from __future__ import annotations

from collections.abc import Callable, Sequence


def _watch(model: object, changed: Callable[[], None]) -> None:
    add_changed = getattr(model, "add_value_changed_fn", None)
    if not callable(add_changed):
        raise TypeError(f"Unsupported ORMS field model: {type(model)!r}")
    add_changed(lambda _model: changed())


def string_field(
    value: str,
    changed: Callable[[str], None],
    *,
    multiline: bool = False,
) -> tuple[object, ...]:
    """Create one local string model for staged or live text."""

    import omni.ui as ui

    model = ui.SimpleStringModel(value)
    ui.StringField(
        model=model,
        multiline=multiline,
        height=72 if multiline else 24,
    )
    _watch(model, lambda: changed(model.get_value_as_string()))
    return (model,)


def material_field(
    kind: str,
    value: object,
    changed: Callable[[object], None],
    minimum: float | None = None,
    maximum: float | None = None,
) -> tuple[object, ...]:
    """Create local scalar or vector models for one material control."""

    import omni.ui as ui

    if kind == "bool":
        model = ui.SimpleBoolModel(bool(value))
        ui.CheckBox(model=model, width=24)
        _watch(model, lambda: changed(model.get_value_as_bool()))
        return (model,)
    if kind == "int":
        model = ui.SimpleIntModel(int(value))
        ui.IntField(model=model)
        _watch(model, lambda: changed(model.get_value_as_int()))
        return (model,)
    if kind == "float":
        model = ui.SimpleFloatModel(float(value))
        ui.FloatField(model=model)
        _watch(
            model,
            lambda: changed(
                _bounded(
                    model.get_value_as_float(),
                    minimum,
                    maximum,
                )
            ),
        )
        return (model,)
    if kind in {"float2", "colour3"}:
        return _vector_field(
            tuple(value),
            changed,
            minimum,
            maximum,
        )
    raise ValueError(f"Unsupported ORMS material field kind: {kind}")


def _vector_field(
    value: Sequence[float],
    changed: Callable[[object], None],
    minimum: float | None,
    maximum: float | None,
) -> tuple[object, ...]:
    import omni.ui as ui

    models = tuple(ui.SimpleFloatModel(float(item)) for item in value)

    def emit() -> None:
        changed(
            tuple(
                _bounded(
                    model.get_value_as_float(),
                    minimum,
                    maximum,
                )
                for model in models
            )
        )

    with ui.HStack(spacing=4):
        for model in models:
            ui.FloatField(model=model)
            _watch(model, emit)
    return models


def _bounded(
    value: float,
    minimum: float | None,
    maximum: float | None,
) -> float:
    if minimum is not None:
        value = max(value, minimum)
    if maximum is not None:
        value = min(value, maximum)
    return value
