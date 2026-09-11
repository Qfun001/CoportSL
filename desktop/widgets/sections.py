"""Sections and prompt controls: collapsible groups, status logos, inline message strips."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..theme import STATUS_LABELS, palette


class CollapsibleSection(QWidget):
    """Foldable grouping: title button + content area, collapsed by default."""

    def __init__(
        self,
        title: str,
        *,
        expanded: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.button = QToolButton()
        self.button.setText(title)
        self.button.setCheckable(True)
        self.button.setChecked(expanded)
        self.button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.button.setArrowType(
            Qt.DownArrow if expanded else Qt.RightArrow)
        self.button.setProperty("sectionToggle", True)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(16, 2, 0, 4)
        self.content.setVisible(expanded)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.button)
        layout.addWidget(self.content)
        self.button.toggled.connect(self._toggle)

    def _toggle(self, checked: bool) -> None:
        self.button.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        self.content.setVisible(checked)

    def set_content(self, widget: QWidget) -> None:
        self.content_layout.addWidget(widget)

    def set_expanded(self, expanded: bool) -> None:
        self.button.setChecked(expanded)


class StatusBadge(QLabel):
    """Task status logo: The background color changes with the status."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = "dark"
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumWidth(64)
        self.set_status("idle")

    def set_theme(self, theme: str) -> None:
        self._theme = theme
        self.set_status(self._status)

    def set_status(self, status: str) -> None:
        self._status = status
        colors = palette(self._theme)
        color = colors.get(status, colors["idle"])
        self.setText(STATUS_LABELS.get(status, status))
        self.setStyleSheet(
            f"QLabel {{ background: {color}; color: #ffffff; "
            "border-radius: 8px; padding: 2px 10px; font-weight: 600; }")


class Banner(QFrame):
    """Inline message strip: three levels of info/warn/error."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = "dark"
        self._kind = "info"
        self.label = QLabel()
        self.label.setWordWrap(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.addWidget(self.label)
        self.hide()

    def set_theme(self, theme: str) -> None:
        self._theme = theme
        if self.isVisible():
            self.show_message(self._kind, self.label.text())

    def show_message(self, kind: str, text: str) -> None:
        self._kind = kind
        colors = palette(self._theme)
        background = colors[f"{kind}_bg"]
        foreground = colors[f"{kind}_text"]
        self.setStyleSheet(
            f"QFrame {{ background: {background}; border-radius: 4px; }}"
            f"QLabel {{ color: {foreground}; background: transparent; }}")
        self.label.setText(text)
        self.show()

    def clear(self) -> None:
        self.label.clear()
        self.hide()
