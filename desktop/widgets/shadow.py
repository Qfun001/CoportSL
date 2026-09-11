"""Soft shadow effect assistant: Provides a "floating" level for cards and buttons."""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget


def apply_shadow(
    widget: QWidget,
    *,
    blur: float = 14.0,
    dy: float = 3.0,
    color: QColor | None = None,
) -> QGraphicsDropShadowEffect:
    """Add a soft shadow to the control; return the effect object for subsequent color changes."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0.0, dy)
    effect.setColor(color or QColor(0, 0, 0, 80))
    widget.setGraphicsEffect(effect)
    return effect


def set_shadow_color(effect: QGraphicsDropShadowEffect | None,
                     color: QColor) -> None:
    if effect is not None:
        effect.setColor(color)
