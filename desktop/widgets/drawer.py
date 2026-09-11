"""Bottom task drawer: status, stage, progress, time taken, log and action buttons.

The drawer only does display and user action forwarding, and the process life cycle is managed by the task controller of the main window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..theme import DEFAULT_THEME, palette
from .sections import StatusBadge


class TaskDrawer(QWidget):
    """The retractable task drawer is permanently located at the bottom of the main window."""

    cancel_requested = Signal()
    open_output_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.max_lines = 2000
        self._theme = DEFAULT_THEME
        self._expanded = True
        self._output_dir: Path | None = None

        self.toggle = QToolButton()
        self.toggle.setText("任务")
        self.toggle.setCheckable(True)
        self.toggle.setChecked(True)
        self.toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle.setArrowType(Qt.DownArrow)
        self.toggle.setProperty("sectionToggle", True)
        self.toggle.toggled.connect(self._toggle_body)

        self.badge = StatusBadge()
        self.title = QLabel("无运行任务")
        self.title.setProperty("dim", True)
        self.stage = QLabel("")
        self.elapsed = QLabel("")

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(self.max_lines)

        self.cancel = QPushButton("取消")
        self.cancel.setProperty("danger", True)
        self.cancel.setEnabled(False)
        self.cancel.clicked.connect(self.cancel_requested)
        self.copy_log = QPushButton("复制日志")
        self.copy_log.clicked.connect(self._copy_log)
        self.open_output = QPushButton("打开结果目录")
        self.open_output.setEnabled(False)
        self.open_output.clicked.connect(self.open_output_requested)

        header = QHBoxLayout()
        header.setContentsMargins(8, 2, 8, 0)
        header.addWidget(self.toggle)
        header.addWidget(self.badge)
        header.addWidget(self.title, 1)
        header.addWidget(self.stage)
        header.addWidget(self.elapsed)
        header.addWidget(self.cancel)
        header.addWidget(self.copy_log)
        header.addWidget(self.open_output)

        self.body = QWidget()
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(8, 2, 8, 6)
        body_layout.setSpacing(4)
        body_layout.addWidget(self.progress)
        body_layout.addWidget(self.log, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(header)
        layout.addWidget(self.body, 1)

    def _toggle_body(self, checked: bool) -> None:
        self._expanded = checked
        self.toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        self.body.setVisible(checked)

    def set_theme(self, theme: str) -> None:
        self._theme = theme
        self.badge.set_theme(theme)

    def set_max_lines(self, count: int) -> None:
        self.max_lines = max(100, int(count))
        self.log.setMaximumBlockCount(self.max_lines)

    def begin(self, title: str) -> None:
        """Start a task: clear the log and enter the running state."""
        self.title.setText(title)
        self.title.setProperty("dim", False)
        self.title.setStyleSheet("")
        self.log.clear()
        self.stage.setText("")
        self.elapsed.setText("")
        self.progress.setRange(0, 0)  # Display busy status when total amount is unknown
        self.badge.set_status("running")
        self.cancel.setEnabled(True)
        self.open_output.setEnabled(False)
        self._output_dir = None
        if not self._expanded:
            self.toggle.setChecked(True)

    def set_status(self, status: str) -> None:
        self.badge.set_status(status)
        self.cancel.setEnabled(status in ("running", "validating", "queued"))

    def set_stage(self, name: str) -> None:
        self.stage.setText(f"阶段：{name}" if name else "")

    def set_elapsed(self, text: str) -> None:
        self.elapsed.setText(text)

    def set_progress(self, current: int, total: int, frame: object = None) -> None:
        total = max(1, int(total))
        self.progress.setRange(0, total)
        self.progress.setValue(min(int(current), total))
        suffix = f"（帧 {frame}）" if frame is not None else ""
        self.progress.setFormat(f"%v/%m{suffix}")

    def set_busy(self) -> None:
        self.progress.setRange(0, 0)

    def set_cancelling(self) -> None:
        """Stops the busy animation to clearly show that the cancellation request is being processed."""
        self.badge.set_status("cancelling")
        self.cancel.setEnabled(False)
        self.stage.setText("阶段：正在取消")
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setFormat("正在取消…")

    def cancel_progress(self) -> None:
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setFormat("已取消")

    def fail_progress(self) -> None:
        """Both failure and startup failure must terminate the indeterminate progress animation."""
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setFormat("运行失败")

    def finish_progress(self) -> None:
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.progress.setFormat("%v/%m")

    def append_log(self, line: str, *, error: bool = False) -> None:
        colors = palette(self._theme)
        color = colors["failed"] if error else colors["text"]
        # Explicitly set the color for each line to prevent a red HTML error from causing subsequent normal text to inherit red.
        self.log.appendHtml(
            f"<span style='color:{color}'>{_escape(line)}</span>")

    def set_output_dir(self, path: Path | None) -> None:
        self._output_dir = path
        self.open_output.setEnabled(path is not None)

    def output_dir(self) -> Path | None:
        return self._output_dir

    def log_text(self) -> str:
        return self.log.toPlainText()

    def _copy_log(self) -> None:
        QApplication.clipboard().setText(self.log.toPlainText())


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
