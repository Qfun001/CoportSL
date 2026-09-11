"""Flux calibration page: frame range, frequency list, and recommended accretion rate results card."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..widgets.fields import (
    ParameterGrid,
    TextListField,
    add_row,
    make_float,
    make_int,
)
from ..widgets.sections import Banner
from .common import (
    build_flux_job,
    hz_to_ghz,
    load_defaults,
)


class FluxPage(QWidget):
    """Runs the FluxWorker and parses the standard output summary into result cards."""

    def __init__(self, window, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.window = window
        self.run_action_text = "运行 Flux"
        try:
            self.defaults = load_defaults("flux")
            load_error = ""
        except Exception as error:  # noqa: BLE001
            self.defaults = None
            load_error = str(error)

        self.banner = Banner()

        flux = self.defaults.get("flux", {}) if self.defaults else {}
        camera = self.defaults.get("camera", {}) if self.defaults else {}

        self.frame_start = make_int(int(flux.get("frame_start", 1000)),
                                    0, 10_000_000)
        self.frame_end = make_int(int(flux.get("frame_end", 2400)),
                                  0, 10_000_000)
        self.frame_step = make_int(int(flux.get("frame_step", 10)),
                                   1, 1_000_000)
        self.npix = make_int(int(camera.get("npix", 256)), 1, 16384)
        frequencies_hz = camera.get("frequencies_hz", [230e9])
        self.frequencies = TextListField([
            float(value) / 1.0e9 for value in frequencies_hz])
        self.target_flux = make_float(float(flux.get("target_flux_jy", 0.66)),
                                      1.0e-9, 1.0e6, decimals=6)
        shared = window.data_page
        self.fov = shared.fov
        self.electron = shared.electron
        self.mdot = shared.mdot
        self.distance = shared.distance
        self.model_panel = shared.model_panel
        self.camera_panel = shared.camera_panel
        self.ray_panel = shared.ray_panel

        params = QGroupBox("测量参数")
        form = ParameterGrid(params)
        add_row(form, "<i>n</i><sub>0</sub>", self.frame_start,
                "起始帧，包含该帧；必须位于已发现的数据范围内。", unit="帧号")
        add_row(form, "<i>n</i><sub>1</sub>", self.frame_end,
                "结束帧，包含该帧；不得小于 n<sub>0</sub>。", unit="帧号")
        add_row(form, "Δ<i>n</i>", self.frame_step,
                "从 n<sub>0</sub> 开始每隔 Δn 帧取样；未对齐的 n<sub>1</sub>"
                " 不额外加入。", unit="帧")
        add_row(form, "<i>N</i><sub>pix</sub>", self.npix,
                "通量估计通常使用较低分辨率。", unit="像素/边")
        add_row(form, "{ν<sub>i</sub>}", self.frequencies,
                "使用逗号分隔多个观测频率。", unit="GHz")
        add_row(form, "$F_{\\nu,\\mathrm{tgt}}$", self.target_flux,
                "用于约束平均通量密度的目标值。", unit="Jy")
        shared_note = QLabel(
            "本页只设置定标抽样参数；以 π rad 表示的 <i>FOV</i>、电子分布、"
            "Ṁ、<i>D</i> 以及模型/观者/光线参数统一取自“数据与模型”页。")
        shared_note.setProperty("dim", True)
        shared_note.setWordWrap(True)
        form.addRow(shared_note)

        self.results_box = QGroupBox("结果")
        self.results_layout = QVBoxLayout(self.results_box)
        empty = QLabel("运行完成后，这里显示各频率的平均通量与建议吸积率。")
        empty.setProperty("dim", True)
        empty.setWordWrap(True)
        self.results_layout.addWidget(empty)
        self.results_box.setVisible(False)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.banner)
        layout.addWidget(params)
        layout.addWidget(self.results_box)
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
                f"无法读取通量定标程序的默认配置：{load_error}。"
                "请确认内部计算程序已构建。")

    def build_job(self) -> dict:
        if self.defaults is None:
            raise ValueError("通量定标默认配置不可用，无法生成作业。")
        fov = self.fov.number_source()
        return build_flux_job(
            self.defaults,
            data=self.window.data_page.data_dir(),
            grid=self.window.data_page.grid_file(),
            npix=self.npix.value(),
            fov_deg=f"({fov})*180" if isinstance(fov, str) else fov * 180.0,
            frequencies_ghz=self.frequencies.number_sources(),
            electron=str(self.electron.currentData()),
            mdot=self.mdot.number_source(),
            frame_start=self.frame_start.value(),
            frame_end=self.frame_end.value(),
            frame_step=self.frame_step.value(),
            target_flux_jy=self.target_flux.number_source(),
            distance_pc=self.distance.number_source(),
            model_extra=self.model_panel.collect() if self.model_panel else None,
            camera_extra=self.camera_panel.collect() if self.camera_panel else None,
            ray=self.ray_panel.collect() if self.ray_panel else None,
        )

    def _check_ready(self) -> bool:
        problems = self.window.data_page.validate_paths(need_output=False)
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
        ok, message = self.window.validate_job("flux", job)
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
        self.results_box.setVisible(False)
        self.window.run_worker_job(
            title="Flux 定标",
            kind="flux",
            job=job,
            output_dir=None,
            on_success=self._show_results,
        )

    def check_current_settings(self) -> None:
        self._validate()

    def run_current_task(self) -> None:
        self._run()

    # ------------------------------------------------------------- Result Card

    def _show_results(self, full_log: str) -> None:
        from .common import parse_flux_summaries

        summaries = parse_flux_summaries(full_log)
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not summaries:
            note = QLabel("未能从日志解析出 Flux 汇总；请查看任务抽屉中的完整日志。")
            note.setProperty("dim", True)
            note.setWordWrap(True)
            self.results_layout.addWidget(note)
        for summary in summaries:
            self.results_layout.addWidget(self._summary_card(summary))
        self.results_box.setVisible(True)

    def _summary_card(self, summary) -> QWidget:
        from ..widgets.shadow import apply_shadow

        card = QGroupBox(f"ν = {summary.nu_ghz:g} GHz")
        apply_shadow(card, blur=12.0, dy=2.0)
        layout = QVBoxLayout(card)
        text = QLabel(
            f"样本帧数 {summary.frame_count}；"
            f"平均通量 <i>F</i><sub>ν</sub> = "
            f"{summary.mean_flux_jy:.6g} Jy"
            f"（标准差 {summary.std_flux_jy:.3g}，"
            f"范围 {summary.min_flux_jy:.3g} – {summary.max_flux_jy:.3g}）；"
            f"<br>当前 Ṁ = {summary.current_mdot:.6g} "
            f"<i>M</i><sub>☉</sub> yr<sup>−1</sup><br>"
            f"建议 Ṁ（线性）= {summary.suggested_mdot_linear:.6g}；"
            f"建议 Ṁ（平方根）= {summary.suggested_mdot_sqrt:.6g} "
            f"<i>M</i><sub>☉</sub> yr<sup>−1</sup>")
        text.setWordWrap(True)
        layout.addWidget(text)
        buttons = QHBoxLayout()
        linear = QPushButton("使用线性建议值")
        sqrt = QPushButton("使用平方根建议值")
        linear.clicked.connect(
            lambda _checked=False, value=summary.suggested_mdot_linear:
            self._apply_mdot(value))
        sqrt.clicked.connect(
            lambda _checked=False, value=summary.suggested_mdot_sqrt:
            self._apply_mdot(value))
        buttons.addWidget(linear)
        buttons.addWidget(sqrt)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        return card

    def _apply_mdot(self, value: float) -> None:
        self.window.apply_flux_mdot(value)
        self.banner.show_message(
            "warn",
            f"已把建议吸积率 {value:.6g} M☉/年 写入“正式计算”页的 Ṁ。"
            "建议值只是首猜：修改 Ṁ 后请重新运行 Flux 验证。")
