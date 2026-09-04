"""Build compact, wrapped hover help for ORMS widgets."""

from __future__ import annotations


def with_wrapped_tooltip(
    widget: object,
    text: str | None,
    *,
    width: int = 300,
) -> object:
    """Attach a fixed-width, word-wrapped tooltip to one widget."""

    if not text:
        return widget

    def build() -> None:
        import omni.ui as ui

        with ui.VStack(width=width, height=0):
            ui.Label(
                text,
                width=width,
                height=0,
                word_wrap=True,
                style={"color": 0xFF202020},
            )

    set_tooltip = getattr(widget, "set_tooltip_fn", None)
    if not callable(set_tooltip):
        raise TypeError(f"Unsupported ORMS tooltip widget: {type(widget)!r}")
    set_tooltip(build)
    return widget
