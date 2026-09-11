"""Performance benchmark page for data parameters, scans, CPU detection, and execution."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..widgets.fields import (
    NoWheelComboBox,
    ParameterGrid,
    TextListField,
    add_row,
    make_int,
)
from ..widgets.panels import ModelPanel
from ..widgets.sections import Banner
from .common import (
    ELECTRON_CHOICES,
    build_benchmark_job,
    load_capabilities,
    load_defaults,
)


class BenchmarkPage(QWidget):
    """Maintain benchmark configurations that are isolated from shared research pages but can be adjusted by data."""

    def __init__(self, window, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.window = window
        self.run_action_text = "运行性能基准"
        try:
            self.defaults = load_defaults("benchmark")
            self.caps = load_capabilities("benchmark")
            load_error = ""
        except Exception as error:  # noqa: BLE001
            self.defaults = None
            self.caps = {}
            load_error = str(error)

        self.banner = Banner()
        bench = self.defaults.get("benchmark", {}) if self.defaults else {}

        self.parameter_group = QButtonGroup(self)
        self.parameter_buttons: dict[str, QPushButton] = {}
        self.parameter_stack = QStackedWidget()
        cards = QHBoxLayout()
        cards.setContentsMargins(0, 0, 0, 0)
        cards.setSpacing(8)
        for index, (key, label) in enumerate((
            ("standard", "数据适配参数"),
            ("scan", "扫描参数"),
        )):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setMinimumHeight(64)
            button.setProperty("card", True)
            self.parameter_group.addButton(button, index)
            self.parameter_buttons[key] = button
            cards.addWidget(button)

        self.parameter_stack.addWidget(self._build_standard_panel())
        self.parameter_stack.addWidget(self._build_scan_panel(bench))
        self.parameter_group.idClicked.connect(
            self._parameter_group_changed)
        self.parameter_buttons["standard"].setChecked(True)
        self._parameter_group_changed(0)

        note = QLabel(
            "数据适配参数只定义当前 GRMHD 模拟和电子模型；扫描参数定义需要"
            "比较的分辨率、物理核心数和帧范围。其余条件由 Benchmark 固定配置定义。")
        note.setProperty("dim", True)
        note.setWordWrap(True)

        cards_widget = QWidget()
        cards_widget.setLayout(cards)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.banner)
        layout.addWidget(note)
        layout.addWidget(cards_widget)
        layout.addWidget(self.parameter_stack)
        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        if load_error:
            self.banner.show_message(
                "error",
                f"无法读取性能基准计算程序的默认配置：{load_error}。"
                "请确认内部计算程序已构建。")

    def _build_standard_panel(self) -> QWidget:
        defaults = self.defaults or {"model": {}}
        model = defaults.get("model", {})

        self.reference_electron = NoWheelComboBox()
        for label, value in ELECTRON_CHOICES:
            self.reference_electron.addItem(label, value)
        electron_index = self.reference_electron.findData(
            model.get("electron", "thermal"))
        if electron_index >= 0:
            self.reference_electron.setCurrentIndex(electron_index)
        electron_box = QGroupBox("电子分布模型")
        electron_form = ParameterGrid(electron_box)
        add_row(electron_form, "电子分布", self.reference_electron)

        self.reference_model_panel = ModelPanel(defaults) \
            if self.defaults else None
        self.reference_camera_panel = None
        self.reference_ray_panel = None
        if self.reference_model_panel is not None:
            if self.reference_model_panel.source is not None:
                self.reference_model_panel.source.hide()
            self.reference_model_panel.numerical.hide()
        self.reference_electron.currentIndexChanged.connect(
            self._reference_electron_changed)
        self._reference_electron_changed()

        self.load_reference = QPushButton("从数据与模型复制 GRMHD 与电子参数")
        self.load_reference.clicked.connect(self._copy_data_profile)
        analysis_note = QLabel(
            "真实源、屏幕、观者、光线积分、数值截断、前置分析和慢光区域"
            "使用 Benchmark 固定配置。缺少匹配前置分析时，计算"
            "程序会在性能计时之外自动生成。")
        analysis_note.setProperty("dim", True)
        analysis_note.setWordWrap(True)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.addWidget(electron_box)
        if self.reference_model_panel is not None:
            layout.addWidget(self.reference_model_panel)
        layout.addWidget(self.load_reference)
        layout.addWidget(analysis_note)
        layout.addStretch(1)
        return page

    def _build_scan_panel(self, bench: dict) -> QWidget:
        self.frame_start = make_int(int(bench.get("frame_start", 2400)),
                                    0, 10_000_000)
        self.frame_end = make_int(int(bench.get("frame_end", 2450)),
                                  0, 10_000_000)
        self.frame_step = make_int(int(bench.get("frame_step", 1)),
                                   1, 1_000_000)
        self.npix_list = TextListField(
            [int(value) for value in bench.get(
                "npix_list", [64, 128, 256, 512])], integer=True)
        self.core_counts = TextListField(
            [int(value) for value in bench.get(
                "core_counts", [1, 2, 4, 8])], integer=True)
        self.repeats = make_int(int(bench.get("repeats", 1)), 1, 1000)
        self.warmup = make_int(int(bench.get("warmup_frames", 1)), 0, 1000)
        self.run_fast = QCheckBox("测量快光")
        self.run_fast.setChecked(bool(bench.get("run_fast", True)))
        self.run_slow = QCheckBox("测量慢光")
        self.run_slow.setChecked(bool(bench.get("run_slow", True)))

        params = QGroupBox("速度与分辨率扫描")
        form = ParameterGrid(params)
        add_row(form, "<i>n</i><sub>0</sub>", self.frame_start,
                "起始帧，包含该帧；必须位于已发现的数据范围内。", unit="帧号")
        add_row(form, "<i>n</i><sub>1</sub>", self.frame_end,
                "结束帧，包含该帧；不得小于 n<sub>0</sub>。", unit="帧号")
        add_row(form, "Δ<i>n</i>", self.frame_step,
                "从 n<sub>0</sub> 开始每隔 Δn 帧取样；未对齐的 n<sub>1</sub>"
                " 不额外加入。", unit="帧")
        add_row(form, "{<i>N</i><sub>pix</sub>}", self.npix_list,
                "逗号分隔整数；写入前去重并排序。", unit="像素/边")
        add_row(form, "{<i>N</i><sub>core</sub>}", self.core_counts,
                "每个物理核心固定使用一个 OpenMP 线程；不得超过所选核心组的可用核心数。",
                unit="核心")
        add_row(form, "$N_{\\mathrm{rep}}$", self.repeats,
                "每次重复都会重新执行被计时的帧流程；网格和光线几何"
                "继续复用。", unit="次")
        add_row(form, "$N_{\\mathrm{w}}$", self.warmup,
                "每组统计中剔除的前导帧数；这些帧仍会实际计算。", unit="帧")
        models_row = QHBoxLayout()
        models_row.addWidget(self.run_fast)
        models_row.addWidget(self.run_slow)
        models_row.addStretch(1)
        models_widget = QWidget()
        models_widget.setLayout(models_row)
        models_row.setContentsMargins(0, 0, 0, 0)
        add_row(form, "传播模型", models_widget)

        cores = QGroupBox("核心组")
        cores_form = ParameterGrid(cores)
        self.core_mode = NoWheelComboBox()
        mode_labels = {
            "physical_cores": "物理核心",
            "performance_cores": "性能核心",
            "efficiency_cores": "能效核心",
        }
        for value in self.caps.get("core_modes", []):
            self.core_mode.addItem(mode_labels.get(value, value), value)
        if self.core_mode.count() == 0:
            for value, label in mode_labels.items():
                self.core_mode.addItem(label, value)
        configured_modes = bench.get("core_modes", ["physical_cores"])
        if configured_modes:
            index = self.core_mode.findData(configured_modes[0])
            if index >= 0:
                self.core_mode.setCurrentIndex(index)
        self.cpu_info = QLabel("尚未检测处理器核心。")
        self.cpu_info.setWordWrap(True)
        self.cpu_button = QPushButton("检测处理器核心")
        self.cpu_button.clicked.connect(self._check_cpu)
        add_row(cores_form, "核心组选择", self.core_mode,
                "每次作业使用一个核心组；可分别运行多次进行比较。")
        add_row(cores_form, "", self.cpu_button)
        cores_form.addRow(self.cpu_info)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.addWidget(params)
        layout.addWidget(cores)
        layout.addStretch(1)
        return page

    def _parameter_group_changed(self, index: int) -> None:
        self.parameter_stack.setCurrentIndex(index)

    def current_parameter_group(self) -> str:
        checked = self.parameter_group.checkedButton()
        for key, button in self.parameter_buttons.items():
            if button is checked:
                return key
        return "standard"

    def select_parameter_group(self, key: str) -> None:
        button = self.parameter_buttons.get(key)
        if button is None:
            return
        button.setChecked(True)
        self._parameter_group_changed(self.parameter_group.id(button))

    def _reference_electron_changed(self, *_args) -> None:
        if self.reference_model_panel is not None:
            self.reference_model_panel.set_electron(
                str(self.reference_electron.currentData()))

    def _copy_data_profile(self) -> None:
        """Explicitly copy GRMHD-data and electron-model fields from shared pages."""
        if self.defaults is None or self.reference_model_panel is None:
            self.banner.show_message("error", "Benchmark 标准默认配置不可用。")
            return
        data = self.window.data_page
        index = self.reference_electron.findData(str(data.electron.currentData()))
        if index >= 0:
            self.reference_electron.setCurrentIndex(index)

        source = data.model_panel
        target = self.reference_model_panel
        for name in (
            "spin", "mdot_sim", "r_low", "r_high", "beta0",
            "p_min", "p_max", "gamma_ratio", "beam_angle", "beam_width",
        ):
            getattr(target, name).setValue(getattr(source, name).value())
        self.banner.show_message(
            "info", "已从“数据与模型”复制 GRMHD 模拟和电子模型参数。")

    def _check_cpu(self) -> None:
        mode = str(self.core_mode.currentData())
        ok, message = self.window.check_cpu(mode)
        label = self.core_mode.currentText()
        self.cpu_info.setText(
            f"{label}：{message}" if ok else f"{label}检测失败：{message}")

    def build_job(self) -> dict:
        if self.defaults is None or self.reference_model_panel is None:
            raise ValueError("性能基准默认配置不可用，无法生成作业。")
        return build_benchmark_job(
            self.defaults,
            data=self.window.data_page.data_dir(),
            grid=self.window.data_page.grid_file(),
            output=self.window.data_page.output_dir(),
            frame_start=self.frame_start.value(),
            frame_end=self.frame_end.value(),
            frame_step=self.frame_step.value(),
            npix_list=[int(value) for value in self.npix_list.parse()],
            core_counts=[int(value) for value in self.core_counts.parse()],
            repeats=self.repeats.value(),
            warmup_frames=self.warmup.value(),
            run_fast=self.run_fast.isChecked(),
            run_slow=self.run_slow.isChecked(),
            electron=str(self.reference_electron.currentData()),
            model_extra=self.reference_model_panel.collect_data_profile(),
            core_modes=[str(self.core_mode.currentData())],
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
        ok, message = self.window.validate_job("benchmark", job)
        if ok:
            self.banner.show_message(
                "info", f"配置校验通过：{message or '计算程序接受该作业。'}")
        else:
            self.banner.show_message("error", f"配置校验失败：{message}")

    def _run(self) -> None:
        if not self._check_ready():
            return
        try:
            job = self.build_job()
        except ValueError as error:
            self.banner.show_message("error", str(error))
            return
        self.window.run_worker_job(
            title="性能基准",
            kind="benchmark",
            job=job,
            output_dir=self.window.data_page.output_dir(),
        )

    def check_current_settings(self) -> None:
        self._validate()

    def run_current_task(self) -> None:
        self._run()

    def set_task_active(self, active: bool) -> None:
        """CPU detection starts an extra worker and is disabled while a production job is running."""
        self.cpu_button.setEnabled(not active)
        self.cpu_button.setToolTip(
            "当前任务结束或取消后才能检查 CPU。" if active else "")
