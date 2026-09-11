"""Running record page: task status and historical job files of this session."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..config import app_data_dir
from ..history import clear_history, load_states
from ..i18n import retranslate_widget_tree
from ..widgets.asyncjob import run_async
from ..widgets.sections import Banner
from ..theme import STATUS_LABELS


class HistoryPage(QWidget):
    """Display job records within the session and historical jobs under %LOCALAPPDATA%\\CoportSL\\jobs."""

    def __init__(self, window, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.window = window
        self.banner = Banner()
        self._scan_job = None
        self._rows = []

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["作业 ID", "标题", "类型", "状态", "结束时间", "日志"])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.refresh)
        self.open_log_button = QPushButton("查看日志")
        self.open_log_button.clicked.connect(self._open_log)
        self.open_jobs_dir = QPushButton("打开作业目录")
        self.open_jobs_dir.clicked.connect(self._open_jobs_dir)
        self.clear_button = QPushButton("清空运行记录")
        self.clear_button.clicked.connect(self._clear)

        buttons = QHBoxLayout()
        buttons.addWidget(self.refresh_button)
        buttons.addWidget(self.open_log_button)
        buttons.addWidget(self.open_jobs_dir)
        buttons.addWidget(self.clear_button)
        buttons.addStretch(1)

        note = QLabel(
            "清空只删除软件作业目录中的配置、状态和日志，"
            "不会删除任何计算结果、图件或原始数据。")
        note.setProperty("dim", True)
        note.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.banner)
        layout.addWidget(self.table, 1)
        layout.addLayout(buttons)
        layout.addWidget(note)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh()

    def set_task_active(self, active: bool) -> None:
        """Viewing capabilities are retained during the run, but deletion of the current job file is prohibited."""
        self.clear_button.setEnabled(not active)
        self.clear_button.setToolTip(
            "当前任务结束或取消后才能清空运行记录。" if active else "")

    def refresh(self) -> None:
        if self._scan_job is not None and self._scan_job.is_running():
            return
        session = tuple(dict(record) for record in self.window.job_records)
        self._scan_job = run_async(
            lambda: self._collect_rows(session),
            self._refresh_done,
            lambda message: self.banner.show_message(
                "error", f"读取运行记录失败：{message}"),
        )

    @staticmethod
    def _collect_rows(
        session: tuple[dict, ...],
    ) -> list[tuple[str, str, str, str, str, Path | None]]:
        rows: list[tuple[str, str, str, str, str, Path | None]] = []
        session_ids = set()
        for record in session:
            session_ids.add(record["job_id"])
            rows.append((
                record["job_id"],
                record["title"],
                record["kind"],
                STATUS_LABELS.get(record["status"], record["status"]),
                record.get("finished", "进行中"),
                record.get("log_path"),
            ))
        for record in load_states():
            job_id = str(record.get("job_id", ""))
            if not job_id or job_id in session_ids:
                continue
            log_value = str(record.get("log_path", ""))
            log_path = Path(log_value) if log_value else None
            if log_path is not None and not log_path.is_file():
                log_path = None
            status = str(record.get("status", "unknown"))
            rows.append((
                job_id,
                str(record.get("title", "（历史作业）")),
                str(record.get("kind", "")),
                STATUS_LABELS.get(status, status),
                str(record.get("finished", "")),
                log_path,
            ))

        # Before the compatible upgrade, there was only job JSON and no history of status snapshots.
        jobs_dir = app_data_dir() / "jobs"
        if jobs_dir.is_dir():
            known = session_ids | {row[0] for row in rows}
            for path in sorted(jobs_dir.glob("*.json"), reverse=True):
                job_id = path.stem
                if job_id in known or job_id == "current":
                    continue
                log_path = jobs_dir / f"{job_id}.log"
                rows.append((
                    job_id, "（旧版历史作业）", HistoryPage._read_kind(path),
                    "已提交（状态未知）", "",
                    log_path if log_path.is_file() else None,
                ))
        return rows

    def _refresh_done(
        self,
        rows: list[tuple[str, str, str, str, str, Path | None]],
    ) -> None:
        self._rows = rows
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(rows))
        for row, (job_id, title, kind, status, finished, log_path) in enumerate(rows):
            values = (job_id, title, kind, status, finished,
                      "有" if log_path else "—")
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()
        self.table.setUpdatesEnabled(True)
        retranslate_widget_tree(self.table)

    @staticmethod
    def _read_kind(path: Path) -> str:
        import json

        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return str(value.get("kind", ""))
        except (OSError, json.JSONDecodeError, TypeError):
            return ""

    def selected_log(self) -> Path | None:
        rows = {index.row() for index in self.table.selectedIndexes()}
        if not rows:
            return None
        row = rows.pop()
        if 0 <= row < len(self._rows):
            return self._rows[row][5]
        return None

    def _open_log(self) -> None:
        log_path = self.selected_log()
        if log_path is None or not log_path.is_file():
            self.banner.show_message("warn", "所选作业没有可用日志文件。")
            return
        QDesktopServices.openUrl(log_path.resolve().as_uri())

    def _open_jobs_dir(self) -> None:
        jobs_dir = app_data_dir() / "jobs"
        jobs_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(jobs_dir.resolve().as_uri())

    def _clear(self) -> None:
        if self.window.process is not None:
            self.banner.show_message(
                "warn", "当前有任务正在运行，完成或取消后才能清空记录。")
            return
        answer = QMessageBox.question(
            self,
            "清空运行记录",
            "确定删除全部作业配置、状态和日志吗？\n"
            "科研计算结果和图件不会被删除。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        removed = clear_history()
        self.window.job_records.clear()
        self.refresh()
        self.banner.show_message("info", f"已清理 {removed} 个历史文件。")
