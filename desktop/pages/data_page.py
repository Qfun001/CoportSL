"""Data & Model page: Centrally manage input paths, imaging settings, and common physical parameters."""

from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..data import grid_candidates, scan_frames
from ..widgets.asyncjob import run_async
from ..widgets.fields import (
    NoWheelComboBox,
    ParameterGrid,
    PathRow,
    add_row,
    make_float,
    make_int,
)
from ..widgets.panels import CameraPanel, ModelPanel, RayPanel
from ..widgets.sections import Banner, CollapsibleSection
from .common import ELECTRON_CHOICES, load_defaults


class DataPage(QWidget):
    """The page entered for the first time; other tasks only reference a shared configuration here."""

    paths_changed = Signal()

    def __init__(self, window, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.window = window
        self._scan_job = None
        self._grid_job = None
        self._scan_generation = 0
        self.frame_info = None

        self.banner = Banner()
        try:
            self.defaults = load_defaults("grrt")
            defaults_error = ""
        except Exception as error:  # noqa: BLE001
            self.defaults = None
            defaults_error = str(error)
        try:
            self.flux_defaults = load_defaults("flux")
        except Exception:  # The Flux page will separately report that the Worker is unavailable
            self.flux_defaults = None

        self.data = PathRow(directory=True,
                            placeholder="选择包含 dataNNNN.dat 的目录")
        self.grid = PathRow(directory=False,
                            placeholder="自动发现 grid_mks.in，或手动选择")
        self.output = PathRow(directory=True,
                              placeholder="默认为数据目录父目录下的 result")

        self.data.changed.connect(self._on_data_changed)
        self.grid.changed.connect(self.paths_changed)
        self.output.changed.connect(self.paths_changed)

        self.frame_summary = QLabel("尚未选择数据目录")
        self.frame_summary.setWordWrap(True)
        self.grid_summary = QLabel("")
        self.grid_summary.setWordWrap(True)
        self.grid_summary.setProperty("dim", True)
        self.output_summary = QLabel("")
        self.output_summary.setWordWrap(True)
        self.output_summary.setProperty("dim", True)

        paths_section = CollapsibleSection("网格与结果路径", expanded=False)
        paths_widget = QWidget()
        form = QFormLayout(paths_widget)
        form.setContentsMargins(0, 0, 0, 0)
        add_row(form, "静态网格文件", self.grid,
                "自动在数据目录及其父目录寻找唯一 grid_mks.in")
        add_row(form, "结果根目录", self.output,
                "必须是可写的绝对目录；支持中文、空格与长路径")
        paths_section.set_content(paths_widget)

        # The first stage of the paper algorithm: unified preparation of data, fixed imaging settings and radiation models.
        camera = self.defaults.get("camera", {}) if self.defaults else {}
        model = self.defaults.get("model", {}) if self.defaults else {}
        flux = self.flux_defaults.get("flux", {}) \
            if self.flux_defaults else {}
        self.electron = NoWheelComboBox()
        for label, value in ELECTRON_CHOICES:
            self.electron.addItem(label, value)
        electron_index = self.electron.findData(
            model.get("electron", "powerlaw"))
        if electron_index >= 0:
            self.electron.setCurrentIndex(electron_index)
        self.npix = make_int(int(camera.get("npix", 512)), 1, 16384)
        self.frequency = make_float(
            float(camera.get("nu_hz", 230e9)) / 1.0e9,
            1.0e-9, 1.0e11, decimals=10, scientific=True)
        self.fov = make_float(
            float(camera.get("fov_rad", math.pi / 64.0)) / math.pi,
            1.0e-12, 2.0, decimals=12, scientific=True)
        self.mdot = make_float(
            float(model.get("mdot_msun_per_year", 2.46e-4)),
            1.0e-12, 1.0e6, decimals=10, scientific=True)
        self.distance = make_float(
            float(flux.get("distance_pc", 16.9e6)),
            1.0, 1.0e12, decimals=2, scientific=True)

        self.source_box = QGroupBox("真实源参数")
        source_form = ParameterGrid(self.source_box)
        add_row(source_form, "$\\dot{M}$", self.mdot,
                "用于把模拟密度归一化到物理单位的吸积率；可由 Flux 定标约束。",
                unit="$M_\\odot\\,\\mathrm{yr}^{-1}$")
        add_row(source_form, "$D$", self.distance,
                "源距离；Flux 定标用它把辐射功率换算为观测通量密度。",
                unit="pc")

        self.telescope_box = QGroupBox("观者处望远镜与成像屏")
        telescope_form = ParameterGrid(self.telescope_box)
        add_row(telescope_form, "$N_{\\mathrm{pix}}$", self.npix,
                "正式图像的单边像素数。", unit="像素/边")
        add_row(telescope_form, "$\\nu$", self.frequency,
                "观测频率；界面按 GHz 输入，作业内部换算为 Hz。", unit="GHz")
        add_row(telescope_form, "$\\mathrm{FOV}$", self.fov,
                "输入值表示视场包含多少个 π rad；"
                "例如 0.015625 π rad 等于 π/64 rad。",
                unit="$\\pi\\,\\mathrm{rad}$")

        self.electron_box = QGroupBox("电子分布模型")
        electron_form = ParameterGrid(self.electron_box)
        add_row(electron_form, "电子分布", self.electron,
                "Flux、前置分析和正式计算共用；性能基准仅在用户显式复制"
                "数据适配参数时更新。")

        self.parameter_sections = QWidget()
        if self.defaults:
            self.model_panel = ModelPanel(
                self.defaults, source_form=source_form)
            self.camera_panel = CameraPanel(self.defaults)
            self.ray_panel = RayPanel(self.defaults)
            self.observer_box = QGroupBox("观者位置")
            observer_layout = QVBoxLayout(self.observer_box)
            observer_layout.addWidget(self.camera_panel)
            self.ray_box = QGroupBox("光线积分数值设置")
            ray_layout = QVBoxLayout(self.ray_box)
            ray_layout.addWidget(self.ray_panel)
            self.defaults_error = None
        else:
            self.model_panel = self.camera_panel = self.ray_panel = None
            self.observer_box = self.ray_box = None
            self.defaults_error = QLabel(
                f"无法读取通用默认配置：{defaults_error}。"
                "请确认内部计算程序已构建。")
            self.defaults_error.setWordWrap(True)
        self.electron.currentIndexChanged.connect(self._electron_changed)
        self._electron_changed()

        self.region_section = QGroupBox("空间分区与慢光分析参数")
        region_section_layout = QVBoxLayout(self.region_section)
        self.region_container = QWidget()
        self.region_layout = QVBoxLayout(self.region_container)
        self.region_layout.setContentsMargins(0, 0, 0, 0)
        region_note = QLabel(
            "空间分区和命名集合由前置分析、慢光成像和区域误差共同使用；"
            "采样间隔与区域容差定义前置分析并进入分析签名，慢光成像和"
            "自动区域误差会匹配或生成相应分析。性能基准维护独立的数据"
            "适配参数，其余条件由 Benchmark 固定配置定义。")
        region_note.setProperty("dim", True)
        region_note.setWordWrap(True)
        self.region_layout.addWidget(region_note)

        analysis_defaults = self.defaults.get("analysis", {}) \
            if self.defaults else {}
        self.analysis_box = QGroupBox("慢光前置分析通用参数")
        analysis_form = ParameterGrid(self.analysis_box)
        self.sample_dt = make_float(
            float(analysis_defaults.get("sample_dt_rg_over_c", 10.0)),
            1.0e-9, 1.0e9, decimals=6)
        add_row(analysis_form, "$\\Delta t$", self.sample_dt,
                "前置分析的快照采样间隔；必须是相邻 GRMHD 帧时间间隔的"
                "正整数倍。", unit="$r_g/c$")
        tolerances = analysis_defaults.get("region_tolerances", {})
        self.tolerance_boxes = {}
        tolerance_labels = {
            "jI": "ε(<i>j</i><sub>I</sub>)",
            "jP": "ε(<i>j</i><sub>P</sub>)",
            "aI": "ε(α<sub>I</sub>)",
            "aP": "ε(α<sub>P</sub>)",
            "rhoV": "ε(ρ<sub>V</sub>)",
            "rhoC": "ε(ρ<sub>C</sub>)",
        }
        for key in ("jI", "jP", "aI", "aP", "rhoV", "rhoC"):
            box = make_float(float(tolerances.get(key, 0.001)),
                             1.0e-12, 1.0, decimals=8, scientific=True)
            self.tolerance_boxes[key] = box
            add_row(analysis_form, tolerance_labels[key], box,
                    "该系数允许由所选慢光区域之外贡献的最大比例；用于生成"
                    "自动区域建议。", unit="无量纲")
        self.region_layout.addWidget(self.analysis_box)
        region_section_layout.addWidget(self.region_container)

        self._build_parameter_navigation()

        workflow = QGroupBox("推荐计算流程")
        workflow_layout = QVBoxLayout(workflow)
        workflow_note = QLabel(
            "① 数据与辐射模型准备　→　② Flux 定标　→　"
            "③ 慢光前置分析　→　④ 正式快光/慢光计算　→　⑤ 结果后处理")
        workflow_note.setProperty("dim", True)
        workflow_note.setWordWrap(True)
        workflow_layout.addWidget(workflow_note)

        hint = QLabel(
            "文件名扫描只做初筛；点击顶部“检查当前设置”后，"
            "会同时检查路径、帧序列和计算程序配置。")
        hint.setProperty("dim", True)
        hint.setWordWrap(True)

        form_widget = QWidget()
        form = QFormLayout(form_widget)
        form.setContentsMargins(0, 0, 0, 0)
        add_row(form, "BHAC 数据目录", self.data)
        form.addRow("帧扫描", self.frame_summary)
        form.addRow("", self.grid_summary)
        form.addRow("", self.output_summary)
        form.addRow("", paths_section)
        form.addRow("", hint)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.banner)
        layout.addWidget(workflow)
        layout.addWidget(form_widget)
        layout.addWidget(self.parameter_sections)
        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _build_parameter_navigation(self) -> None:
        """Use a single row of cards to switch common parameter groups to avoid vertical stacking of all groups."""
        self.parameter_group = QButtonGroup(self)
        self.parameter_buttons: dict[str, QPushButton] = {}
        self.parameter_stack = QStackedWidget()
        cards_layout = QHBoxLayout()
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(8)

        groups: list[tuple[str, str, list[QWidget]]] = [
            ("source", "真实源", [self.source_box]),
            ("telescope", "成像屏", [self.telescope_box]),
        ]
        if self.model_panel is not None:
            groups.extend([
                ("simulation", "GRMHD 模拟", [self.model_panel.simulation]),
                ("electron", "电子模型", [
                    self.electron_box,
                    self.model_panel.temperature,
                    self.model_panel.nonthermal,
                    self.model_panel.beam,
                    self.model_panel.note,
                ]),
                ("numerical", "数值截断", [self.model_panel.numerical]),
                ("observer", "观者位置", [self.observer_box]),
                ("ray", "光线积分", [self.ray_box]),
            ])
        elif self.defaults_error is not None:
            groups.append(("defaults", "配置错误", [self.defaults_error]))
        groups.append(("region", "空间分区", [self.region_section]))

        for index, (key, label, widgets) in enumerate(groups):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setMinimumSize(124, 48)
            button.setProperty("card", True)
            self.parameter_group.addButton(button, index)
            self.parameter_buttons[key] = button
            cards_layout.addWidget(button)

            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(0, 4, 0, 0)
            for widget in widgets:
                page_layout.addWidget(widget)
            page_layout.addStretch(1)
            self.parameter_stack.addWidget(page)

        cards_widget = QWidget()
        cards_widget.setLayout(cards_layout)
        cards_widget.setMinimumWidth(len(groups) * 124 + (len(groups) - 1) * 8)
        cards_scroll = QScrollArea()
        cards_scroll.setWidgetResizable(True)
        cards_scroll.setFrameShape(QScrollArea.NoFrame)
        cards_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        cards_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cards_scroll.setFixedHeight(66)
        cards_scroll.setWidget(cards_widget)

        parameter_layout = QVBoxLayout(self.parameter_sections)
        parameter_layout.setContentsMargins(0, 0, 0, 0)
        parameter_layout.addWidget(cards_scroll)
        parameter_layout.addWidget(self.parameter_stack)
        self.parameter_group.idClicked.connect(
            self._parameter_group_changed)
        first = self.parameter_buttons["source"]
        first.setChecked(True)
        self._parameter_group_changed(self.parameter_group.id(first))

    def _parameter_group_changed(self, index: int) -> None:
        self.parameter_stack.setCurrentIndex(index)

    def current_parameter_group(self) -> str:
        checked = self.parameter_group.checkedButton()
        for key, button in self.parameter_buttons.items():
            if button is checked:
                return key
        return "source"

    def select_parameter_group(self, key: str) -> None:
        button = self.parameter_buttons.get(key)
        if button is None:
            return
        button.setChecked(True)
        self._parameter_group_changed(self.parameter_group.id(button))

    def _electron_changed(self, *_args) -> None:
        if self.model_panel:
            self.model_panel.set_electron(str(self.electron.currentData()))

    def set_mdot(self, value: float) -> None:
        """Receive scaling suggestions from the Flux page for reuse in all subsequent tasks."""
        self.mdot.setValue(float(value))

    def add_region_panel(self, panel: QWidget) -> None:
        """Place the shared production-region editor on the Data and Models page."""
        self.region_layout.insertWidget(
            self.region_layout.indexOf(self.analysis_box), panel)

    def analysis_config(self) -> dict:
        """Returns the analysis configuration shared by pre-analysis and slow-light imaging."""
        return {
            "sample_dt_rg_over_c": self.sample_dt.number_source(),
            "region_tolerances": {
                key: box.number_source()
                for key, box in self.tolerance_boxes.items()
            },
        }

    # --------------------------------------------------------------- Path

    def data_dir(self) -> Path:
        return self.data.path()

    def grid_file(self) -> Path:
        return self.grid.path()

    def output_dir(self) -> Path:
        return self.output.path()

    def set_paths(self, data: str, grid: str, output: str) -> None:
        """Restore the last used path respectively; if one item is empty, it will not affect the other two items."""
        if data:
            self.data.set_text(data)
        if grid:
            self.grid.set_text(grid)
            self.grid_summary.setText(f"已恢复上次网格：{grid}")
        if output:
            self.output.set_text(output)
            self.output_summary.setText(f"已恢复上次结果目录：{output}")
        if data:
            self._on_data_changed()

    # ------------------------------------------------------------------ Scan

    def _on_data_changed(self) -> None:
        self._scan_generation += 1
        generation = self._scan_generation
        directory = self.data.path()
        self.frame_info = None
        if not str(self.data.text()):
            self.frame_summary.setText("尚未选择数据目录")
            self.paths_changed.emit()
            return
        if not directory.is_dir():
            self.frame_summary.setText(f"数据目录不存在：{directory}")
            self.banner.show_message(
                "error", "数据目录不存在或不可访问：请重新选择。")
            self.paths_changed.emit()
            return
        self.banner.clear()
        self.frame_summary.setText("正在扫描帧文件…")
        self._scan_job = run_async(
            lambda: scan_frames(directory),
            lambda scan: self._scan_done(scan, generation, directory),
            lambda message: self._scan_failed(message, generation, directory),
        )

    def _scan_is_current(self, generation: int, directory: Path) -> bool:
        return generation == self._scan_generation and self.data.path() == directory

    def _scan_done(self, scan, generation: int, directory: Path) -> None:
        if not self._scan_is_current(generation, directory):
            return
        self.frame_info = scan
        state = "连续" if scan.continuous else "不连续（缺帧）"
        self.frame_summary.setText(
            f"帧 {scan.first} – {scan.last}，共 {scan.count} 帧，{state}")
        if not scan.continuous:
            self.banner.show_message(
                "warn",
                "帧序列不连续：正式计算要求连续帧，请检查数据目录。")
        self._discover_grid(generation, directory)
        if not self.output.text():
            default_output = (self.data.path().parent / "result").resolve()
            self.output.set_text(str(default_output))
            self.output_summary.setText(f"默认结果目录：{default_output}")
        self.paths_changed.emit()

    def _scan_failed(self, message: str, generation: int, directory: Path) -> None:
        if not self._scan_is_current(generation, directory):
            return
        self.frame_summary.setText(message)
        self.banner.show_message(
            "error",
            f"无法扫描数据目录：{message}。请确认目录中存在 dataNNNN.dat。")
        self.paths_changed.emit()

    def _discover_grid(self, generation: int, directory: Path) -> None:
        self._grid_job = run_async(
            lambda: grid_candidates(directory),
            lambda candidates: self._grid_done(
                candidates, generation, directory),
            lambda message: self._grid_failed(
                message, generation, directory),
        )

    def _grid_failed(self, message: str, generation: int, directory: Path) -> None:
        if self._scan_is_current(generation, directory):
            self.grid_summary.setText(f"网格发现失败：{message}")

    def _grid_done(
        self,
        candidates: list[Path],
        generation: int,
        directory: Path,
    ) -> None:
        if not self._scan_is_current(generation, directory):
            return
        if len(candidates) == 1:
            if not self.grid.text():
                self.grid.set_text(str(candidates[0]))
            self.grid_summary.setText(f"已发现网格：{candidates[0]}")
            self.banner.clear()
        elif not candidates:
            self.grid_summary.setText(
                "未在数据目录及其父目录找到 grid_mks.in，请手动选择。")
            if not self.grid.text():
                self.banner.show_message(
                    "warn", "缺少静态网格文件 grid_mks.in："
                    "请通过“网格与结果路径”选择。")
        else:
            self.grid_summary.setText(
                "发现多个 grid_mks.in 候选，请通过“网格与结果路径”"
                "明确选择一个。")
            self.banner.show_message(
                "warn",
                "找到多个网格候选：请在“网格与结果路径”中"
                "明确选择要使用的文件。")
        self.paths_changed.emit()

    # --------------------------------------------------------------- Verification

    def validate_paths(self, *, need_output: bool) -> list[str]:
        """Returns a list of problems that prevent running; an empty list means running is possible."""
        problems: list[str] = []
        data = self.data.path()
        if not self.data.text() or not data.is_dir():
            problems.append("数据目录无效：请先在“数据”页选择 BHAC 数据目录。")
        else:
            try:
                scan = scan_frames(data)
                if not scan.continuous:
                    problems.append(
                        f"帧序列不连续（{scan.first}–{scan.last}，实际 "
                        f"{scan.count} 帧）：请补全缺帧。")
            except FileNotFoundError as error:
                problems.append(f"帧扫描失败：{error}")
        if not self.grid.text() or not self.grid.path().is_file():
            problems.append("静态网格文件无效：请选择存在的 grid_mks.in。")
        if need_output:
            output_text = self.output.text()
            if not output_text:
                problems.append(
                    "结果根目录为空：请在“数据与模型”页的"
                    "“网格与结果路径”中设置。")
            else:
                output = self.output.path()
                try:
                    output.mkdir(parents=True, exist_ok=True)
                    probe = output / ".coportsl-write-test"
                    probe.write_text("ok", encoding="utf-8")
                    probe.unlink()
                except OSError as error:
                    problems.append(
                        f"结果根目录不可写（{output}）：{error}。"
                        "请更换为可写目录。")
        return problems

    def _inspect(self) -> None:
        problems = self.validate_paths(need_output=True)
        if problems:
            self.banner.show_message("error", "\n".join(problems))
            return
        self.window.inspect_input()

    def check_current_settings(self) -> None:
        """Full input checking is performed by the top action bar."""
        self._inspect()
