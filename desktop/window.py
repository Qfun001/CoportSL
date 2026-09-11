"""CoportSL desktop window and single-job task controller.

The window owns navigation, summary, pages, and the task drawer. It serializes
compute jobs and handles events, logs, cancellation, shutdown safety, and job
history; individual pages collect parameters and construct jobs.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from threading import Lock

from PySide6.QtCore import QProcess, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .config import app_data_dir, write_json
from .engine import find_worker, run_worker, runtime_root
from .form_state import (
    STATE_VERSION,
    capture_state,
    connect_changes,
    restore_state,
)
from .history import prune_history, save_state
from . import i18n
from .pages.common import new_job_id, parse_event_line
from .widgets import icons as icon_factory
from .widgets.drawer import TaskDrawer
from .widgets.nav import NavigationBar
from .widgets.sections import Banner, StatusBadge
from . import theme as theme_module
from .version import __version__

NAV_ITEMS = (
    "数据与模型", "Flux 定标", "正式计算", "后处理",
    "GRMHD 工具", "性能基准", "运行记录", "设置",
)

NAV_ICONS = (
    "database", "flux_wave", "black_hole", "bar_chart",
    "grid", "gauge", "history", "gear",
)

DEFAULT_SETTINGS = {
    "language": i18n.DEFAULT_LANGUAGE,
    "theme": "dark",
    "log_lines": 2000,
    "history_limit": 200,
    "last_paths": {"data": "", "grid": "", "output": ""},
    "last_parameters": {"version": STATE_VERSION, "values": {}},
}

BUSY_MESSAGE = "当前已有任务正在运行。请等待完成或先取消，再启动新任务。"


def _validated_settings(stored: object) -> dict:
    """Verify the type and interface range of persistent settings to avoid conversion exceptions during the startup phase."""
    if not isinstance(stored, dict):
        raise ValueError("设置根对象必须是 JSON object。")
    settings = json.loads(json.dumps(DEFAULT_SETTINGS))

    language = stored.get("language", settings["language"])
    if language not in i18n.LANGUAGES:
        raise ValueError("language must be en or zh_CN.")
    settings["language"] = language

    theme = stored.get("theme", settings["theme"])
    if theme not in theme_module.THEME_NAMES:
        raise ValueError("theme 必须是 dark 或 light。")
    settings["theme"] = theme

    for key, minimum, maximum in (
        ("log_lines", 100, 100000),
        ("history_limit", 10, 10000),
    ):
        value = stored.get(key, settings[key])
        if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
            raise ValueError(f"{key} 必须是 {minimum}..{maximum} 范围内的整数。")
        settings[key] = value

    paths = stored.get("last_paths", {})
    if not isinstance(paths, dict) or any(
            key not in {"data", "grid", "output"} or not isinstance(value, str)
            for key, value in paths.items()):
        raise ValueError("last_paths 必须只包含 data、grid、output 字符串。")
    settings["last_paths"].update(paths)

    parameters = stored.get("last_parameters", settings["last_parameters"])
    if not isinstance(parameters, dict):
        raise ValueError("last_parameters 必须是 JSON object。")
    version = parameters.get("version")
    values = parameters.get("values")
    if version == STATE_VERSION and isinstance(values, dict):
        settings["last_parameters"] = {
            "version": STATE_VERSION,
            "values": values,
        }
    return settings


def load_settings() -> tuple[dict, str]:
    """Read settings; backup to .broken.json when damaged and return default values and prompts."""
    path = app_data_dir() / "settings.json"
    settings = json.loads(json.dumps(DEFAULT_SETTINGS))
    if not path.is_file():
        return settings, ""
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
        return _validated_settings(stored), ""
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = path.with_name(f"{path.stem}.broken-{stamp}.json")
        try:
            path.rename(backup)
            return settings, f"设置文件已损坏，已备份为 {backup} 并恢复默认值。"
        except OSError:
            return settings, f"设置文件已损坏且无法备份：{error}；已恢复默认值。"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"CoportSL {__version__}")
        self.resize(1280, 800)
        self.setMinimumSize(1160, 640)

        self.settings, settings_warning = load_settings()
        i18n.set_language(str(self.settings["language"]))
        self._settings_closed = False
        self._settings_lock = Lock()
        self._settings_pending: tuple[Path, dict] | None = None
        self._settings_writer_active = False
        self._settings_executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="coportsl-settings")
        prune_history(int(self.settings.get("history_limit", 200)))
        theme_module.apply_theme(
            QApplication.instance(), str(self.settings["theme"]))

        self.process: QProcess | None = None
        self.stdout_buffer = ""
        self.cancelled = False
        self.cancel_file: Path | None = None
        self.job_records: list[dict] = []
        self.current_record: dict | None = None
        self._log_stream = None
        self._start_time = 0.0
        self._on_success = None

        self._build()
        restored_parameters = self._restore_parameter_state()
        self._apply_settings_effects()

        last = self.settings["last_paths"]
        restored_paths = any(last.get(key) for key in ("data", "grid", "output"))
        if restored_paths:
            self.data_page.set_paths(
                last.get("data", ""), last.get("grid", ""),
                last.get("output", ""))
        self._setup_parameter_autosave()
        self._update_summary()
        i18n.retranslate_widget_tree(self)
        if settings_warning:
            self._show_status(settings_warning, 15000)
        elif restored_paths or restored_parameters:
            restored = "数据路径和参数" if \
                restored_paths and restored_parameters else \
                ("数据路径" if restored_paths else "参数")
            self._show_status(
                f"已自动恢复上次使用的{restored}", 8000)

    def _show_status(self, message: str, timeout: int = 0) -> None:
        """Show a localized status-bar message."""
        self.statusBar().showMessage(i18n.tr(message), timeout)

    # ------------------------------------------------------------------Interface

    def _build(self) -> None:
        from .pages.data_page import DataPage
        from .pages.flux_page import FluxPage
        from .pages.compute_page import ComputePage
        from .pages.postprocess_page import PostprocessPage
        from .pages.grmhd_page import GrmhdPage
        from .pages.benchmark_page import BenchmarkPage
        from .pages.history_page import HistoryPage
        from .pages.settings_page import SettingsPage

        self.nav = NavigationBar(
            list(zip(NAV_ITEMS, NAV_ICONS)),
            theme=str(self.settings["theme"]))
        self.nav.setFixedWidth(172)

        # Brand header: black hole logo + name
        self.brand_logo = QLabel()
        self.brand_title = QLabel("CoportSL")
        self.brand_title.setObjectName("brandTitle")
        self.brand_sub = QLabel("GRRT 桌面工作站")
        self.brand_sub.setObjectName("brandSub")
        brand_text = QVBoxLayout()
        brand_text.setContentsMargins(0, 0, 0, 0)
        brand_text.setSpacing(0)
        brand_text.addWidget(self.brand_title)
        brand_text.addWidget(self.brand_sub)
        brand = QWidget()
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(14, 12, 8, 8)
        brand_layout.setSpacing(10)
        brand_layout.addWidget(self.brand_logo)
        brand_layout.addLayout(brand_text, 1)

        side = QWidget()
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(0)
        side_layout.addWidget(brand)
        side_layout.addWidget(self.nav, 1)
        side.setFixedWidth(172)

        # Top data summary
        self.summary_data = QLabel("数据：未选择")
        self.summary_frames = QLabel("帧：—")
        self.summary_grid = QLabel("网格：—")
        self.summary_output = QLabel("结果：—")
        for label in (self.summary_frames, self.summary_grid,
                      self.summary_output):
            label.setProperty("dim", True)
        summary = QFrame()
        summary.setObjectName("summaryBar")
        summary_layout = QHBoxLayout(summary)
        summary_layout.setContentsMargins(14, 8, 14, 8)
        summary_layout.setSpacing(18)
        summary_layout.addWidget(self.summary_data)
        summary_layout.addWidget(self.summary_frames)
        summary_layout.addWidget(self.summary_grid)
        summary_layout.addWidget(self.summary_output, 1)

        glow = QFrame()
        glow.setObjectName("glowDivider")
        glow.setFixedHeight(2)

        self.data_page = DataPage(self)
        self.flux_page = FluxPage(self)
        self.compute_page = ComputePage(self)
        self.postprocess_page = PostprocessPage(self)
        self.grmhd_page = GrmhdPage(self)
        self.benchmark_page = BenchmarkPage(self)
        self.history_page = HistoryPage(self)
        self.settings_page = SettingsPage(self)

        self.stack = QStackedWidget()
        for page in (self.data_page, self.flux_page, self.compute_page,
                     self.postprocess_page, self.grmhd_page,
                     self.benchmark_page, self.history_page,
                     self.settings_page):
            self.stack.addWidget(page)

        # Keep common actions outside the page scroll area so they remain visible beside long forms.
        self.quick_context = QLabel("数据准备")
        self.quick_context.setObjectName("quickContext")
        self.quick_check = QPushButton("检查当前设置")
        self.quick_analysis = QPushButton("慢光前置分析")
        self.quick_run = QPushButton("运行当前任务")
        self.quick_run.setProperty("primary", True)
        self.quick_open = QPushButton("打开结果目录")
        for button in (
            self.quick_check,
            self.quick_analysis,
            self.quick_run,
            self.quick_open,
        ):
            button.setProperty("quickAction", True)
        self.quick_check.clicked.connect(self._quick_check)
        self.quick_analysis.clicked.connect(self.compute_page.run_analysis)
        self.quick_run.clicked.connect(self._quick_run)
        self.quick_open.clicked.connect(self._quick_open_output)
        self.quick_analysis.setVisible(False)
        self._refresh_quick_icons()

        quick_bar = QFrame()
        quick_bar.setObjectName("quickActionBar")
        quick_layout = QHBoxLayout(quick_bar)
        quick_layout.setContentsMargins(14, 8, 10, 8)
        quick_layout.setSpacing(8)
        quick_layout.addWidget(self.quick_context)
        quick_layout.addStretch(1)
        quick_layout.addWidget(self.quick_check)
        quick_layout.addWidget(self.quick_analysis)
        quick_layout.addWidget(self.quick_run)
        quick_layout.addWidget(self.quick_open)
        self.quick_action_bar = quick_bar

        self.drawer = TaskDrawer()
        self.drawer.cancel_requested.connect(self.cancel_job)
        self.drawer.open_output_requested.connect(self._open_drawer_output)

        # Avoid shadows on large parameter cards because they trigger full-card offscreen repainting.
        from .widgets.shadow import apply_shadow

        self._card_shadows = [
            apply_shadow(summary, blur=14.0, dy=2.0),
            apply_shadow(quick_bar, blur=14.0, dy=2.0),
        ]
        self._update_shadow_colors()

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(10, 8, 10, 4)
        center_layout.setSpacing(6)
        center_layout.addWidget(summary)
        center_layout.addWidget(glow)
        center_layout.addWidget(quick_bar)
        center_layout.addWidget(self.stack, 1)

        splitter = QSplitter()
        splitter.addWidget(side)
        splitter.addWidget(center)
        splitter.setStretchFactor(1, 1)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.addWidget(splitter)
        main_splitter.addWidget(self.drawer)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setCollapsible(0, False)
        main_splitter.setCollapsible(1, False)
        self.setCentralWidget(main_splitter)

        self.nav.current_changed.connect(self._nav_changed)
        self.nav.set_current(0)
        self._refresh_brand()
        self.data_page.paths_changed.connect(self._update_summary)

        self.elapsed_timer = QTimer(self)
        self.elapsed_timer.setInterval(500)
        self.elapsed_timer.timeout.connect(self._tick_elapsed)

        self._show_status("就绪")

    def _nav_changed(self, row: int) -> None:
        if 0 <= row < self.stack.count():
            self.stack.setCurrentIndex(row)
            self._update_quick_actions(row)

    def _update_quick_actions(self, row: int) -> None:
        """Let the fixed action bar switch semantics and available status with the current page."""
        contexts = {
            0: ("数据与模型准备", self.data_page),
            1: ("Flux 定标", self.flux_page),
            2: ("正式计算", self.compute_page),
            3: ("后处理", self.postprocess_page),
            4: ("GRMHD 工具", self.grmhd_page),
            5: ("性能基准", self.benchmark_page),
            6: ("运行记录", None),
            7: ("设置", None),
        }
        title, page = contexts.get(row, ("当前页面", None))
        self.quick_context.setText(title)
        check = getattr(page, "check_current_settings", None)
        run = getattr(page, "run_current_task", None)
        active = self.process is not None
        self.quick_check.setEnabled(callable(check) and not active)
        self.quick_run.setEnabled(callable(run) and not active)
        show_analysis = row == 2
        self.quick_analysis.setVisible(show_analysis)
        self.quick_analysis.setEnabled(show_analysis and not active)
        busy_hint = "当前任务结束或取消后才能执行此操作。" if active else ""
        self.quick_check.setToolTip(busy_hint if callable(check) else "")
        self.quick_run.setToolTip(busy_hint if callable(run) else "")
        self.quick_analysis.setToolTip(
            busy_hint if active else
            "单独运行慢光前置分析，不改变当前选中的正式计算任务。")
        self.quick_run.setText(
            str(getattr(page, "run_action_text", "运行当前任务"))
            if page is not None else "运行当前任务")

    def _refresh_task_controls(self) -> None:
        """Synchronize all controls that can initiate or destroy job status."""
        self._update_quick_actions(self.stack.currentIndex())
        active = self.process is not None
        self.history_page.set_task_active(active)
        self.benchmark_page.set_task_active(active)

    def _quick_check(self) -> None:
        if self.process is not None:
            self._show_status(BUSY_MESSAGE, 5000)
            return
        page = self.stack.currentWidget()
        action = getattr(page, "check_current_settings", None)
        if callable(action):
            action()
            return
        self._show_status("当前页面没有需要检查的设置", 5000)

    def _quick_run(self) -> None:
        if self.process is not None:
            self._show_status(BUSY_MESSAGE, 5000)
            return
        page = self.stack.currentWidget()
        action = getattr(page, "run_current_task", None)
        if callable(action):
            action()
            return
        self._show_status("当前页面没有统一的运行操作", 5000)

    def _quick_open_output(self) -> None:
        text = self.data_page.output.text()
        if not text:
            QMessageBox.information(
                self, "尚未选择结果目录", "请先在数据页选择结果根目录。")
            return
        path = Path(text).expanduser()
        if not path.is_dir():
            QMessageBox.warning(
                self, "结果目录不存在",
                f"当前结果目录尚不存在：\n{path}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))

    def _apply_settings_effects(self) -> None:
        self.drawer.set_max_lines(int(self.settings["log_lines"]))
        self._propagate_theme()

    def _propagate_theme(self) -> None:
        name = str(self.settings["theme"])
        self.drawer.set_theme(name)
        self.nav.set_theme(name)
        self.compute_page.set_theme(name)
        self._refresh_quick_icons()
        for widget in self.findChildren(Banner) + self.findChildren(StatusBadge):
            widget.set_theme(name)
        self._refresh_brand()
        self._update_shadow_colors()

    def _refresh_quick_icons(self) -> None:
        colors = theme_module.palette(str(self.settings["theme"]))
        dpr = self.devicePixelRatioF()
        self.quick_check.setIcon(
            icon_factory.icon("check", colors["text"], 18, dpr))
        self.quick_analysis.setIcon(
            icon_factory.icon("analysis", colors["text"], 18, dpr))
        self.quick_run.setIcon(
            icon_factory.icon("play", colors["accent_text"], 18, dpr))
        self.quick_open.setIcon(
            icon_factory.icon("folder", colors["text"], 18, dpr))

    def _update_shadow_colors(self) -> None:
        from PySide6.QtGui import QColor

        if str(self.settings["theme"]) == "dark":
            color = QColor(0, 0, 0, 90)
        else:
            color = QColor(70, 85, 110, 45)
        for effect in getattr(self, "_card_shadows", []):
            effect.setColor(color)

    def _refresh_brand(self) -> None:
        dpr = self.devicePixelRatioF()
        self.brand_logo.setPixmap(icon_factory.brand_pixmap(40, dpr))
        self.setWindowIcon(QIcon(icon_factory.brand_pixmap(64, dpr)))

    def update_settings(self, partial: dict) -> None:
        language_changed = "language" in partial and \
            partial["language"] != self.settings["language"]
        theme_changed = "theme" in partial and \
            partial["theme"] != self.settings["theme"]
        self.settings.update(partial)
        if language_changed:
            i18n.set_language(str(self.settings["language"]))
        write_json(
            app_data_dir() / "settings.json", self.settings, durable=False)
        if theme_changed:
            theme_module.apply_theme(
                QApplication.instance(), str(self.settings["theme"]))
            self._propagate_theme()
        self._apply_settings_effects()
        if language_changed:
            i18n.retranslate_widget_tree(self)
            self._update_summary()
            self._update_quick_actions(self.stack.currentIndex())
        self._show_status("设置已保存", 5000)

    # --------------------------------------------------------------- Parameter memory

    def _parameter_roots(self) -> tuple[tuple[str, object], ...]:
        """Stable listing of pages and shared parameter panels that need to be restored across startups."""
        roots: list[tuple[str, object]] = [
            ("data", self.data_page),
            ("flux", self.flux_page),
            ("compute", self.compute_page),
            ("postprocess", self.postprocess_page),
            ("grmhd", self.grmhd_page),
            ("benchmark", self.benchmark_page),
        ]
        for name, panel in (
            ("model", self.data_page.model_panel),
            ("camera", self.data_page.camera_panel),
            ("ray", self.data_page.ray_panel),
            ("benchmark_model", self.benchmark_page.reference_model_panel),
            ("benchmark_camera", self.benchmark_page.reference_camera_panel),
            ("benchmark_ray", self.benchmark_page.reference_ray_panel),
        ):
            if panel is not None:
                roots.insert(1, (name, panel))
        return tuple(roots)

    def _restore_parameter_state(self) -> bool:
        state = self.settings.get("last_parameters", {})
        if not isinstance(state, dict) or \
                state.get("version") != STATE_VERSION:
            return False
        values = state.get("values")
        if not isinstance(values, dict) or not values:
            return False
        values = dict(values)
        if "data.distance" not in values and "flux.distance" in values:
            values["data.distance"] = values["flux.distance"]
        for old, new in {
            "postprocess.evpa_workers": "postprocess.workers",
            "postprocess.evpa_png": "postprocess.png",
            "postprocess.evpa_pdf": "postprocess.pdf",
            "compute.sample_dt": "data.sample_dt",
            "compute.tolerance_boxes.jI": "data.tolerance_boxes.jI",
            "compute.tolerance_boxes.jP": "data.tolerance_boxes.jP",
            "compute.tolerance_boxes.aI": "data.tolerance_boxes.aI",
            "compute.tolerance_boxes.aP": "data.tolerance_boxes.aP",
            "compute.tolerance_boxes.rhoV": "data.tolerance_boxes.rhoV",
            "compute.tolerance_boxes.rhoC": "data.tolerance_boxes.rhoC",
        }.items():
            if new not in values and old in values:
                values[new] = values[old]

        region_texts = values.get("compute.region_texts")
        if isinstance(region_texts, dict):
            safe_texts = {
                key: self.compute_page.migrate_region_text(key, text)
                for key, text in region_texts.items()
                if key in {"shell", "jet_shell"}
                and isinstance(text, str)
                and len(text) <= 100_000
            }
            self.compute_page._region_texts.update(safe_texts)

        partition_value = values.get("compute.partition")
        saved_partition = partition_value.get("data") \
            if isinstance(partition_value, dict) else None
        active_regions = values.get("compute.region_sets")
        if saved_partition in {"shell", "jet_shell"} and \
                isinstance(active_regions, str):
            values["compute.region_sets"] = \
                self.compute_page.migrate_region_text(
                    str(saved_partition), active_regions)

        restored = restore_state(self._parameter_roots(), values)

        # The custom area name should be selected again after partition and text recovery and drop-down option reconstruction.
        manual = values.get("compute.manual_set")
        if isinstance(manual, dict):
            index = self.compute_page.manual_set.findData(manual.get("data"))
            if index < 0 and isinstance(manual.get("text"), str):
                index = self.compute_page.manual_set.findText(manual["text"])
            if index >= 0:
                self.compute_page.manual_set.setCurrentIndex(index)
                restored.add("compute.manual_set")

        task = values.get("compute.task")
        if isinstance(task, str) and task in self.compute_page.task_buttons:
            button = self.compute_page.task_buttons[task]
            button.setChecked(True)
            self.compute_page._task_changed(
                self.compute_page.task_group.id(button))
            restored.add("compute.task")
        parameter_group = values.get("data.parameter_group")
        if isinstance(parameter_group, str) and \
                parameter_group in self.data_page.parameter_buttons:
            self.data_page.select_parameter_group(parameter_group)
            restored.add("data.parameter_group")
        benchmark_group = values.get("benchmark.parameter_group")
        if isinstance(benchmark_group, str) and \
                benchmark_group in self.benchmark_page.parameter_buttons:
            self.benchmark_page.select_parameter_group(benchmark_group)
            restored.add("benchmark.parameter_group")
        return bool(restored)

    def _setup_parameter_autosave(self) -> None:
        self._parameter_save_timer = QTimer(self)
        self._parameter_save_timer.setSingleShot(True)
        self._parameter_save_timer.setInterval(600)
        self._parameter_save_timer.timeout.connect(
            self._save_parameter_state)
        connect_changes(self._parameter_roots(), self._schedule_parameter_save)
        for button in self.compute_page.task_buttons.values():
            button.toggled.connect(self._schedule_parameter_save)
        for button in self.data_page.parameter_buttons.values():
            button.toggled.connect(self._schedule_parameter_save)
        for button in self.benchmark_page.parameter_buttons.values():
            button.toggled.connect(self._schedule_parameter_save)

    def _schedule_parameter_save(self, *_args) -> None:
        self._parameter_save_timer.start()

    def _save_parameter_state(self) -> None:
        previous = self.settings.get("last_parameters", {}).get("values", {})
        if not isinstance(previous, dict):
            previous = {}
        values = capture_state(self._parameter_roots(), previous)
        values.pop("flux.distance", None)
        values["data.parameter_group"] = \
            self.data_page.current_parameter_group()
        values["benchmark.parameter_group"] = \
            self.benchmark_page.current_parameter_group()
        values["compute.task"] = self.compute_page.current_task()
        values["compute.region_texts"] = dict(
            self.compute_page._region_texts)
        values["compute.region_texts"][
            str(self.compute_page.partition.currentData())
        ] = self.compute_page.region_sets.toPlainText()
        self.settings["last_parameters"] = {
            "version": STATE_VERSION,
            "values": values,
        }
        self._queue_settings_write()

    def _queue_settings_write(self) -> None:
        """Writes a snapshot of the latest settings in the background; successive changes are merged into the last one."""
        if self._settings_closed:
            return
        snapshot = deepcopy(self.settings)
        path = app_data_dir() / "settings.json"
        with self._settings_lock:
            self._settings_pending = (path, snapshot)
            if self._settings_writer_active:
                return
            self._settings_writer_active = True
        self._settings_executor.submit(self._drain_settings_writes)

    def _drain_settings_writes(self) -> None:
        """Writes the current latest snapshot serially and absorbs new snapshots arriving during the write."""
        while True:
            with self._settings_lock:
                pending = self._settings_pending
                self._settings_pending = None
                if pending is None:
                    self._settings_writer_active = False
                    return
            path, snapshot = pending
            try:
                write_json(path, snapshot, durable=False)
            except OSError:
                pass

    # ------------------------------------------------------------------ Summary column

    def _update_summary(self) -> None:
        data_text = self.data_page.data.text()
        if data_text:
            self.summary_data.setText(f"数据：{data_text}")
            self.summary_frames.setText(self.data_page.frame_summary.text())
        else:
            self.summary_data.setText("数据：未选择")
            self.summary_frames.setText("帧：—")
        grid_text = self.data_page.grid.text()
        self.summary_grid.setText(
            f"网格：{Path(grid_text).name}" if grid_text else "网格：—")
        output_text = self.data_page.output.text()
        self.summary_output.setText(
            f"结果：{output_text}" if output_text else "结果：—")
        self.settings["last_paths"] = {
            "data": data_text,
            "grid": grid_text,
            "output": output_text,
        }
        self._queue_settings_write()

    # --------------------------------------------------------------- Page jump

    def goto_compute_task(self, task: str) -> None:
        button = self.compute_page.task_buttons.get(task)
        if button:
            button.setChecked(True)
            self.compute_page._task_changed(
                self.compute_page.task_group.id(button))
        self.nav.set_current(2)

    def apply_flux_mdot(self, value: float) -> None:
        self.data_page.set_mdot(value)
        self._show_status(
            f"已把建议吸积率 {value:.6g} 写入正式计算页", 8000)

    # --------------------------------------------------------------- Verification

    def validate_job(self, kind: str, job: dict) -> tuple[bool, str]:
        """Use Worker --validate-config to do trusted boundary verification (synchronous, fast)."""
        if self.process is not None:
            return False, BUSY_MESSAGE
        try:
            worker = find_worker(kind)
        except FileNotFoundError as error:
            return False, str(error)
        try:
            path = write_json(
                app_data_dir() / "jobs" / f"validate-{new_job_id()}.json",
                job,
            )
        except (OSError, TypeError, ValueError) as error:
            return False, f"无法保存临时校验配置：{error}"
        try:
            result = run_worker(worker, ["--validate-config", str(path)])
        except Exception as error:  # noqa: BLE001
            return False, f"校验进程失败：{error}"
        finally:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        message = (result.stderr or result.stdout).strip()
        return result.returncode == 0, message

    def check_cpu(self, mode: str) -> tuple[bool, str]:
        if self.process is not None:
            return False, BUSY_MESSAGE
        try:
            worker = find_worker("benchmark")
        except FileNotFoundError as error:
            return False, str(error)
        try:
            result = run_worker(worker, ["--check-cpu", mode])
        except Exception as error:  # noqa: BLE001
            return False, str(error)
        message = (result.stdout or result.stderr).strip()
        return result.returncode == 0, message

    def inspect_input(self) -> None:
        if self.process is not None:
            self.data_page.banner.show_message("warn", BUSY_MESSAGE)
            return
        try:
            job = self.compute_page.build_job()
        except ValueError as error:
            self.data_page.banner.show_message("error", str(error))
            return
        self.run_worker_job(
            title="输入检查（inspect-input）",
            kind="grrt",
            job=job,
            output_dir=None,
            arguments_extra=["--inspect-input"],
        )

    # ------------------------------------------------------------------ Mission

    def run_worker_job(
        self,
        *,
        title: str,
        kind: str,
        job: dict,
        output_dir: Path | None,
        on_success=None,
        arguments_extra: list[str] | None = None,
    ) -> bool:
        """Run a C++ worker job while enforcing the single-active-job rule."""
        if self.process is not None:
            QMessageBox.information(
                self, "已有任务在运行", BUSY_MESSAGE)
            return False
        try:
            worker = find_worker(kind)
        except FileNotFoundError as error:
            QMessageBox.critical(self, "找不到内部计算程序", str(error))
            return False
        arguments = [*(arguments_extra or []), "--config"]
        return self._start_process(
            title=title, program=str(worker), arguments=arguments,
            kind=kind, job=job, output_dir=output_dir,
            on_success=on_success)

    def run_internal_job(
        self,
        *,
        title: str,
        kind: str,
        job: dict,
        output_dir: Path | None,
        on_success=None,
    ) -> bool:
        """Run Python internal Worker (postprocess/evpa)."""
        if self.process is not None:
            QMessageBox.information(
                self, "已有任务在运行", BUSY_MESSAGE)
            return False
        if getattr(sys, "frozen", False):
            program = sys.executable
            arguments = ["--internal-worker", kind]
        else:
            program = sys.executable
            arguments = ["-m", "desktop", "--internal-worker", kind]
        return self._start_process(
            title=title, program=program, arguments=arguments,
            kind=kind, job=job, output_dir=output_dir,
            on_success=on_success,
            working_directory=str(runtime_root()))

    def _start_process(
        self,
        *,
        title: str,
        program: str,
        arguments: list[str],
        kind: str,
        job: dict,
        output_dir: Path | None,
        on_success,
        working_directory: str | None = None,
    ) -> bool:
        if self.process is not None:
            QMessageBox.information(
                self, "已有任务在运行", BUSY_MESSAGE)
            return False
        job_id = new_job_id()
        job["job_id"] = job_id
        jobs_dir = app_data_dir() / "jobs"
        cancel_file = jobs_dir / f"{job_id}.cancel"
        try:
            paths = job.setdefault("paths", {})
            if not isinstance(paths, dict):
                raise ValueError("作业中的 paths 必须是对象。")
            paths["cancel_file"] = str(cancel_file.resolve())
            job_path = write_json(jobs_dir / f"{job_id}.json", job)
        except (OSError, TypeError, ValueError) as error:
            QMessageBox.critical(self, "无法保存作业配置", str(error))
            return False
        log_path = jobs_dir / f"{job_id}.log"
        try:
            self._log_stream = log_path.open("w", encoding="utf-8",
                                             errors="replace", newline="\n")
        except OSError as error:
            QMessageBox.critical(self, "无法写入日志", str(error))
            try:
                job_path.unlink(missing_ok=True)
            except OSError:
                pass
            return False
        self.cancel_file = cancel_file

        process = QProcess(self)
        process.setProgram(program)
        process.setArguments([*arguments, str(job_path)])
        if working_directory:
            process.setWorkingDirectory(working_directory)
        process.setProcessChannelMode(QProcess.SeparateChannels)
        process.readyReadStandardOutput.connect(self._read_stdout)
        process.readyReadStandardError.connect(self._read_stderr)
        process.finished.connect(self._finished)
        process.errorOccurred.connect(
            lambda error, owner=process: self._process_error(owner, error))

        self.process = process
        self.cancelled = False
        self.stdout_buffer = ""
        self._start_time = time.monotonic()
        self._on_success = on_success
        self.current_record = {
            "job_id": job_id,
            "title": title,
            "kind": kind,
            "status": "running",
            "started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "finished": "",
            "exit_code": None,
            "log_path": log_path,
            "job_path": job_path,
            "output_path": str(output_dir.resolve()) if output_dir else "",
        }
        self.job_records.append(self.current_record)
        try:
            save_state(self.current_record)
        except OSError as error:
            self._write_log_line(f"# 无法保存作业状态：{error}")

        self.drawer.begin(title)
        self._refresh_task_controls()
        if output_dir is not None:
            self.drawer.set_output_dir(output_dir)
        self._show_status(f"正在运行：{title}")
        self.elapsed_timer.start()
        self._write_log_line(f"# {title}")
        self._write_log_line(f"# 作业文件：{job_path}")
        process.start()
        return True

    # --------------------------------------------------------------- Event

    def _process_error(
        self,
        process: QProcess,
        error: QProcess.ProcessError,
    ) -> None:
        """Log asynchronous process errors and close the finished signal path for "Program cannot be started"."""
        if process is not self.process:
            return
        message = f"内部程序错误：{process.errorString()}"
        self.drawer.append_log(message, error=True)
        self._write_log_line(f"[process] {message}")
        if error == QProcess.ProcessError.FailedToStart:
            QTimer.singleShot(
                0, lambda owner=process: self._finish_failed_start(owner))

    def _finish_failed_start(self, process: QProcess) -> None:
        if process is self.process and \
                process.state() == QProcess.ProcessState.NotRunning:
            self._finished(-1, QProcess.ExitStatus.CrashExit)

    def _tick_elapsed(self) -> None:
        seconds = int(time.monotonic() - self._start_time)
        self.drawer.set_elapsed(f"耗时 {seconds // 60:02d}:{seconds % 60:02d}")

    def _write_log_line(self, line: str) -> None:
        if self._log_stream is not None:
            try:
                self._log_stream.write(line + "\n")
                self._log_stream.flush()
            except OSError:
                pass

    def _read_stdout(self) -> None:
        if self.process:
            self.stdout_buffer += bytes(
                self.process.readAllStandardOutput()).decode("utf-8", "replace")
            lines = self.stdout_buffer.split("\n")
            self.stdout_buffer = lines.pop()
            for line in lines:
                self._handle_stdout_line(line.rstrip("\r"))

    def _handle_stdout_line(self, line: str) -> None:
        if not line:
            return
        event = parse_event_line(line)
        if event is None:
            self.drawer.append_log(line)
            self._write_log_line(line)
            return
        self._write_log_line(line)
        event_type = event.get("type")
        if self.cancelled and event_type in {"progress", "stage"}:
            return
        if event_type == "progress":
            try:
                self.drawer.set_progress(
                    int(event["current"]), int(event["total"]),
                    event.get("frame"))
            except (KeyError, TypeError, ValueError):
                self.drawer.append_log(line)
        elif event_type == "stage":
            self.drawer.set_stage(str(event.get("name", "")))
        elif event_type == "result":
            path = str(event.get("path", ""))
            if path:
                self.drawer.set_output_dir(Path(path))
                if self.current_record is not None:
                    self.current_record["output_path"] = path
            self.drawer.append_log(f"结果：{path}")
        elif event_type == "warning":
            self.drawer.append_log(str(event.get("message", "")))
        elif event_type == "error":
            self.drawer.append_log(str(event.get("message", "")), error=True)
        else:
            self.drawer.append_log(line)

    def _read_stderr(self) -> None:
        if self.process:
            text = bytes(
                self.process.readAllStandardError()).decode("utf-8", "replace")
            for line in text.rstrip("\n").split("\n"):
                if line:
                    self.drawer.append_log(line, error=True)
                    self._write_log_line(f"[stderr] {line}")

    def _finished(self, exit_code: int, status: QProcess.ExitStatus) -> None:
        if self.process is None or self.current_record is None:
            return
        # The finished signal may arrive before the last readyRead and be actively emptied before exiting.
        self._read_stdout()
        self._read_stderr()
        if self.stdout_buffer:
            self._handle_stdout_line(self.stdout_buffer)
            self.stdout_buffer = ""
        self.elapsed_timer.stop()
        seconds = int(time.monotonic() - self._start_time)
        self.drawer.set_elapsed(f"耗时 {seconds // 60:02d}:{seconds % 60:02d}")

        crashed = status == QProcess.CrashExit
        if self.cancelled:
            final = "cancelled"
            message = "任务已取消；中断的结果目录不会标记为 complete。"
            self.drawer.cancel_progress()
        elif exit_code == 0 and not crashed:
            final = "success"
            message = "运行完成"
            self.drawer.finish_progress()
        else:
            final = "failed"
            self.drawer.fail_progress()
            detail = f"退出码 {exit_code}"
            if crashed:
                detail += "（进程异常结束）"
            message = (
                f"运行失败（{detail}）。完整日志："
                f"{self.current_record['log_path']}")
        self.drawer.set_status(final)
        self._show_status(message, 30000)
        if final != "success":
            self.drawer.append_log(message, error=(final == "failed"))

        record = self.current_record
        if record is not None:
            record["status"] = final
            record["finished"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            record["exit_code"] = exit_code
            try:
                save_state(record)
            except OSError as error:
                self.drawer.append_log(
                    f"无法保存作业历史：{error}", error=True)
        if final == "success" and self._on_success is not None:
            try:
                self._on_success(self.drawer.log_text())
            except Exception as error:  # noqa: BLE001
                self.drawer.append_log(f"结果解析失败：{error}", error=True)
        self._on_success = None
        self.current_record = None
        self.cancelled = False
        self.process = None
        self._refresh_task_controls()
        if self.cancel_file is not None:
            try:
                self.cancel_file.unlink(missing_ok=True)
            except OSError:
                pass
            self.cancel_file = None
        if self._log_stream is not None:
            try:
                self._log_stream.close()
            except OSError:
                pass
            self._log_stream = None
        self.history_page.refresh()
        prune_history(int(self.settings.get("history_limit", 200)))

    def cancel_job(self) -> None:
        if self.process is None:
            return
        answer = QMessageBox.question(
            self,
            "取消任务",
            "确定取消当前任务吗？\n"
            "程序会先请求内部计算程序在当前帧边界安全停止；"
            "已写出的部分结果不会标记为完整。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.cancelled = True
        self.drawer.set_cancelling()
        self.drawer.append_log(
            "用户请求取消，已发送安全停止标记，正在等待当前计算单元结束…")
        try:
            if self.cancel_file is None:
                raise OSError("取消标记路径不可用")
            self.cancel_file.parent.mkdir(parents=True, exist_ok=True)
            self.cancel_file.write_text("cancel\n", encoding="utf-8")
        except OSError as error:
            self.drawer.append_log(
                f"无法写入安全停止标记：{error}；将请求终止进程。",
                error=True)
            self.process.terminate()
            QTimer.singleShot(2000, self._force_kill_if_needed)
            return
        QTimer.singleShot(5000, self._offer_force_terminate)

    def _offer_force_terminate(self) -> None:
        if self.process is None or not self.cancelled:
            return
        answer = QMessageBox.question(
            self,
            "安全取消仍在等待",
            "内部计算程序尚未到达安全停止边界。是否强制终止进程？\n"
            "强制终止可能留下未完成的当前帧文件。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes and self.process is not None:
            self.drawer.append_log("正在强制终止进程…")
            self._force_kill_if_needed()

    def _force_kill_if_needed(self) -> None:
        if self.process is not None and self.cancelled:
            self.drawer.append_log("进程未响应终止请求，强制结束。")
            process = self.process
            pid = int(process.processId())
            if sys.platform == "win32" and pid > 0:
                try:
                    completed = subprocess.run(
                        ["taskkill", "/PID", str(pid), "/T", "/F"],
                        check=False,
                        capture_output=True,
                        text=True,
                        creationflags=getattr(
                            subprocess, "CREATE_NO_WINDOW", 0),
                    )
                    if completed.returncode == 0:
                        return
                except OSError as error:
                    self.drawer.append_log(
                        f"无法调用系统进程树终止工具：{error}；"
                        "改为终止直接进程。",
                        error=True,
                    )
            process.kill()

    def _open_drawer_output(self) -> None:
        path = self.drawer.output_dir()
        if path is None:
            return
        try:
            path.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(path.resolve().as_uri())
        except OSError as error:
            QMessageBox.warning(self, "无法打开目录", str(error))

    # --------------------------------------------------------------- Close

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._settings_closed:
            event.accept()
            return
        self._parameter_save_timer.stop()
        self._save_parameter_state()
        if self.process is None:
            self._settings_closed = True
            self._settings_executor.shutdown(wait=True)
            event.accept()
            return
        answer = QMessageBox.question(
            self,
            "任务仍在运行",
            "关闭窗口会终止当前任务，部分结果将保留为未完成状态。\n"
            "确定关闭吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.cancelled = True
            self.drawer.set_cancelling()
            self.drawer.append_log(
                "窗口关闭前正在终止当前任务…")
            process = self.process
            self._force_kill_if_needed()
            if self.process is not None:
                process.waitForFinished(2000)
            if self.process is not None:
                # Some platforms do not send the finished signal during synchronization waiting, and still need to persist the cancellation state.
                self._finished(-1, QProcess.ExitStatus.CrashExit)
            self._settings_closed = True
            self._settings_executor.shutdown(wait=True)
            event.accept()
        else:
            event.ignore()
