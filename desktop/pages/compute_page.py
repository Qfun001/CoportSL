"""Imaging page for selecting a GRRT task and configuring task-specific parameters."""

from __future__ import annotations

import re

from PySide6.QtCore import QSize
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..widgets import icons as icon_factory
from ..widgets.asyncjob import run_async
from ..widgets.fields import (
    NoWheelComboBox,
    ParameterGrid,
    add_row,
    make_int,
)
from ..widgets.sections import Banner
from ..theme import palette
from .common import (
    TASK_CHOICES,
    WINDOW_CHOICES,
    build_grrt_job,
    load_capabilities,
    load_defaults,
)

TASK_ICONS = {
    "fast": "fast",
    "slow": "slow",
    "region_error": "target",
}

SELECTABLE_TASKS = tuple(
    item for item in TASK_CHOICES if item[1] != "analysis")


class ComputePage(QWidget):
    """Generate and verify GRRT jobs, and hand them over to the main window for unified scheduling."""

    def __init__(self, window, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.window = window
        self._slow_scan_job = None
        self.run_action_text = "运行正式计算"
        try:
            self.defaults = load_defaults("grrt")
            self.caps = load_capabilities("grrt")
            load_error = ""
        except Exception as error:  # noqa: BLE001
            self.defaults = None
            self.caps = {}
            load_error = str(error)

        self.banner = Banner()

        # task card
        self.task_group = QButtonGroup(self)
        self.task_buttons: dict[str, QPushButton] = {}
        self._card_effects = {}
        cards = QHBoxLayout()
        cards.setSpacing(8)
        for index, (label, value) in enumerate(SELECTABLE_TASKS):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setMinimumHeight(64)
            button.setProperty("card", True)
            button.setIconSize(QSize(22, 22))
            button.toggled.connect(
                lambda _checked, v=value: self._refresh_card_icon(v))
            self.task_group.addButton(button, index)
            self.task_buttons[value] = button
            cards.addWidget(button)
        self.task_group.idClicked.connect(self._task_changed)

        # General imaging, model, viewer, and lighting parameters are only set on the "Data & Model" page.
        shared = window.data_page
        self.electron = shared.electron
        self.npix = shared.npix
        self.frequency = shared.frequency
        self.fov = shared.fov
        self.mdot = shared.mdot
        self.model_panel = shared.model_panel
        self.camera_panel = shared.camera_panel
        self.ray_panel = shared.ray_panel
        self.sample_dt = shared.sample_dt
        self.tolerance_boxes = shared.tolerance_boxes
        # Task additional parameters
        self.task_stack = QStackedWidget()
        self._build_task_panels()
        self.region_box = self._build_region_panel()
        self.window.data_page.add_region_panel(self.region_box)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.banner)
        shared_note = QLabel(
            "通用模型、观者、光线、空间分区、命名集合与分析容差均在"
            "“数据与模型”页设置；此处只保留任务选择和专属参数。")
        shared_note.setProperty("dim", True)
        shared_note.setWordWrap(True)
        layout.addWidget(shared_note)
        self.task_cards = QWidget()
        self.task_cards.setLayout(cards)
        cards.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.task_cards)
        layout.addWidget(self.task_stack)
        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.task_buttons["fast"].setChecked(True)
        self._task_changed(0)
        self.set_theme(str(window.settings.get("theme", "dark")))
        if load_error:
            self.banner.show_message(
                "error",
                f"无法读取成像计算程序的默认配置：{load_error}。"
                "请确认内部计算程序已构建。")

    # -------------------------------------------------------- Mission Panel

    def _build_task_panels(self) -> None:
        defaults = self.defaults or {}
        slow_defaults = defaults.get("slow", {})
        region_defaults = defaults.get("region_error", {})

        # Fast
        fast_page = QWidget()
        fast_layout = ParameterGrid(fast_page)
        fast_layout.setContentsMargins(0, 4, 0, 4)
        fast_note = QLabel(
            "快光默认处理全部输入帧；也可填写连续帧范围用于小规模试算。")
        fast_note.setProperty("dim", True)
        fast_layout.addRow(fast_note)
        self.fast_custom_range = QCheckBox("手动指定输出帧范围")
        self.fast_frame_start = make_int(0, 0, 10_000_000)
        self.fast_frame_end = make_int(0, 0, 10_000_000)
        fast_layout.addRow("", self.fast_custom_range)
        add_row(fast_layout, "<i>n</i><sub>0</sub>", self.fast_frame_start,
                "手动范围的起始输出帧，包含该帧；关闭手动范围时自动输出"
                "全部可用帧。",
                unit="帧号")
        add_row(fast_layout, "<i>n</i><sub>1</sub>", self.fast_frame_end,
                "手动范围的结束输出帧，包含该帧。", unit="帧号")
        self.fast_custom_range.toggled.connect(self._frame_range_changed)
        self.task_stack.addWidget(fast_page)

        # Slow
        slow_page = QWidget()
        slow_form = ParameterGrid(slow_page)
        slow_form.setContentsMargins(0, 4, 0, 4)
        self.slow_match = QLabel("未检查匹配的前置分析")
        self.slow_match.setWordWrap(True)
        self.region_mode = NoWheelComboBox()
        self.region_mode.addItem("自动采用分析建议", "suggest")
        self.region_mode.addItem("手动选择命名集合", "manual")
        self.region_mode.currentIndexChanged.connect(self._slow_mode_changed)
        windows = tuple(self.caps.get("windows", WINDOW_CHOICES))
        self.window_combo = NoWheelComboBox()
        for value in windows:
            self.window_combo.addItem(value, value)
        index = self.window_combo.findData(slow_defaults.get("window", "p99"))
        if index >= 0:
            self.window_combo.setCurrentIndex(index)
        self.manual_set = NoWheelComboBox()
        add_row(slow_form, "匹配的前置分析", self.slow_match)
        add_row(slow_form, "区域模式", self.region_mode,
                "自动模式缺少匹配结果时，会先运行前置分析。")
        add_row(slow_form, "时间窗口", self.window_combo,
                "选择慢光区域时延分布的覆盖分位；决定安全输出范围和缓存跨度。")
        add_row(slow_form, "命名集合", self.manual_set,
                "名称来自下方可编辑的区域集合。")
        self.slow_custom_range = QCheckBox("手动指定输出帧范围")
        self.slow_frame_start = make_int(0, 0, 10_000_000)
        self.slow_frame_end = make_int(0, 0, 10_000_000)
        slow_form.addRow("", self.slow_custom_range)
        add_row(slow_form, "<i>n</i><sub>0</sub>", self.slow_frame_start,
                "手动范围的起始输出帧，包含该帧；范围必须落在当前时窗的"
                "安全基准帧内。",
                unit="帧号")
        add_row(slow_form, "<i>n</i><sub>1</sub>", self.slow_frame_end,
                "结束输出帧，包含该帧；范围外必要 GRMHD 帧仍用于时间"
                "插值缓存。", unit="帧号")
        self.slow_custom_range.toggled.connect(self._frame_range_changed)
        self.task_stack.addWidget(slow_page)
        self._slow_mode_changed()

        # RegionError
        region_page = QWidget()
        region_form = ParameterGrid(region_page)
        region_form.setContentsMargins(0, 4, 0, 4)
        self.region_frame_step = make_int(
            int(region_defaults.get("frame_step", 25)), 1, 10_000_000)
        add_row(region_form, "Δ<i>n</i>", self.region_frame_step,
                "从输入首帧开始每隔 Δn 帧取样；未对齐的末帧不额外加入。",
                unit="帧")
        region_note = QLabel(
            "区域误差按上方定义顺序一次扫描全部命名集合，分别关闭各集合"
            "外的发射系数或全部辐射转移系数，再与同帧完整快光图像比较。")
        region_note.setProperty("dim", True)
        region_note.setWordWrap(True)
        region_form.addRow(region_note)
        self.task_stack.addWidget(region_page)
        self._frame_range_changed()

    def _build_region_panel(self) -> QGroupBox:
        """Build a partitioned and named collection editor shared by all zone-related tasks."""
        slow = (self.defaults or {}).get("slow", {})
        self.partition = NoWheelComboBox()
        labels = {"shell": "径向壳层",
                  "jet_shell": "喷流、环境分别分层"}
        for value in self.caps.get("partitions", ("shell", "jet_shell")):
            self.partition.addItem(labels.get(value, value), value)
        selected = self.partition.findData(slow.get("partition", "shell"))
        if selected >= 0:
            self.partition.setCurrentIndex(selected)

        self.region_sets = QPlainTextEdit()
        self.region_sets.setMinimumHeight(104)
        self.region_sets.setPlaceholderText(
            "每行一个集合，例如：Omega1: north_000, south_000, non_jet_000")
        self.region_keys = QLabel()
        self.region_keys.setWordWrap(True)
        self.region_keys.setProperty("dim", True)
        self._region_texts: dict[str, str] = {}
        self._active_partition = str(self.partition.currentData())
        self.region_sets.setPlainText(self._format_region_sets(
            slow.get("region_sets") or
            self._default_region_sets(self._active_partition)))
        self._region_texts[self._active_partition] = \
            self.region_sets.toPlainText()

        self.partition.currentIndexChanged.connect(self._partition_changed)
        self.region_sets.textChanged.connect(self._region_sets_changed)

        box = QGroupBox("区域分区与命名集合")
        form = ParameterGrid(box)
        add_row(form, "空间分区", self.partition,
                "前置分析、慢光成像和区域误差共用；修改后会改变分析签名。")
        add_row(form, "命名集合", self.region_sets,
                "格式为“名称: key1, key2”；名称和键必须唯一。")
        form.addRow("可用区域键", self.region_keys)
        self._refresh_region_keys()
        self._region_sets_changed()
        return box

    @staticmethod
    def _format_region_sets(items) -> str:
        return "\n".join(
            f"{item['name']}: {', '.join(item['keys'])}"
            for item in items
        )

    @staticmethod
    def _legacy_jet_region_sets() -> list[dict]:
        """JetShell default for 0.5.1 and earlier, used only for parameter snapshot migrations."""
        return [
            {"name": "r20", "keys": [
                "north_000", "south_000", "non_jet_000"]},
            {"name": "r30", "keys": [
                "north_000", "south_000",
                "non_jet_000", "non_jet_001"]},
            {"name": "r50", "keys": [
                "north_000", "south_000",
                "non_jet_000", "non_jet_001", "non_jet_002"]},
            {"name": "r80", "keys": [
                "north_000", "south_000", "non_jet_000",
                "non_jet_001", "non_jet_002", "non_jet_003"]},
        ]

    @staticmethod
    def _legacy_shell_region_sets() -> list[dict]:
        """Shell defaults for 0.5.7 and earlier, used only for parameter snapshot migrations."""
        return [
            {"name": "r20", "keys": ["region_000"]},
            {"name": "r30", "keys": ["region_000", "region_001"]},
            {"name": "r50", "keys": [
                "region_000", "region_001", "region_002"]},
            {"name": "r80", "keys": [
                "region_000", "region_001", "region_002", "region_003"]},
        ]

    @staticmethod
    def _default_region_sets(partition: str) -> list[dict]:
        if partition == "jet_shell":
            return [
                {"name": "Omega1", "keys": [
                    "north_000", "south_000",
                    "non_jet_000", "non_jet_001", "non_jet_002"]},
                {"name": "Omega2", "keys": [
                    "north_000", "south_000", "south_001",
                    "non_jet_000", "non_jet_001", "non_jet_002"]},
                {"name": "Omega3", "keys": [
                    "north_000",
                    "south_000", "south_001", "south_002", "south_003",
                    "non_jet_000", "non_jet_001", "non_jet_002"]},
                {"name": "Omega4", "keys": [
                    "north_000",
                    "south_000", "south_001", "south_002", "south_003",
                    "south_004", "south_005",
                    "non_jet_000", "non_jet_001", "non_jet_002"]},
                {"name": "Omega5", "keys": [
                    "north_000", "north_001",
                    "south_000", "south_001", "south_002", "south_003",
                    "south_004", "south_005",
                    "non_jet_000", "non_jet_001", "non_jet_002",
                    "non_jet_003", "non_jet_004"]},
                {"name": "Omega6", "keys": [
                    "north_000", "north_001", "north_002", "north_003",
                    "south_000", "south_001", "south_002", "south_003",
                    "south_004", "south_005",
                    "non_jet_000", "non_jet_001", "non_jet_002",
                    "non_jet_003", "non_jet_004"]},
                {"name": "Omega7", "keys": [
                    "north_000", "north_001", "north_002", "north_003",
                    "north_004", "north_005",
                    "south_000", "south_001", "south_002", "south_003",
                    "south_004", "south_005",
                    "non_jet_000", "non_jet_001", "non_jet_002",
                    "non_jet_003", "non_jet_004", "non_jet_005"]},
            ]
        return [
            {"name": "r20", "keys": ["region_000"]},
            {"name": "r30", "keys": ["region_000", "region_001"]},
            {"name": "r50", "keys": [
                "region_000", "region_001", "region_002"]},
            {"name": "r80", "keys": [
                "region_000", "region_001", "region_002", "region_003"]},
            {"name": "r100", "keys": [
                "region_000", "region_001", "region_002", "region_003",
                "region_004"]},
            {"name": "r200", "keys": [
                "region_000", "region_001", "region_002", "region_003",
                "region_004", "region_005"]},
        ]

    @classmethod
    def migrate_region_text(cls, partition: str, text: str) -> str:
        """Only the old, as-is defaults are replaced; any user-defined text remains unchanged."""
        legacy_items = cls._legacy_jet_region_sets() \
            if partition == "jet_shell" else cls._legacy_shell_region_sets()
        legacy = cls._format_region_sets(legacy_items)
        if text.strip() != legacy.strip():
            return text
        return cls._format_region_sets(cls._default_region_sets(partition))

    def _parse_region_sets(self) -> list[dict]:
        partition = str(self.partition.currentData())
        available = {
            item["key"] for item in
            self.caps.get("regions_by_partition", {}).get(partition, [])
        }
        result = []
        names = set()
        for line_number, raw in enumerate(
                self.region_sets.toPlainText().splitlines(), 1):
            line = raw.strip()
            if not line:
                continue
            if ":" not in line:
                raise ValueError(
                    f"区域集合第 {line_number} 行缺少冒号。")
            name, values = line.split(":", 1)
            name = name.strip()
            keys = [value.strip() for value in values.split(",")
                    if value.strip()]
            if not name or name in names:
                raise ValueError(
                    f"区域集合第 {line_number} 行名称为空或重复：{name!r}")
            if re.fullmatch(r"[A-Za-z0-9_-]+", name) is None:
                raise ValueError(
                    f"区域集合 {name!r} 只能使用字母、数字、下划线和连字符。")
            if not keys or len(keys) != len(set(keys)):
                raise ValueError(
                    f"区域集合 {name} 的键为空或存在重复。")
            unknown = [key for key in keys if key not in available]
            if unknown:
                raise ValueError(
                    f"区域集合 {name} 含当前分区未知键：{', '.join(unknown)}")
            names.add(name)
            result.append({"name": name, "keys": keys})
        if not result:
            raise ValueError("至少需要一个区域集合。")
        return result

    def _partition_changed(self, *_args) -> None:
        self._region_texts[self._active_partition] = \
            self.region_sets.toPlainText()
        partition = str(self.partition.currentData())
        self._active_partition = partition
        text = self._region_texts.get(partition)
        if text is None:
            text = self._format_region_sets(
                self._default_region_sets(partition))
            self._region_texts[partition] = text
        self.region_sets.setPlainText(text)
        self._refresh_region_keys()

    def _refresh_region_keys(self) -> None:
        partition = str(self.partition.currentData())
        items = self.caps.get(
            "regions_by_partition", {}).get(partition, [])
        self.region_keys.setText("；".join(
            f"{item['key']}（{item['label']}）" for item in items))

    def _region_sets_changed(self) -> None:
        previous = self.manual_set.currentText()
        try:
            names = [item["name"] for item in self._parse_region_sets()]
        except ValueError:
            names = []
        self.manual_set.blockSignals(True)
        self.manual_set.clear()
        for name in names:
            self.manual_set.addItem(name, name)
        preferred = "Omega1" if \
            str(self.partition.currentData()) == "jet_shell" else "r50"
        index = self.manual_set.findData(previous)
        if index < 0:
            index = self.manual_set.findData(preferred)
        if index >= 0:
            self.manual_set.setCurrentIndex(index)
        self.manual_set.blockSignals(False)

    def set_theme(self, theme: str) -> None:
        """Redraw the task card icon when switching themes."""
        self._theme = theme
        for value in self.task_buttons:
            self._refresh_card_icon(value)

    def _refresh_card_icon(self, task: str) -> None:
        from PySide6.QtGui import QColor

        button = self.task_buttons[task]
        colors = palette(getattr(self, "_theme", "dark"))
        checked = button.isChecked()
        color = colors["accent"] if checked else colors["text_dim"]
        button.setIcon(icon_factory.icon(
            TASK_ICONS[task], color, 22, button.devicePixelRatioF()))
        effect = self._card_effects.get(task)
        if effect is not None:
            if checked:
                # Selected Card: Amber Glow
                glow = QColor(colors["accent"])
                glow.setAlpha(90)
                effect.setColor(glow)
                effect.setBlurRadius(26.0)
                effect.setOffset(0.0, 0.0)
            else:
                effect.setColor(QColor(0, 0, 0, 70))
                effect.setBlurRadius(14.0)
                effect.setOffset(0.0, 3.0)

    def _task_changed(self, index: int) -> None:
        self.task_stack.setCurrentIndex(index)
        task = SELECTABLE_TASKS[index][1]
        # The page is built before the main window's stack and action bar, so initialization needs no refresh.
        if hasattr(self.window, "stack"):
            self.window._update_quick_actions(self.window.stack.currentIndex())
        if task == "slow":
            self.refresh_slow_match()

    def _slow_mode_changed(self, *_args) -> None:
        manual = self.region_mode.currentData() == "manual"
        self.manual_set.setEnabled(manual)

    def _frame_range_changed(self, *_args) -> None:
        for enabled, start, end in (
            (self.fast_custom_range.isChecked(),
             self.fast_frame_start, self.fast_frame_end),
            (self.slow_custom_range.isChecked(),
             self.slow_frame_start, self.slow_frame_end),
        ):
            start.setEnabled(enabled)
            end.setEnabled(enabled)

    def set_mdot(self, value: float) -> None:
        """Recommended accretion rate written by Flux page."""
        self.window.data_page.set_mdot(value)

    def refresh_slow_match(self) -> None:
        """Asynchronously scans the complete Analysis as a conservative presence hint of match status.

        Exact signature matching is done at runtime by an internal calculation routine."""
        if self._slow_scan_job is not None and \
                self._slow_scan_job.is_running():
            return
        if not self.window.data_page.output.text():
            self.slow_match.setText(
                "尚未设置结果目录；运行时会在所选结果目录中匹配前置分析。")
            return
        output = self.window.data_page.output_dir()
        analysis_dir = output / "analysis"
        self.slow_match.setText("正在后台检查已完成的前置分析…")
        self._slow_scan_job = run_async(
            lambda: self._collect_complete_analysis(analysis_dir),
            lambda complete: self._slow_match_done(output, complete),
            lambda message: self._slow_match_failed(output, message),
        )

    @staticmethod
    def _collect_complete_analysis(analysis_dir) -> list[str]:
        complete = []
        if analysis_dir.is_dir():
            for child in sorted(analysis_dir.iterdir()):
                status = child / "status.txt"
                try:
                    if child.is_dir() and status.is_file():
                        value = ""
                        for line in status.read_text(
                            encoding="utf-8", errors="replace",
                        ).splitlines():
                            if not line:
                                continue
                            key = line.split("=", 1)[0] if "=" in line else \
                                line.split(" ", 1)[0]
                            if key in {"data", "grid", "output", "analysis"}:
                                continue
                            value = line.split(" ", 1)[0]
                        if value == "complete":
                            complete.append(child.name)
                except OSError:
                    continue
        return complete

    def _slow_match_done(self, output, complete: list[str]) -> None:
        if output != self.window.data_page.output_dir():
            return
        if complete:
            self.slow_match.setText(
                f"发现 {len(complete)} 个已完成的前置分析（最新：{complete[-1]}）；"
                "精确签名匹配由内部计算程序在运行时判定。")
        else:
            self.slow_match.setText(
                "结果目录中没有已完成的前置分析；自动模式会先执行前置分析，"
                "手动模式需要已有可解析的区域定义。")

    def _slow_match_failed(self, output, message: str) -> None:
        if output == self.window.data_page.output_dir():
            self.slow_match.setText(f"检查前置分析失败：{message}")

    # ----------------------------------------------------------Job generation

    def current_task(self) -> str:
        index = self.task_group.checkedId()
        if index < 0:
            index = 0
        return SELECTABLE_TASKS[index][1]

    def build_job(
        self,
        task_override: str | None = None,
    ) -> dict:
        if self.defaults is None:
            raise ValueError("成像默认配置不可用，无法生成作业。")
        task = task_override or self.current_task()
        analysis = None
        slow = None
        region_error = None
        region_config = {
            "partition": str(self.partition.currentData()),
            "region_sets": self._parse_region_sets(),
        }
        if task in {"analysis", "slow"}:
            analysis = self.window.data_page.analysis_config()
        if task == "analysis":
            slow = region_config
        elif task == "slow":
            slow = {
                **region_config,
                "region_mode": str(self.region_mode.currentData()),
                "window": str(self.window_combo.currentData()),
                "manual_set": str(self.manual_set.currentData()),
            }
        elif task == "region_error":
            slow = region_config
            region_error = {
                "frame_step": self.region_frame_step.value(),
            }
        frame_start = None
        frame_end = None
        if task == "fast" and self.fast_custom_range.isChecked():
            frame_start = self.fast_frame_start.value()
            frame_end = self.fast_frame_end.value()
        elif task == "slow" and self.slow_custom_range.isChecked():
            frame_start = self.slow_frame_start.value()
            frame_end = self.slow_frame_end.value()
        fov = self.fov.number_source()
        return build_grrt_job(
            self.defaults,
            data=self.window.data_page.data_dir(),
            grid=self.window.data_page.grid_file(),
            output=self.window.data_page.output_dir(),
            task=task,
            npix=self.npix.value(),
            frequency_ghz=self.frequency.number_source(),
            fov_deg=f"({fov})*180" if isinstance(fov, str) else fov * 180.0,
            electron=str(self.electron.currentData()),
            mdot=self.mdot.number_source(),
            # Plotting tasks are selected centrally on the Post-processing page; the legacy fixed entry is no longer invoked.
            postprocess=False,
            frame_start=frame_start,
            frame_end=frame_end,
            model_extra=self.model_panel.collect() if self.model_panel else None,
            camera_extra=self.camera_panel.collect() if self.camera_panel else None,
            ray=self.ray_panel.collect() if self.ray_panel else None,
            analysis=analysis,
            slow=slow,
            region_error=region_error,
        )

    def _check_ready(self) -> bool:
        problems = self.window.data_page.validate_paths(need_output=True)
        if problems:
            self.banner.show_message("error", "\n".join(problems))
            return False
        return True

    def _validate(self) -> None:
        if not self._check_ready():
            return
        try:
            job = self.build_job()
        except ValueError as error:
            self.banner.show_message("error", str(error))
            return
        ok, message = self.window.validate_job("grrt", job)
        if ok:
            self.banner.show_message(
                "info", f"配置校验通过：{message or '计算程序接受该作业。'}")
        else:
            self.banner.show_message("error", f"配置校验失败：{message}")

    def _run(
        self,
        task_override: str | None = None,
    ) -> None:
        if not self._check_ready():
            return
        try:
            job = self.build_job(task_override)
        except ValueError as error:
            self.banner.show_message("error", str(error))
            return
        task_label = dict((value, label) for label, value in TASK_CHOICES)[
            job["grrt"]["task"]]
        action = "正式计算"
        self.window.run_worker_job(
            title=f"{action} · {task_label}",
            kind="grrt",
            job=job,
            output_dir=self.window.data_page.output_dir(),
        )

    def run_analysis(self) -> None:
        """Run slow-light pre-analysis directly from the top fixed action bar."""
        self._run("analysis")

    def check_current_settings(self) -> None:
        self._validate()

    def run_current_task(self) -> None:
        self._run()
