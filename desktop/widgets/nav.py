"""Left navigation bar: icon + text, selection light bar and hover halo."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QPushButton, QVBoxLayout, QWidget

from ..theme import palette
from . import icons


class NavigationBar(QWidget):
    """Vertical navigation; items switch icon color and lighting between checked/hover states."""

    current_changed = Signal(int)

    def __init__(
        self,
        items: list[tuple[str, str]],
        *,
        theme: str = "dark",
        parent: QWidget | None = None,
    ) -> None:
        """items: [(display text, icon name), ...]"""
        super().__init__(parent)
        self._theme = theme
        self._icon_names = [icon_name for _, icon_name in items]
        self._labels = [label for label, _ in items]
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: list[QPushButton] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(3)
        for index, (label, _icon_name) in enumerate(items):
            button = QPushButton(label)
            button.setProperty("nav", True)
            button.setCheckable(True)
            button.setIconSize(QSize(20, 20))
            button.setMinimumHeight(40)
            button.setCursor(Qt.PointingHandCursor)
            self.group.addButton(button, index)
            self.buttons.append(button)
            layout.addWidget(button)
            button.toggled.connect(
                lambda checked, i=index: self._toggled(i, checked))
        layout.addStretch(1)
        self.group.idClicked.connect(self.current_changed)
        self._refresh_icons()

    # --------------------------------------------------------------- Status

    def count(self) -> int:
        return len(self.buttons)

    def item_text(self, index: int) -> str:
        return self._labels[index]

    def current_index(self) -> int:
        return self.group.checkedId()

    def set_current(self, index: int) -> None:
        if 0 <= index < len(self.buttons):
            self.buttons[index].setChecked(True)
            self.group.idClicked.emit(index)

    def set_theme(self, theme: str) -> None:
        self._theme = theme
        self._refresh_icons()

    # --------------------------------------------------------------- Internal

    def _toggled(self, index: int, _checked: bool) -> None:
        self._refresh_icon(index)

    def _refresh_icons(self) -> None:
        for index in range(len(self.buttons)):
            self._refresh_icon(index)

    def _refresh_icon(self, index: int) -> None:
        colors = palette(self._theme)
        button = self.buttons[index]
        color = colors["accent"] if button.isChecked() else colors["text_dim"]
        dpr = button.devicePixelRatioF()
        button.setIcon(icons.icon(self._icon_names[index], color, 20, dpr))
