"""GRMHD distribution, profile, time-varying curve, video and interpolation error tool page."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..config import logical_cpu_count
from ..widgets.fields import (
    NoWheelComboBox,
    ParameterGrid,
    PathRow,
    TextListField,
    add_row,
    make_float,
    make_int,
)
from ..widgets.sections import Banner


QUANTITIES = (
    ("模拟静质量密度 ρ", "rho"),
    ("物理质量密度 ρ", "rho_cgs"),
    ("电子数密度 n_e", "ne"),
    ("电子温度 T_e", "Te"),
    ("磁化率 σ", "sigma"),
    ("等离子体 β", "beta"),
    ("径向速度 vʳ", "vr"),
    ("磁面角速度 Ω_B/Ω_H", "omega_b"),
    ("磁场俯仰角 η_B", "eta_b"),
    ("磁场强度 b²", "bsq"),
    ("极向磁场占比", "btheta_over_b"),
    ("非热电子比例", "f_nth"),
    ("非热电子幂律指数 p", "power"),
    ("最小洛伦兹因子 γ_min", "gamma_min"),
)


def _field_output_dir(output: Path, *fields: str) -> Path:
    return output / "_".join(fields)


class GrmhdPage(QWidget):
    """The current level of tab determines the GRMHD functionality submitted by the top run button."""

    run_action_text = "运行当前 GRMHD 功能"

    def __init__(self, window, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.window = window
        self.banner = Banner()

        common = QGroupBox("通用输出参数")
        common_form = QFormLayout(common)
        formats = QHBoxLayout()
        self.png = QCheckBox("PNG")
        self.png.setChecked(True)
        self.pdf = QCheckBox("PDF")
        formats.addWidget(self.png)
        formats.addWidget(self.pdf)
        formats.addStretch(1)
        formats_widget = QWidget()
        formats_widget.setLayout(formats)
        formats.setContentsMargins(0, 0, 0, 0)
        common_form.addRow("图件格式", formats_widget)
        self.workers = make_int(1, 1, logical_cpu_count())
        common_form.addRow("并行进程", self.workers)
        common_note = QLabel(
            "并行进程用于插值误差；GRMHD 图按帧顺序读取，"
            "避免多个进程同时争用大型 BHAC 文件。")
        common_note.setProperty("dim", True)
        common_note.setWordWrap(True)
        common_form.addRow("", common_note)

        # Distribution map
        self.plot_start, self.plot_end, self.plot_step = \
            self._frame_fields()
        self.quantity = self._quantity_combo()
        self.plot_xz = QCheckBox("XZ 截面图")
        self.plot_xz.setChecked(True)
        self.plot_xy = QCheckBox("XY 截面图")
        self.plot_xz_xy = QCheckBox("XZ + XY 双平面拼图")
        self.limit = make_float(50.0, 0.1, 1.0e6)
        self.slice_width = make_float(0.1, 1.0e-6, 3.14, decimals=6)
        self.jet_boundary = QCheckBox("绘制喷流分界线")
        self.jet_boundary.setChecked(True)
        self.magnetic = QCheckBox("绘制磁力线")
        self.sigma = make_float(20.0, 0.0, 1.0e9)
        self.be = make_float(1.02, -1.0e9, 1.0e9)
        plot_box = QGroupBox("分布图参数")
        plot_form = ParameterGrid(plot_box)
        self._add_frame_rows(
            plot_form, self.plot_start, self.plot_end, self.plot_step)
        add_row(plot_form, "物理量", self.quantity)
        plot_types = QHBoxLayout()
        for checkbox in (self.plot_xz, self.plot_xy, self.plot_xz_xy):
            plot_types.addWidget(checkbox)
        plot_types.addStretch(1)
        plot_types_widget = QWidget()
        plot_types_widget.setLayout(plot_types)
        plot_types.setContentsMargins(0, 0, 0, 0)
        add_row(plot_form, "输出图件", plot_types_widget,
                "三类图件彼此独立，可同时生成。")
        add_row(plot_form, "$L$", self.limit,
                "图像横纵坐标均显示 [-L, L]。", unit="$r_g$")
        add_row(plot_form, "$\\Delta\\theta$", self.slice_width,
                "平面选样的角向半宽；XZ 使用方位角到截面的偏差，XY 使用"
                "极角到赤道面的偏差。", unit="$\\mathrm{rad}$")
        plot_form.addRow("", self.jet_boundary)
        plot_form.addRow("", self.magnetic)
        add_row(plot_form, "$\\sigma_{\\mathrm{jet}}$",
                self.sigma, "XZ 图中标记喷流边界的磁化率等值线值。",
                unit="无量纲")
        add_row(plot_form, "$\\mathrm{Be}_{\\mathrm{jet}}$",
                self.be, "XZ 图中标记喷流边界的 Bernoulli 等值线值。",
                unit="无量纲")

        # Sectional view
        self.profile_start, self.profile_end, self.profile_step = \
            self._frame_fields()
        self.profile_quantity = self._quantity_combo()
        self.profile_radial = QCheckBox("径向分布")
        self.profile_radial.setChecked(True)
        self.profile_theta = QCheckBox("极角分布")
        self.profile_theta.setChecked(True)
        self.profile_r0 = make_float(1.5, 0.0, 1.0e6)
        self.profile_r1 = make_float(50.0, 0.0, 1.0e6)
        self.shell_r0 = make_float(1.5, 0.0, 1.0e6)
        self.shell_r1 = make_float(10.0, 0.0, 1.0e6)
        self.bins = make_int(100, 2, 100000)
        self.smooth = make_int(5, 1, 10001)
        self.profile_log = QCheckBox("纵轴使用对数坐标")
        self.profile_log.setChecked(True)
        profile_box = QGroupBox("剖面图参数")
        profile_form = ParameterGrid(profile_box)
        self._add_frame_rows(
            profile_form,
            self.profile_start,
            self.profile_end,
            self.profile_step,
        )
        add_row(profile_form, "物理量", self.profile_quantity)
        profile_types = QHBoxLayout()
        profile_types.addWidget(self.profile_radial)
        profile_types.addWidget(self.profile_theta)
        profile_types.addStretch(1)
        profile_types_widget = QWidget()
        profile_types_widget.setLayout(profile_types)
        profile_types.setContentsMargins(0, 0, 0, 0)
        add_row(profile_form, "分布方向", profile_types_widget,
                "径向分布对角向积分；极角分布在指定径向壳层内积分。")
        add_row(profile_form, "$r_{\\min}$", self.profile_r0,
                "径向分布下限。", unit="$r_g$")
        add_row(profile_form, "$r_{\\max}$", self.profile_r1,
                "径向分布上限。", unit="$r_g$")
        add_row(profile_form, "$r_{\\theta,\\min}$", self.shell_r0,
                "极角分布采用的径向下限。", unit="$r_g$")
        add_row(profile_form, "$r_{\\theta,\\max}$", self.shell_r1,
                "极角分布采用的径向上限。", unit="$r_g$")
        add_row(profile_form, "$N_{\\mathrm{bin}}$", self.bins, unit="个")
        add_row(profile_form, "$N_{\\mathrm{smooth}}$",
                self.smooth, unit="分箱")
        profile_form.addRow("", self.profile_log)

        # time varying curve
        self.time_start, self.time_end, self.time_step = self._frame_fields()
        self.time_step.setValue(10)
        self.time_radius = make_float(2.5, 1.0, 1.0e6, decimals=6)
        self.time_half_width = make_float(
            0.25, 1.0e-6, 1.0e6, decimals=6)
        time_box = QGroupBox("吸积率与磁通量时变曲线")
        time_form = ParameterGrid(time_box)
        self._add_frame_rows(
            time_form, self.time_start, self.time_end, self.time_step)
        add_row(time_form, "$r_{\\mathrm{int}}$", self.time_radius,
                "执行表面积分的中心半径；必须在事件视界之外。",
                unit="$r_g$")
        add_row(time_form, "$\\Delta r$", self.time_half_width,
                "有限体积薄壳的径向半宽。", unit="$r_g$")
        time_note = QLabel(
            "输出吸积率、磁通量和无量纲磁通量的 CSV 与曲线。")
        time_note.setProperty("dim", True)
        time_note.setWordWrap(True)
        time_form.addRow(time_note)

        # video
        video_box = QGroupBox("视频参数")
        video_form = ParameterGrid(video_box)
        self.video_quantity = self._quantity_combo()
        self.video_plane = NoWheelComboBox()
        self.video_plane.addItem("XZ 平面", "xz")
        self.video_plane.addItem("XY 平面", "xy")
        self.video_plane.addItem("XZ + XY 双平面拼图", "xz_xy")
        add_row(video_form, "已生成物理量", self.video_quantity)
        add_row(video_form, "平面", self.video_plane)
        video_note = QLabel(
            "视频只读取已经生成的 PNG 序列；请先在“分布图”生成相应图件。")
        video_note.setProperty("dim", True)
        video_note.setWordWrap(True)
        video_form.addRow(video_note)

        # interpolation error
        self.dt = TextListField([0.2, 0.5, 1.0, 2.0, 4.0])
        self.interp_action = NoWheelComboBox()
        self.interp_action.addItem("计算并绘图", "calculate")
        self.interp_action.addItem("只重绘已有误差", "plot")
        self.primitive_output = PathRow(
            directory=True, placeholder="原始变量插值误差输出目录")
        primitive_box = QGroupBox("GRMHD 原始变量")
        primitive_form = ParameterGrid(primitive_box)
        add_row(primitive_form, "$\\{\\Delta t\\}$", self.dt,
                "逗号分隔多个待比较间隔。", unit="$r_g/c$")
        add_row(primitive_form, "执行方式", self.interp_action)
        add_row(primitive_form, "输出目录", self.primitive_output)

        self.observation_input = PathRow(
            directory=True, placeholder="包含 I/Q/U/V CSV 的快光结果目录")
        self.observation_output = PathRow(
            directory=True, placeholder="观测图像插值误差输出目录")
        self.observation_action = NoWheelComboBox()
        self.observation_action.addItem("计算并绘图", "calculate")
        self.observation_action.addItem("只重绘已有误差", "plot")
        observation_box = QGroupBox("观测图像")
        observation_form = ParameterGrid(observation_box)
        add_row(observation_form, "快光结果", self.observation_input)
        add_row(observation_form, "执行方式", self.observation_action)
        add_row(observation_form, "输出目录", self.observation_output)
        self.error_tabs = QTabWidget()
        self.error_tabs.addTab(primitive_box, "原始变量")
        self.error_tabs.addTab(observation_box, "观测图像")

        self.function_tabs = QTabWidget()
        self.function_tabs.addTab(plot_box, "分布图")
        self.function_tabs.addTab(profile_box, "剖面图")
        self.function_tabs.addTab(time_box, "时变曲线")
        self.function_tabs.addTab(video_box, "视频")
        self.function_tabs.addTab(self.error_tabs, "插值误差")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.banner)
        layout.addWidget(common)
        layout.addWidget(self.function_tabs)
        layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    @staticmethod
    def _quantity_combo() -> NoWheelComboBox:
        combo = NoWheelComboBox()
        for label, value in QUANTITIES:
            combo.addItem(label, value)
        return combo

    @staticmethod
    def _frame_fields():
        return (
            make_int(1000, 0, 10_000_000),
            make_int(1000, 0, 10_000_000),
            make_int(1, 1, 10_000_000),
        )

    @staticmethod
    def _add_frame_rows(form, start, end, step) -> None:
        add_row(form, "$n_0$", start,
                "起始帧，包含该帧；所选数据文件必须存在。", unit="帧号")
        add_row(form, "$n_1$", end,
                "结束帧，包含该帧；不得小于 n<sub>0</sub>。", unit="帧号")
        add_row(form, "$\\Delta n$", step,
                "实际选择满足 n<sub>0</sub> + k Δn ≤ n<sub>1</sub> 的帧；"
                "未对齐的 n<sub>1</sub> 不额外加入。", unit="帧")

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        output = self.window.data_page.output_dir()
        if not self.primitive_output.text() and str(output):
            self.primitive_output.set_text(
                str(output / "timing" / "b_interp"))
        if not self.observation_output.text() and str(output):
            self.observation_output.set_text(
                str(output / "timing" / "obs_interp"))
        info = getattr(self.window.data_page, "frame_info", None)
        if info is not None and getattr(info, "first", None) is not None:
            first = int(info.first)
            last = int(info.last)
            for start, end in (
                (self.plot_start, self.plot_end),
                (self.profile_start, self.profile_end),
            ):
                if start.value() == 1000 and end.value() == 1000:
                    start.setValue(first)
                    end.setValue(first)
            if self.time_start.value() == 1000 and self.time_end.value() == 1000:
                self.time_start.setValue(first)
                self.time_end.setValue(last)

    def _formats(self) -> list[str]:
        values = []
        if self.png.isChecked():
            values.append("png")
        if self.pdf.isChecked():
            values.append("pdf")
        if not values:
            raise ValueError("请至少选择一种输出格式。")
        return values

    @staticmethod
    def _frames(start, end, step) -> list[int]:
        if start.value() > end.value():
            raise ValueError("帧范围必须满足起始帧不大于结束帧。")
        return list(range(start.value(), end.value() + 1, step.value()))

    def _model(self) -> dict[str, float]:
        panel = self.window.data_page.model_panel
        return {
            "mbh": float(panel.mbh.value()),
            "mdot": float(self.window.data_page.mdot.value()),
            "mdot_sim": float(panel.mdot_sim.value()),
            "r_low": float(panel.r_low.value()),
            "r_high": float(panel.r_high.value()),
            "beta0": float(panel.beta0.value()),
            "p_min": float(panel.p_min.value()),
            "p_max": float(panel.p_max.value()),
            "gamma_ratio": float(panel.gamma_ratio.value()),
        }

    def _common_job(self, *, frames: list[int] | None = None) -> dict:
        problems = self.window.data_page.validate_paths(need_output=True)
        if problems:
            raise ValueError("\n".join(problems))
        job = {
            "input": str(self.window.data_page.data_dir()),
            "grid": str(self.window.data_page.grid_file()),
            "output": str(self.window.data_page.output_dir() / "grmhd"),
            "model": self._model(),
            "formats": self._formats(),
        }
        if frames is not None:
            missing = [
                nt for nt in frames
                if not (self.window.data_page.data_dir() /
                        f"data{nt:04d}.dat").is_file()
            ]
            if missing:
                shown = ", ".join(str(value) for value in missing[:5])
                raise ValueError(f"所选帧不存在：{shown}")
            job["frames"] = frames
        return job

    def _plot_job(self) -> tuple[str, dict, Path]:
        job = self._common_job(frames=self._frames(
            self.plot_start, self.plot_end, self.plot_step))
        plot_types = [
            name for checkbox, name in (
                (self.plot_xz, "xz"),
                (self.plot_xy, "xy"),
                (self.plot_xz_xy, "xz_xy"),
            ) if checkbox.isChecked()
        ]
        if not plot_types:
            raise ValueError("请至少选择一种分布图。")
        job.update({
            "quantities": [str(self.quantity.currentData())],
            "plot_types": plot_types,
            "limit": self.limit.value(),
            "slice_width": self.slice_width.value(),
            "draw_jet_boundary": self.jet_boundary.isChecked(),
            "draw_magnetic_field": self.magnetic.isChecked(),
            "sigma_level": self.sigma.value(),
            "be_level": self.be.value(),
        })
        output = Path(str(job["output"]))
        result = _field_output_dir(
            output, plot_types[0], str(job["quantities"][0])) \
            if len(plot_types) == 1 else output
        return "bhac_plot", job, result

    def _profile_job(self) -> tuple[str, dict, Path]:
        job = self._common_job(frames=self._frames(
            self.profile_start, self.profile_end, self.profile_step))
        types = [
            name for checkbox, name in (
                (self.profile_radial, "radial"),
                (self.profile_theta, "theta"),
            ) if checkbox.isChecked()
        ]
        if not types:
            raise ValueError("请至少选择径向分布或极角分布。")
        if self.profile_r0.value() >= self.profile_r1.value() or \
                self.shell_r0.value() >= self.shell_r1.value():
            raise ValueError("剖面径向范围必须满足下限小于上限。")
        if self.smooth.value() % 2 == 0:
            raise ValueError("平滑窗口必须为奇数。")
        job.update({
            "profile_quantity": str(self.profile_quantity.currentData()),
            "profile_types": types,
            "profile_r": [self.profile_r0.value(), self.profile_r1.value()],
            "profile_shell": [self.shell_r0.value(), self.shell_r1.value()],
            "profile_bins": self.bins.value(),
            "profile_smooth": self.smooth.value(),
            "profile_log": self.profile_log.isChecked(),
        })
        output = Path(str(job["output"]))
        result = _field_output_dir(
            output, f"profile_{types[0]}",
            str(job["profile_quantity"])) \
            if len(types) == 1 else output
        return "bhac_profile", job, result

    def _timeseries_job(self) -> tuple[str, dict, Path]:
        job = self._common_job(frames=self._frames(
            self.time_start, self.time_end, self.time_step))
        if self.time_half_width.value() >= self.time_radius.value():
            raise ValueError("薄壳半宽必须小于积分半径。")
        job.update({
            "timeseries_radius": self.time_radius.value(),
            "timeseries_half_width": self.time_half_width.value(),
        })
        return "bhac_timeseries", job, \
            Path(str(job["output"])) / "timeseries"

    def _video_job(self) -> tuple[str, dict, Path]:
        job = self._common_job()
        job.update({
            "quantity": str(self.video_quantity.currentData()),
            "plane": str(self.video_plane.currentData()),
        })
        output = Path(str(job["output"]))
        image_dir = _field_output_dir(
            output, str(job["plane"]), str(job["quantity"]))
        legacy_dir = output / str(job["plane"])
        if not any(image_dir.glob(f"{job['quantity']}_*.png")) and \
                not any(legacy_dir.glob(f"{job['quantity']}_*.png")):
            raise ValueError("没有找到匹配的 PNG 序列，请先生成分布图。")
        return "bhac_video", job, _field_output_dir(
            output, "movie", str(job["plane"]), str(job["quantity"]))

    def _interp_job(self, *, observation: bool) -> tuple[str, dict, Path]:
        output_row = self.observation_output if observation \
            else self.primitive_output
        output = output_row.path().resolve()
        input_path = self.observation_input.path().resolve() if observation \
            else self.window.data_page.data_dir().resolve()
        if not input_path.is_dir():
            raise ValueError("请选择有效的插值误差输入目录。")
        action = self.observation_action if observation else self.interp_action
        calculate = action.currentData() == "calculate"
        kind = (
            "interp_observation" if observation else "interp_primitive"
        ) if calculate else (
            "plot_observation_error" if observation
            else "plot_primitive_error"
        )
        job = {
            "input": str(input_path),
            "grid": str(self.window.data_page.grid_file().resolve()),
            "output": str(output),
            "dt": [float(value) for value in self.dt.parse()],
            "shells": [[1.5, 5.0], [5.0, 10.0], [10.0, 20.0]],
            "load_workers": 1,
            "workers": self.workers.value(),
            "formats": self._formats(),
        }
        return kind, job, output if calculate else output / "plot"

    def build_current_task(self) -> tuple[str, dict, Path]:
        index = self.function_tabs.currentIndex()
        if index == 0:
            return self._plot_job()
        if index == 1:
            return self._profile_job()
        if index == 2:
            return self._timeseries_job()
        if index == 3:
            return self._video_job()
        return self._interp_job(
            observation=self.error_tabs.currentIndex() == 1)

    def check_current_settings(self) -> None:
        try:
            kind, job, _ = self.build_current_task()
        except ValueError as error:
            self.banner.show_message("error", str(error))
            return
        count = len(job.get("frames", []))
        detail = f"，共 {count} 帧" if count else ""
        self.banner.show_message(
            "info", f"当前设置有效：{kind}{detail}。")

    def run_current_task(self) -> None:
        try:
            kind, job, output = self.build_current_task()
        except ValueError as error:
            self.banner.show_message("error", str(error))
            return
        labels = {
            "bhac_plot": "GRMHD 分布图",
            "bhac_profile": "GRMHD 剖面图",
            "bhac_timeseries": "GRMHD 时变曲线",
            "bhac_video": "GRMHD 视频",
            "interp_primitive": "原始变量插值误差",
            "plot_primitive_error": "原始变量误差绘图",
            "interp_observation": "观测图像插值误差",
            "plot_observation_error": "观测插值误差绘图",
        }
        self.window.run_internal_job(
            title=labels[kind],
            kind=kind,
            job=job,
            output_dir=output,
        )
