"""Settings page for language, theme, logs, history, and application details."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QGroupBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..config import app_data_info
from ..i18n import LANGUAGES
from ..theme import THEME_NAMES
from ..version import __version__
from ..widgets.fields import (
    NoWheelComboBox,
    ParameterGrid,
    add_row,
    make_int,
)
from ..widgets.sections import Banner


class SettingsPage(QWidget):
    """Keep UI preferences here and computation parameters on task pages."""

    def __init__(self, window, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.window = window
        settings = window.settings

        self.banner = Banner()

        self.language = NoWheelComboBox()
        for key, label in LANGUAGES.items():
            self.language.addItem(label, key)
        language_index = self.language.findData(settings.get("language", "en"))
        if language_index >= 0:
            self.language.setCurrentIndex(language_index)
        self.language.currentIndexChanged.connect(self._changed)

        self.theme = NoWheelComboBox()
        for key, label in THEME_NAMES.items():
            self.theme.addItem(label, key)
        index = self.theme.findData(settings.get("theme", "dark"))
        if index >= 0:
            self.theme.setCurrentIndex(index)
        self.theme.currentIndexChanged.connect(self._changed)

        self.log_lines = make_int(
            int(settings.get("log_lines", 2000)), 100, 100000)
        self.log_lines.valueChanged.connect(self._changed)

        self.history_limit = make_int(
            int(settings.get("history_limit", 200)), 10, 10000)
        self.history_limit.valueChanged.connect(self._changed)

        data_path, fallback = app_data_info()
        note = QLabel(
            f"设置、作业与日志目录：{data_path}\n"
            "数据路径和各页面参数会自动恢复上次有效值；"
            "损坏时自动备份为 .broken.json 并恢复默认值。"
            + (f"\n{fallback}" if fallback else
               "\n当前使用软件同级的便携数据目录。"))
        note.setProperty("dim", True)
        note.setWordWrap(True)

        form_widget = QWidget()
        form = ParameterGrid(form_widget)
        form.setContentsMargins(0, 0, 0, 0)
        add_row(form, "界面语言", self.language, "切换后立即生效")
        add_row(form, "主题", self.theme, "切换后立即生效")
        add_row(form, "任务抽屉日志容量", self.log_lines,
                "超出后丢弃最旧行；完整日志始终写入作业目录。",
                unit="行")
        add_row(form, "历史作业保留上限", self.history_limit,
                "超过上限后自动删除最旧的作业 JSON、状态和日志；"
                "不会删除科研计算结果。",
                unit="项")
        form.addRow(note)

        about = QGroupBox("关于")
        about_layout = QVBoxLayout(about)
        about_text = QLabel(
            f"CoportSL {__version__}\n"
            "偏振广义相对论辐射转移桌面软件\n\n"
            "许可证：GNU Affero General Public License v3.0\n"
            "主要组件：Qt/PySide6、PyInstaller、NumPy、SciPy、"
            "Matplotlib、OpenCV、nlohmann/json\n"
            "源码：对外发布时请在同一发布页提供本版本对应源码。")
        about_text.setWordWrap(True)
        about_layout.addWidget(about_text)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.banner)
        layout.addWidget(form_widget)
        layout.addWidget(about)
        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _changed(self, *_args) -> None:
        self.window.update_settings({
            "language": str(self.language.currentData()),
            "theme": str(self.theme.currentData()),
            "log_lines": self.log_lines.value(),
            "history_limit": self.history_limit.value(),
        })
