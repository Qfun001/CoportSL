"""Post-processing page: Select full results, check plot tasks and run them all from the top."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..widgets.asyncjob import run_async
from ..config import logical_cpu_count
from ..i18n import retranslate_widget_tree
from ..widgets.fields import TextListField, make_float, make_int
from ..widgets.sections import Banner
from .common import ResultRecord, format_electron, hz_to_ghz, scan_results
from tools.lib.paths import MODEL_FIELDS, compare_model_configs


MODEL_FIELD_LABELS = {
    "input_signature": "输入数据签名",
    "Input::NT0": "首帧",
    "Input::NT1": "末帧",
    "Input::T0": "首帧时刻",
    "Input::DT": "数据时间间隔",
    "Config::NPIX": "图像边长",
    "Config::FOV": "视场角",
    "Config::NU": "观测频率",
    "Config::OBS_T": "观者时刻",
    "Config::OBS_R": "观者半径",
    "Config::OBS_TH": "观者极角",
    "Config::OBS_PH": "观者方位角",
    "Config::SPIN": "黑洞自旋",
    "Config::HS": "网格 h_s",
    "Config::ELECTRON": "电子分布",
    "Config::MBH": "黑洞质量",
    "Config::MDOT": "物理吸积率",
    "Config::MDOT_SIM": "模拟吸积率",
    "Config::R_LOW": "R_low",
    "Config::R_HIGH": "R_high",
    "Config::BETA0": "beta0",
    "Config::SIGMA_MAX": "磁化参数上限",
    "Config::THETAE_EMIT": "电子温度下限",
    "Config::NE_EMIT": "电子数密度下限",
    "Config::POL_LIMIT": "偏振转移截断",
    "Config::P_MIN": "幂律指数下限",
    "Config::P_MAX": "幂律指数上限",
    "Config::GAMMA_RATIO": "Lorentz 因子比值",
    "Config::BEAM_ANGLE": "束流角",
    "Config::BEAM_WIDTH": "束流宽度",
    "Config::R_SOURCE": "发射区外边界",
}


class PostprocessPage(QWidget):
    """Organize configurable plotting tasks from result metadata."""

    run_action_text = "运行勾选任务"

    def __init__(self, window, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.window = window
        self.records: list[ResultRecord] = []
        self._scan_job = None

        self.banner = Banner()
        self.root_label = QLabel("")
        self.root_label.setWordWrap(True)
        self.root_label.setProperty("dim", True)
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.refresh)
        self.open_root = QPushButton("打开结果根目录")
        self.open_root.clicked.connect(self._open_root)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["任务", "编号", "状态", "电子模型", "频率 (GHz)",
             "图像边长", "签名", "已生成图件"])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._selection_changed)

        common = QGroupBox("通用参数")
        common_form = QFormLayout(common)
        self.workers = make_int(1, 1, logical_cpu_count())
        self.workers.setFixedWidth(72)
        common_form.addRow("并行进程", self.workers)
        formats = QHBoxLayout()
        self.png = QCheckBox("PNG")
        self.png.setChecked(True)
        self.pdf = QCheckBox("PDF")
        self.pdf.setChecked(True)
        formats.addWidget(self.png)
        formats.addWidget(self.pdf)
        formats.addStretch(1)
        formats_widget = QWidget()
        formats_widget.setLayout(formats)
        formats.setContentsMargins(0, 0, 0, 0)
        common_form.addRow("图件格式", formats_widget)
        common_note = QLabel(
            "并行数和图件格式对所有支持这些参数的勾选任务生效；"
            "任务会按依赖顺序串行执行，避免同时读取同一批大型文件。")
        common_note.setProperty("dim", True)
        common_note.setWordWrap(True)
        common_form.addRow("", common_note)

        self.task_observables = QCheckBox("生成积分观测量及曲线")
        self.task_observables.setChecked(True)
        self.observables_reuse = QCheckBox("字段完整时复用已有 CSV")
        self.observables_reuse.setChecked(True)
        observables = self._task_tab(
            self.task_observables,
            self.observables_reuse,
            note="生成 flux.csv、lp.csv、beta2.csv 及对应曲线；"
                 "复用 CSV 时不会再次读取全部 Stokes 图像。",
        )

        self.task_evpa = QCheckBox("生成逐帧 EVPA 图")
        self.task_evpa_video = QCheckBox("生成 EVPA 视频")
        self.evpa_reuse = QCheckBox("复用已有 EVPA 图件")
        self.evpa_reuse.setChecked(True)
        self.video_fps = make_float(30.0, 0.1, 240.0, decimals=2)
        evpa = QWidget()
        evpa_form = QFormLayout(evpa)
        evpa_form.addRow("", self.task_evpa)
        evpa_form.addRow("", self.task_evpa_video)
        evpa_form.addRow("", self.evpa_reuse)
        evpa_form.addRow("视频帧率", self.video_fps)
        evpa_note = QLabel(
            "视频采用 1920×1080 标准画布，原图等比例缩放并留边，"
            "不会裁剪或拉伸；若尚无 PNG，请同时勾选逐帧 EVPA。")
        evpa_note.setProperty("dim", True)
        evpa_note.setWordWrap(True)
        evpa_form.addRow("", evpa_note)

        self.task_align = QCheckBox("与兼容快光对齐")
        self.task_compare = QCheckBox("绘制快慢光对比曲线")
        self.task_evpa_compare = QCheckBox("绘制指定时刻的快慢光 EVPA 对比")
        self.fast_match_status = QLabel("请选择一个完整慢光结果。")
        self.fast_match_status.setWordWrap(True)
        self.fast_match_status.setProperty("matchStatus", True)
        self.evpa_times = TextListField([10800.0, 11000.0, 11200.0])
        self.evpa_times.edit.setPlaceholderText("例如 10800, 11000, 11200")
        compare = self._task_tab(
            self.task_align,
            self.task_compare,
            self.task_evpa_compare,
            self.fast_match_status,
            QLabel("EVPA 对比时刻（r<sub>g</sub>/c）"),
            self.evpa_times,
            note="只适用于慢光结果；对齐先于比较执行。"
                 "曲线比较需要两者都已有积分观测量 CSV；"
                 "EVPA 对比读取指定物理时刻附近的 Stokes 帧。",
        )

        self.task_benchmark = QCheckBox("绘制性能基准图")
        self.task_scan = QCheckBox("绘制慢光控制变量扫描")
        self.task_diagnostics = QCheckBox("生成任务专属科研图件")
        advanced = self._task_tab(
            self.task_diagnostics,
            self.task_benchmark,
            self.task_scan,
            note="性能图只适用于单个 Benchmark 结果；"
                 "控制变量扫描需要多选至少两个完整慢光结果。",
        )

        self.function_tabs = QTabWidget()
        self.function_tabs.addTab(observables, "积分观测量")
        self.function_tabs.addTab(evpa, "EVPA")
        self.function_tabs.addTab(compare, "快慢光比较")
        self.function_tabs.addTab(advanced, "基准与扫描")

        actions = QGroupBox("勾选任务")
        actions_layout = QVBoxLayout(actions)
        actions_layout.addWidget(common)
        actions_layout.addWidget(self.function_tabs)

        header = QHBoxLayout()
        header.addWidget(QLabel("结果根目录："))
        header.addWidget(self.root_label, 1)
        header.addWidget(self.refresh_button)
        header.addWidget(self.open_root)

        result_page = QWidget()
        result_layout = QVBoxLayout(result_page)
        result_layout.setContentsMargins(0, 4, 0, 0)
        result_layout.addLayout(header)
        result_layout.addWidget(self.table, 1)

        self.selection_summary = QLabel("尚未选择结果。")
        self.selection_summary.setWordWrap(True)
        self.selection_summary.setProperty("dim", True)
        task_container = QWidget()
        task_layout = QVBoxLayout(task_container)
        task_layout.setContentsMargins(0, 4, 0, 0)
        task_layout.addWidget(self.selection_summary)
        task_layout.addWidget(actions)
        task_layout.addStretch(1)
        task_scroll = QScrollArea()
        task_scroll.setWidgetResizable(True)
        task_scroll.setFrameShape(QScrollArea.NoFrame)
        task_scroll.setWidget(task_container)

        self.panel_group = QButtonGroup(self)
        self.panel_buttons: dict[str, QPushButton] = {}
        panel_cards = QHBoxLayout()
        panel_cards.setContentsMargins(0, 0, 0, 0)
        panel_cards.setSpacing(8)
        for index, (key, label) in enumerate((
            ("results", "结果选择"),
            ("tasks", "任务参数"),
        )):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setMinimumHeight(56)
            button.setProperty("card", True)
            self.panel_group.addButton(button, index)
            self.panel_buttons[key] = button
            panel_cards.addWidget(button)
        cards_widget = QWidget()
        cards_widget.setLayout(panel_cards)
        self.panel_stack = QStackedWidget()
        self.panel_stack.addWidget(result_page)
        self.panel_stack.addWidget(task_scroll)
        self.panel_group.idClicked.connect(self.panel_stack.setCurrentIndex)
        self.panel_buttons["results"].setChecked(True)
        self.panel_stack.setCurrentIndex(0)

        layout = QVBoxLayout(self)
        layout.addWidget(self.banner)
        layout.addWidget(cards_widget)
        layout.addWidget(self.panel_stack, 1)
        self._selection_changed()

    @staticmethod
    def _task_tab(
        *controls: QWidget,
        note: str,
    ) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        for control in controls:
            layout.addWidget(control)
        text = QLabel(note)
        text.setProperty("dim", True)
        text.setWordWrap(True)
        layout.addWidget(text)
        layout.addStretch(1)
        return widget

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        if not self.window.data_page.output.text():
            self.root_label.setText("未设置")
            self.table.setRowCount(0)
            self.records = []
            self.banner.show_message(
                "info", "结果根目录尚未设置；运行计算后会自动填充。")
            return
        root = self.window.data_page.output_dir()
        self.root_label.setText(str(root))
        if not root.is_dir():
            self.table.setRowCount(0)
            self.records = []
            self.banner.show_message(
                "info", "结果根目录不存在或尚未设置；运行计算后会自动填充。")
            return
        if self._scan_job is not None and self._scan_job.is_running():
            return
        self.banner.clear()
        self._scan_job = run_async(
            lambda: scan_results(root),
            lambda records: self._scan_done_for_root(root, records),
            lambda message: self.banner.show_message(
                "error", f"扫描结果目录失败：{message}"),
        )

    def _scan_done_for_root(
        self,
        root: Path,
        records: list[ResultRecord],
    ) -> None:
        if root == self.window.data_page.output_dir():
            self._scan_done(records)

    def _scan_done(self, records: list[ResultRecord]) -> None:
        selected_paths = {record.path for record in self.selected_records()}
        self.records = records
        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(records))
        task_labels = {
            "analysis": "前置分析",
            "fast": "快光",
            "slow": "慢光",
            "region_error": "区域误差",
            "benchmark": "性能基准",
        }
        status_labels = {
            "running": "运行中",
            "complete": "已完成",
            "invalid": "完整性失败",
            "failed": "失败",
            "cancelled": "已取消",
        }
        for row, record in enumerate(records):
            try:
                frequency = f"{hz_to_ghz(float(record.fields.get('Config::NU', 'nan'))):g}"
            except (TypeError, ValueError):
                frequency = ""
            values = (
                task_labels.get(record.task, record.task),
                record.name,
                status_labels.get(record.status, record.status or "未知"),
                format_electron(record.fields),
                frequency,
                record.fields.get("Config::NPIX", ""),
                record.signature_short,
                record.plot_summary or "—",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if record.integrity_reason:
                    item.setToolTip(record.integrity_reason)
                self.table.setItem(row, column, item)
                if record.path in selected_paths:
                    item.setSelected(True)
        self.table.resizeColumnsToContents()
        self.table.setUpdatesEnabled(True)
        self.table.blockSignals(False)
        retranslate_widget_tree(self.table)
        self._selection_changed()

    def selected_record(self) -> ResultRecord | None:
        records = self.selected_records()
        return records[0] if len(records) == 1 else None

    def selected_records(self) -> list[ResultRecord]:
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        return [self.records[row] for row in rows
                if 0 <= row < len(self.records)]

    def _selection_changed(self) -> None:
        record = self.selected_record()
        selected = self.selected_records()
        complete = record is not None and record.status == "complete"
        if not selected:
            self.selection_summary.setText("尚未选择结果。")
        elif len(selected) == 1:
            detail = f" · {selected[0].integrity_reason}" \
                if selected[0].integrity_reason else ""
            self.selection_summary.setText(
                f"当前结果：{selected[0].task}/{selected[0].name} · "
                f"状态 {selected[0].status or '未知'}{detail}")
        else:
            self.selection_summary.setText(
                f"当前已选择 {len(selected)} 个结果；多选只适用于支持批量的任务。")
        image = complete and record.task in {"fast", "slow"}
        self.task_observables.setEnabled(image)
        self.task_evpa.setEnabled(image)
        self.task_evpa_video.setEnabled(image)
        reference = self._matching_fast(record) if record is not None else None
        has_fast = reference is not None
        self.task_align.setEnabled(
            complete and record.task == "slow" and has_fast)
        self.task_compare.setEnabled(
            complete and record.task == "slow" and has_fast)
        self.task_evpa_compare.setEnabled(
            complete and record.task == "slow" and has_fast)
        self.task_diagnostics.setEnabled(
            complete and record.task in {"analysis", "slow", "region_error"})
        self.task_benchmark.setEnabled(
            complete and record.task == "benchmark")
        scan_ready = len(selected) >= 2 and all(
            item.task == "slow" and item.status == "complete"
            for item in selected)
        self.task_scan.setEnabled(scan_ready)
        match_message = self._fast_match_message(record, reference)
        self.fast_match_status.setText(match_message)
        for checkbox in (
            self.task_align,
            self.task_compare,
            self.task_evpa_compare,
        ):
            checkbox.setToolTip(match_message)
        for checkbox in (
            self.task_observables,
            self.task_evpa,
            self.task_evpa_video,
            self.task_align,
            self.task_compare,
            self.task_evpa_compare,
            self.task_diagnostics,
            self.task_benchmark,
            self.task_scan,
        ):
            if not checkbox.isEnabled():
                checkbox.setChecked(False)
        if record is not None and not complete:
            reason = f"：{record.integrity_reason}" \
                if record.integrity_reason else ""
            self.banner.show_message(
                "warn", f"{record.name} 不是完整结果，不能执行后处理{reason}。")
        elif record is not None and record.task == "slow" and reference is None:
            self.banner.show_message("warn", match_message)
        elif selected:
            self.banner.clear()

    def _formats(self) -> list[str]:
        values = []
        if self.png.isChecked():
            values.append("png")
        if self.pdf.isChecked():
            values.append("pdf")
        if not values:
            raise ValueError("请至少选择一种图件格式。")
        return values

    def _matching_fast(self, record: ResultRecord) -> ResultRecord | None:
        signature = record.fields.get("model_signature", "")
        exact = [
            item for item in self.records
            if item.task == "fast" and item.status == "complete" and
            signature and item.fields.get("model_signature") == signature
        ]
        if exact:
            return max(exact, key=lambda item: item.index)
        compatible = []
        for item in self.records:
            if item.task != "fast" or item.status != "complete":
                continue
            comparison = compare_model_configs(item.fields, record.fields)
            if comparison.compatible and comparison.approximate_fields:
                compatible.append(item)
        return max(compatible, key=lambda item: item.index) \
            if compatible else None

    @staticmethod
    def _model_differences(
        fast: ResultRecord,
        slow: ResultRecord,
    ) -> list[tuple[str, str, str]]:
        comparison = compare_model_configs(fast.fields, slow.fields)
        return [
            (field, fast.fields.get(field, ""), slow.fields.get(field, ""))
            for field in comparison.different_fields
        ]

    def _fast_match_message(
        self,
        record: ResultRecord | None,
        reference: ResultRecord | None,
    ) -> str:
        if record is None:
            return "快光匹配：请选择一个完整慢光结果。"
        if record.task != "slow":
            return "快光匹配：当前选择不是慢光结果。"
        if record.status != "complete":
            return "快光匹配：慢光结果尚未完整，暂不能匹配。"
        if reference is not None:
            if reference.fields.get("model_signature") == \
                    record.fields.get("model_signature"):
                return f"快光匹配：{reference.path}（模型签名一致）"
            comparison = compare_model_configs(reference.fields, record.fields)
            details = "、".join(
                f"{MODEL_FIELD_LABELS.get(field, field)}"
                f"（快光 {reference.fields.get(field, '')}；"
                f"慢光 {record.fields.get(field, '')}）"
                for field in comparison.approximate_fields
            )
            return (
                f"快光匹配：{reference.path}（输入签名一致，参数容差匹配；"
                f"末位差异：{details}）"
            )

        candidates = [
            item for item in self.records
            if item.task == "fast" and item.status == "complete"
        ]
        if not candidates:
            return (
                "快光匹配：结果根目录中没有完整快光结果。"
                "请先用相同参数运行快光，然后点击刷新。"
            )

        ranked = sorted(
            ((len(self._model_differences(item, record)), item)
             for item in candidates),
            key=lambda value: (value[0], -value[1].index),
        )
        _, nearest = ranked[0]
        differences = self._model_differences(nearest, record)
        if differences:
            details = []
            for field, fast_value, slow_value in differences[:3]:
                label = MODEL_FIELD_LABELS.get(field, field)
                details.append(
                    f"{label}（快光 {fast_value or '未设置'}；"
                    f"慢光 {slow_value or '未设置'}）"
                )
            if len(differences) > 3:
                details.append(f"另有 {len(differences) - 3} 项")
            reason = "、".join(details)
        else:
            reason = "输入数据首帧或网格文件内容不同"
        return (
            f"快光匹配：已扫描到 {len(candidates)} 个完整快光，但没有兼容结果。"
            f"最接近的是 {nearest.path}；差异：{reason}。"
            "请用慢光相同参数和输入数据重跑快光后刷新。"
        )

    def _single_tasks(self, record: ResultRecord) -> list[dict[str, object]]:
        formats = self._formats()
        workers = self.workers.value()
        tasks: list[dict[str, object]] = []
        if self.task_observables.isChecked():
            tasks.append({
                "kind": "observables",
                "label": "积分观测量",
                "job": {
                    "result": str(record.path),
                    "radii_muas": [None, 20.0],
                    "workers": workers,
                    "formats": formats,
                    "reuse_data": self.observables_reuse.isChecked(),
                },
            })
        if self.task_evpa.isChecked():
            tasks.append({
                "kind": "evpa",
                "label": "逐帧 EVPA",
                "job": {
                    "result": str(record.path),
                    "formats": formats,
                    "workers": workers,
                    "reuse": self.evpa_reuse.isChecked(),
                },
            })
        if self.task_evpa_video.isChecked():
            evpa_dir = record.path / "plot" / "evpa"
            has_png = any(evpa_dir.glob("*.png"))
            will_generate_png = (
                self.task_evpa.isChecked() and "png" in formats)
            if not has_png and not will_generate_png:
                raise ValueError("没有可用于视频的 EVPA PNG；请同时勾选逐帧 EVPA。")
            tasks.append({
                "kind": "evpa_video",
                "label": "EVPA 视频",
                "job": {
                    "result": str(record.path),
                    "fps": self.video_fps.value(),
                    "canvas_size": [1920, 1080],
                },
            })
        reference = self._matching_fast(record)
        if self.task_align.isChecked() or self.task_compare.isChecked():
            if reference is None:
                raise ValueError("没有找到输入数据和模型参数兼容的完整快光结果。")
        if self.task_align.isChecked() and reference is not None:
            tasks.append({
                "kind": "align",
                "label": "快慢光对齐",
                "job": {
                    "reference": str(reference.path),
                    "target": str(record.path),
                    "max_lag": 300.0,
                    "min_overlap_fraction": 0.75,
                },
            })
        if self.task_compare.isChecked() and reference is not None:
            tasks.append({
                "kind": "compare",
                "label": "快慢光比较",
                "job": {
                    "reference": str(reference.path),
                    "target": str(record.path),
                    "reference_label": f"快光 {reference.name}",
                    "target_label": f"慢光 {record.name}",
                    "radii_muas": [None, 20.0],
                    "formats": formats,
                },
            })
        if self.task_evpa_compare.isChecked() and reference is not None:
            alignment = record.path / "plot" / "time_alignment.csv"
            if not self.task_align.isChecked() and not alignment.is_file():
                raise ValueError("EVPA 对比需要时间对齐；请同时勾选快慢光对齐。")
            times = [float(value) for value in self.evpa_times.parse()]
            if not times:
                raise ValueError("请至少输入一个 EVPA 对比时刻。")
            tasks.append({
                "kind": "evpa_compare",
                "label": "快慢光 EVPA 对比",
                "job": {
                    "reference": str(reference.path),
                    "target": str(record.path),
                    "reference_label": f"快光 {reference.name}",
                    "target_label": f"慢光 {record.name}",
                    "times": times,
                },
            })
        if self.task_diagnostics.isChecked():
            tasks.append({
                "kind": "result_diagnostics",
                "label": "任务专属科研图件",
                "job": {
                    "result": str(record.path),
                    "formats": formats,
                },
            })
        if self.task_benchmark.isChecked():
            tasks.append({
                "kind": "benchmark_plot",
                "label": "性能基准图",
                "job": {
                    "result": str(record.path),
                    "formats": formats,
                    "memory_unit": "GiB",
                },
            })
        return tasks

    def _scan_task(self, *, prompt: bool) -> tuple[dict[str, object], Path] | None:
        selected = self.selected_records()
        if not self.task_scan.isChecked():
            return None
        if len(selected) < 2:
            raise ValueError("控制变量扫描需要至少两个慢光结果。")
        reference_fast = self._matching_fast(selected[0])
        if reference_fast is None or any(
                self._matching_fast(item) != reference_fast for item in selected):
            raise ValueError("所选慢光结果没有共同的模型签名匹配快光结果。")
        if not prompt:
            return None
        default_values = ", ".join(str(index + 1)
                                   for index in range(len(selected)))
        text, ok = QInputDialog.getText(
            self, "控制变量数值",
            f"按当前选中顺序输入 {len(selected)} 个横轴数值（逗号分隔）：",
            text=default_values)
        if not ok:
            return None
        try:
            values = [float(value.strip()) for value in
                      text.replace("，", ",").split(",") if value.strip()]
        except ValueError as error:
            raise ValueError("控制变量数值无法解析。") from error
        if len(values) != len(selected):
            raise ValueError(
                f"需要 {len(selected)} 个数值，实际得到 {len(values)} 个。")
        time_text, ok = QInputDialog.getText(
            self, "比较时间范围", "输入起始与结束时刻（逗号分隔，单位 r_g/c）：",
            text="10800,11600")
        if not ok:
            return None
        try:
            time_start, time_end = [
                float(value.strip())
                for value in time_text.replace("，", ",").split(",")
            ]
        except (ValueError, TypeError) as error:
            raise ValueError("时间范围应为两个逗号分隔数值。") from error
        output = self.window.data_page.output_dir() / "comparison" / (
            "scan_" + datetime.now().strftime("%Y%m%d-%H%M%S"))
        task = {
            "kind": "error_scan",
            "label": "慢光控制变量扫描",
            "job": {
                "slow_results": [str(item.path) for item in selected],
                "values": values,
                "reference": selected[-1].name,
                "fast_result": str(reference_fast.path),
                "output": str(output),
                "time_start": time_start,
                "time_end": time_end,
                "workers": self.workers.value(),
                "formats": self._formats(),
            },
        }
        return task, output

    def _build_batch(
        self,
        *,
        prompt: bool,
    ) -> tuple[list[dict[str, object]], Path]:
        record = self.selected_record()
        selected = self.selected_records()
        if not selected:
            raise ValueError("请先在结果表中选择一个完整结果。")
        if any(item.status != "complete" for item in selected):
            invalid = next(
                (item for item in selected if item.integrity_reason), None)
            if invalid is not None:
                raise ValueError(
                    f"{invalid.name} 完整性检查失败：{invalid.integrity_reason}")
            raise ValueError("只有状态为 complete 的结果可以执行后处理。")
        tasks = self._single_tasks(record) if record is not None else []
        scan = self._scan_task(prompt=prompt)
        if scan is not None:
            task, output = scan
            tasks.append(task)
            manifest_dir = output
        if record is not None:
            manifest_dir = record.path / "plot"
        else:
            manifest_dir = self.window.data_page.output_dir() / "comparison"
        if not tasks:
            if self.task_scan.isChecked() and not prompt:
                # The input box does not pop up during the checking phase, but the selection relationship has been passed.
                return [], manifest_dir
            raise ValueError("请至少勾选一个需要运行的任务。")
        return tasks, manifest_dir

    def check_current_settings(self) -> None:
        try:
            tasks, _ = self._build_batch(prompt=False)
        except ValueError as error:
            self.banner.show_message("error", str(error))
            return
        count = len(tasks) if tasks else 1
        self.banner.show_message(
            "info", f"当前选择有效，将按顺序执行 {count} 个后处理任务。")

    def run_current_task(self) -> None:
        try:
            tasks, manifest_dir = self._build_batch(prompt=True)
        except ValueError as error:
            self.banner.show_message("error", str(error))
            return
        if not tasks:
            return
        manifest = manifest_dir / "tasks.json"
        labels = "、".join(str(item["label"]) for item in tasks)
        self.window.run_internal_job(
            title=f"后处理 · {labels}",
            kind="task_batch",
            job={"tasks": tasks, "manifest": str(manifest)},
            output_dir=manifest_dir,
            on_success=lambda _log: self.refresh(),
        )

    def _open_root(self) -> None:
        from PySide6.QtGui import QDesktopServices

        root: Path = self.window.data_page.output_dir()
        if root.is_dir():
            QDesktopServices.openUrl(root.resolve().as_uri())
        else:
            self.banner.show_message("warn", "结果根目录不存在，无法打开。")
