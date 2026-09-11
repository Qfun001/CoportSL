"""Shared parameter panels: physics model, camera viewer, and ray integration parameters.

The three panels only edit the whitelist fields that have been accessed by the C++ runtime configuration.
(See MODEL_KEYS / CAMERA_KEYS / RAY_KEYS in desktop/pages/common.py),
Unfilled fields retain the Worker default values and will not be silently discarded."""

from __future__ import annotations

import math
from typing import Any

from PySide6.QtWidgets import (
    QGroupBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from .fields import ParameterGrid, add_row, make_float


class ModelPanel(QWidget):
    """Organize model parameters by physical role and electron-model applicability."""

    def __init__(
        self,
        defaults: dict[str, Any],
        *,
        source_form: ParameterGrid | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        model = defaults["model"]
        self.mbh = make_float(float(model["mbh_msun"]), 1.0, 1.0e12,
                              decimals=2, scientific=True)
        self.spin = make_float(float(model["spin"]), -1.0, 1.0, decimals=6)
        self.mdot_sim = make_float(float(model["mdot_sim"]), 1.0e-12, 1.0e12,
                                   decimals=6, scientific=True)
        self.r_low = make_float(float(model["r_low"]), 0.0, 1.0e9, decimals=6)
        self.r_high = make_float(float(model["r_high"]), 0.0, 1.0e12, decimals=6)
        self.beta0 = make_float(float(model["beta0"]), 1.0e-12, 1.0e12,
                                decimals=6, scientific=True)
        self.sigma_max = make_float(float(model["sigma_max"]), 0.0, 1.0e12,
                                    decimals=6)
        self.r_source = make_float(float(model["r_source_rg"]), 0.0, 1.0e12,
                                   decimals=6)

        self.thetae_emit = make_float(float(model["thetae_emit"]), 0.0, 1.0e6,
                                      decimals=6)
        self.ne_emit = make_float(float(model["ne_emit_cm3"]), 0.0, 1.0e18,
                                  decimals=6, scientific=True)
        self.pol_limit = make_float(float(model["pol_limit"]), 0.0, 1.0,
                                    decimals=6)
        self.p_min = make_float(float(model["p_min"]), 2.000001, 1.0e6, decimals=6)
        self.p_max = make_float(float(model["p_max"]), 2.000001, 1.0e9, decimals=6)
        self.gamma_ratio = make_float(float(model["gamma_ratio"]), 1.000001, 1.0e12,
                                      decimals=6, scientific=True)

        self.beam_angle = make_float(float(model["beam_angle_rad"]),
                                     0.0, 3.141592653589793, decimals=8)
        self.beam_width = make_float(float(model["beam_width"]), 1.0e-12, 1.0e6,
                                     decimals=6)

        source = None
        if source_form is None:
            source = QGroupBox("真实源参数")
            source_form = ParameterGrid(source)
        add_row(source_form, "$M_{\\mathrm{BH}}$", self.mbh,
                "黑洞真实质量。", unit="$M_\\odot$")

        self.source = source
        self.simulation = QGroupBox("GRMHD 模拟参数")
        simulation_form = ParameterGrid(self.simulation)
        add_row(simulation_form, "$a_*$", self.spin,
                "黑洞无量纲自旋，允许范围为 [-1, 1]。", unit="无量纲")
        add_row(simulation_form, "$\\dot{M}_{\\mathrm{sim}}$",
                self.mdot_sim,
                "GRMHD 吸积率归一化，必须与输入数据一致。",
                unit="$M_{\\mathrm{BH}}/T_{\\mathrm{unit}}$")
        grid_note = QLabel(
            "MKSBHAC 网格参数 h_s 直接读取 grid_mks.in 的 hslope，"
            "不在界面重复设置。")
        grid_note.setProperty("dim", True)
        grid_note.setWordWrap(True)
        simulation_form.addRow(grid_note)

        self.temperature = QGroupBox("电子温度模型")
        temperature_form = ParameterGrid(self.temperature)
        add_row(temperature_form, "$R_{\\mathrm{low}}$", self.r_low,
                "<i>R</i>–β 电子温度模型的低磁化区温度比。",
                unit="无量纲")
        add_row(temperature_form, "$R_{\\mathrm{high}}$", self.r_high,
                "<i>R</i>–β 电子温度模型的高磁化区温度比。",
                unit="无量纲")
        add_row(temperature_form, "$\\beta_0$", self.beta0,
                "控制 <i>R</i><sub>low</sub> 与 "
                "<i>R</i><sub>high</sub> 之间的过渡。", unit="无量纲")

        self.numerical = QGroupBox("数值截断与发射区域")
        numerical_form = ParameterGrid(self.numerical)
        add_row(numerical_form, "$\\sigma_{\\max}$", self.sigma_max,
                "超过 σ<sub>max</sub> 的区域不产生辐射。", unit="无量纲")
        add_row(numerical_form, "$r_{\\mathrm{src}}$", self.r_source,
                "辐射源区域的外边界半径；射线越过该半径并向外传播时"
                "终止追迹。", unit="$r_g$")
        add_row(numerical_form, "$\\Theta_{e,\\min}$",
                self.thetae_emit,
                "电子温度低于该阈值时，局域辐射转移系数置零。",
                unit="无量纲")
        add_row(numerical_form, "$n_{e,\\min}$", self.ne_emit,
                "电子数密度低于该阈值时，局域辐射转移系数置零。",
                unit="$\\mathrm{cm}^{-3}$")
        add_row(numerical_form, "$f_{\\mathrm{pol}}^{\\max}$", self.pol_limit,
                "限制偏振发射与吸收系数相对总强度系数的幅度。",
                unit="无量纲")

        self.nonthermal = QGroupBox("非热电子分布")
        nonthermal_form = ParameterGrid(self.nonthermal)
        add_row(nonthermal_form, "$p_{\\min}$", self.p_min,
                "非热电子幂律指数下限。", unit="无量纲")
        add_row(nonthermal_form, "$p_{\\max}$", self.p_max,
                "非热电子幂律指数上限。", unit="无量纲")
        add_row(nonthermal_form,
                "$\\gamma_{\\max}/\\gamma_{\\min}$",
                self.gamma_ratio,
                "电子 Lorentz 因子的比值 "
                "γ<sub>max</sub>/γ<sub>min</sub>。", unit="无量纲")

        self.beam = QGroupBox("束流分布")
        beam_form = ParameterGrid(self.beam)
        add_row(beam_form, "$\\alpha_0$", self.beam_angle,
                "束流中心相对于局域磁场方向的夹角。", unit="rad")
        add_row(beam_form, "$\\sigma_{\\cos\\alpha}$", self.beam_width,
                "以 cos α 为变量的高斯分布标准差，因此无量纲。",
                unit="无量纲")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if source is not None:
            layout.addWidget(source)
        layout.addWidget(self.simulation)
        layout.addWidget(self.temperature)
        layout.addWidget(self.numerical)
        layout.addWidget(self.nonthermal)
        layout.addWidget(self.beam)
        self.note = QLabel(
            "度规 mksbhac 与流体后端 bhac 为当前唯一已接入能力，"
            "在作业中固定写入。")
        self.note.setProperty("dim", True)
        self.note.setWordWrap(True)
        layout.addWidget(self.note)

    def set_electron(self, electron: str) -> None:
        """Hide non-thermal and beam fields when hot electrons (keep Worker defaults in job)."""
        self.nonthermal.setVisible(electron != "thermal")
        self.beam.setVisible(electron in {"beam", "losscone"})

    def collect(self) -> dict[str, Any]:
        """Collect overridden fields for model; hidden fields do not appear in the results."""
        if not self.nonthermal.isHidden() and self.p_min.value() > self.p_max.value():
            raise ValueError("非热电子参数必须满足 p_min 不大于 p_max。")
        values: dict[str, Any] = {
            "mbh_msun": self.mbh.number_source(),
            "spin": self.spin.number_source(),
            "mdot_sim": self.mdot_sim.number_source(),
            "r_low": self.r_low.number_source(),
            "r_high": self.r_high.number_source(),
            "beta0": self.beta0.number_source(),
            "sigma_max": self.sigma_max.number_source(),
            "r_source_rg": self.r_source.number_source(),
            "thetae_emit": self.thetae_emit.number_source(),
            "ne_emit_cm3": self.ne_emit.number_source(),
            "pol_limit": self.pol_limit.number_source(),
        }
        # Page navigation must not alter a job; include fields according to electron-model visibility rules.
        if not self.nonthermal.isHidden():
            values.update({
                "p_min": self.p_min.number_source(),
                "p_max": self.p_max.number_source(),
                "gamma_ratio": self.gamma_ratio.number_source(),
            })
        if not self.beam.isHidden():
            values.update({
                "beam_angle_rad": self.beam_angle.number_source(),
                "beam_width": self.beam_width.number_source(),
            })
        return values

    def collect_data_profile(self) -> dict[str, Any]:
        """Collect simulation and electron-model fields that may change with a GRMHD data set."""
        if not self.nonthermal.isHidden() and self.p_min.value() > self.p_max.value():
            raise ValueError("非热电子参数必须满足 p_min 不大于 p_max。")
        values: dict[str, Any] = {
            "spin": self.spin.number_source(),
            "mdot_sim": self.mdot_sim.number_source(),
            "r_low": self.r_low.number_source(),
            "r_high": self.r_high.number_source(),
            "beta0": self.beta0.number_source(),
        }
        if not self.nonthermal.isHidden():
            values.update({
                "p_min": self.p_min.number_source(),
                "p_max": self.p_max.number_source(),
                "gamma_ratio": self.gamma_ratio.number_source(),
            })
        if not self.beam.isHidden():
            values.update({
                "beam_angle_rad": self.beam_angle.number_source(),
                "beam_width": self.beam_width.number_source(),
            })
        return values


class CameraPanel(QWidget):
    """Viewer coordinate parameters; input units follow the writing convention of C++ default values."""

    def __init__(self, defaults: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        camera = defaults["camera"]
        self.observer_t = make_float(float(camera["observer_t"]), -1.0e12,
                                     1.0e12, decimals=6, scientific=True)
        self.observer_r = make_float(float(camera["observer_r_rg"]), 1.0e-6,
                                     1.0e12, decimals=6)
        self.observer_theta = make_float(
            math.degrees(float(camera["observer_theta_rad"])),
            0.0, 180.0, decimals=8)
        self.observer_phi = make_float(
            float(camera["observer_phi_rad"]), -6.283185307179586,
            6.283185307179586, decimals=8)

        form = ParameterGrid(self)
        form.setContentsMargins(0, 0, 0, 0)
        add_row(form, "$t_{\\mathrm{obs}}$", self.observer_t,
                "成像屏所在事件的观者坐标时刻。", unit="$r_g/c$")
        add_row(form, "$r_{\\mathrm{obs}}$", self.observer_r,
                "观者到黑洞的径向坐标距离。", unit="$r_g$")
        add_row(form, "$\\theta_{\\mathrm{obs}}$", self.observer_theta,
                "从黑洞自旋轴正方向量起，界面以度输入。", unit="°")
        add_row(form, "$\\phi_{\\mathrm{obs}}$", self.observer_phi,
                "绕黑洞自旋轴的方位角，界面以弧度输入。", unit="rad")

    def collect(self) -> dict[str, Any]:
        theta = self.observer_theta.number_source()
        return {
            "observer_t": self.observer_t.number_source(),
            "observer_r_rg": self.observer_r.number_source(),
            "observer_theta_rad": f"({theta})*pi/180"
                if isinstance(theta, str) else math.radians(theta),
            "observer_phi_rad": self.observer_phi.number_source(),
        }


class RayPanel(QWidget):
    """Ray integration tolerance; modification changes model signature and numerical accuracy."""

    def __init__(self, defaults: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        ray = defaults["ray"]
        self.atol = make_float(float(ray["atol"]), 1.0e-18, 1.0,
                               decimals=12, scientific=True)
        self.rtol = make_float(float(ray["rtol"]), 1.0e-18, 1.0,
                               decimals=12, scientific=True)
        self.hmin = make_float(float(ray["hmin"]), 1.0e-18, 1.0,
                               decimals=12, scientific=True)
        self.lmax = make_float(float(ray["lmax"]), 1.0, 1.0e12,
                               decimals=2, scientific=True)
        self.h0 = make_float(float(ray["h0"]), 1.0e-9, 1.0e9, decimals=6)
        self.cell_fraction = make_float(float(ray["cell_fraction"]), 1.0e-12, 1.0,
                                        decimals=6)
        self.horizon_factor = make_float(float(ray["horizon_factor"]), 1.0e-12,
                                         1.0e3, decimals=6)

        form = ParameterGrid(self)
        form.setContentsMargins(0, 0, 0, 0)
        add_row(form, "$\\varepsilon_{\\mathrm{abs}}$", self.atol,
                "测地线积分步长控制中的绝对误差容限；对应内部字段 "
                "atol。")
        add_row(form, "$\\varepsilon_{\\mathrm{rel}}$", self.rtol,
                "测地线积分步长控制中的相对误差容限；对应内部字段 "
                "rtol。",
                unit="无量纲")
        add_row(form, "$h_{\\min}$", self.hmin,
                "积分器允许的最小仿射步长。")
        add_row(form, "$\\lambda_{\\max}$", self.lmax,
                "射线追迹允许的最大累计仿射长度。")
        add_row(form, "$h_0$", self.h0,
                "射线积分的初始仿射步长。")
        add_row(form, "$f_{\\mathrm{cell}}$", self.cell_fraction,
                "单步最大空间推进量相对局域网格尺度的比例。", unit="无量纲")
        add_row(form, "$f_H$", self.horizon_factor,
                "射线进入 f<sub>H</sub> r<sub>H</sub> 内时终止追迹。",
                unit="无量纲")
        note = QLabel("注意：修改光线参数会改变模型签名和数值精度，"
                      "已有结果的匹配状态需要重新检查。")
        note.setProperty("dim", True)
        note.setWordWrap(True)
        form.addRow(note)

    def collect(self) -> dict[str, Any]:
        return {
            "atol": self.atol.number_source(),
            "rtol": self.rtol.number_source(),
            "hmin": self.hmin.number_source(),
            "lmax": self.lmax.number_source(),
            "h0": self.h0.number_source(),
            "cell_fraction": self.cell_fraction.number_source(),
            "horizon_factor": self.horizon_factor.number_source(),
        }
