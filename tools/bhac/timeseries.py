"""Calculate accretion rate and radial flux time-varying curves from BHAC frames."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

if __package__ and __package__.startswith("tools."):
    from ..lib.cancel import throw_if_cancelled
    from ..lib.save_fig import save_figure
else:
    from lib.cancel import throw_if_cancelled
    from lib.save_fig import save_figure

from .plot import infer_style
from .quantities import (
    ModelParameters,
    load_fluid_frame,
    path_for_frame,
    prepare_run,
)


@dataclass(frozen=True)
class HorizonFlux:
    """Conservation flow rate integral over a thin shell of specified radius."""

    frame: int
    time: float
    radius: float
    half_width: float
    mdot: float
    magnetic_flux: float
    dimensionless_flux: float


def shell_flux(frame, *, radius: float, half_width: float) -> HorizonFlux:
    """Average mass flow rate and absolute radial magnetic flux of thin shells along the radial direction.

    The conserved current density is integrated within the finite thickness of the radial logarithmic coordinate, and then divided by the width of the interval,
    Finite volume estimates are obtained for constant radius surface integrals. Mass flow rate is positive within the orientation."""
    if radius <= frame.horizon:
        raise ValueError(
            f"积分半径 {radius:g} 必须大于事件视界 {frame.horizon:g}。")
    if half_width <= 0.0 or radius - half_width <= frame.horizon:
        raise ValueError("薄壳半宽必须为正，且内边界必须位于事件视界之外。")
    r = frame.get("r")
    mask = (r >= radius - half_width) & (r <= radius + half_width)
    if np.count_nonzero(mask) < 8:
        raise ValueError(
            f"半径 {radius:g} 的薄壳只包含 {np.count_nonzero(mask)} 个单元。")
    dx1 = math.log(radius + half_width) - math.log(radius - half_width)
    measure = (
        frame.get("sqrt_neg_g")[mask]
        * frame.coordinate_volume[mask]
        / dx1
    )
    mdot = -float(np.nansum(
        frame.get("rho")[mask] * frame.get("ur")[mask] * measure))
    magnetic_flux = 0.5 * float(np.nansum(
        np.abs(frame.get("Br")[mask]) * measure))
    dimensionless = magnetic_flux / math.sqrt(mdot) \
        if mdot > 0.0 else math.nan
    return HorizonFlux(
        frame=frame.nt,
        time=frame.time,
        radius=radius,
        half_width=half_width,
        mdot=mdot,
        magnetic_flux=magnetic_flux,
        dimensionless_flux=dimensionless,
    )


def calculate_timeseries(
    *,
    input_dir: Path,
    grid_path: Path,
    frames: tuple[int, ...],
    model: ModelParameters,
    radius: float,
    half_width: float,
    cancel_file: Path | None = None,
) -> list[HorizonFlux]:
    """Selected BHAC frames are read sequentially and thin shell integrals are calculated."""
    if not frames:
        raise ValueError("时变曲线至少需要一帧 BHAC 数据。")
    run = prepare_run(input_dir, grid_path)
    values = []
    for index, nt in enumerate(frames, 1):
        throw_if_cancelled(cancel_file)
        frame = load_fluid_frame(run, path_for_frame(run, nt), model)
        throw_if_cancelled(cancel_file)
        values.append(shell_flux(
            frame, radius=radius, half_width=half_width))
        print(
            f"timeseries: {index}/{len(frames)} frame={nt} "
            f"t={frame.time:g} mdot={values[-1].mdot:.6e} "
            f"Phi={values[-1].magnetic_flux:.6e}",
            flush=True,
        )
    return values


def write_timeseries(values: list[HorizonFlux], output: Path) -> Path:
    """Write the thin shell integral CSV."""
    if not values:
        raise ValueError("时变曲线没有数据。")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow((
            "frame",
            "time_rg_over_c",
            "radius_rg",
            "half_width_rg",
            "mdot_sim",
            "magnetic_flux_sim",
            "dimensionless_flux",
        ))
        for value in values:
            writer.writerow((
                value.frame,
                f"{value.time:.17g}",
                f"{value.radius:.17g}",
                f"{value.half_width:.17g}",
                f"{value.mdot:.17g}",
                f"{value.magnetic_flux:.17g}",
                f"{value.dimensionless_flux:.17g}",
            ))
    return output


def plot_timeseries(
    values: list[HorizonFlux],
    output: Path,
    *,
    formats: tuple[str, ...],
) -> list[Path]:
    """Plot mass flow rate, magnetic flux, and dimensionless magnetic flux as a function of time."""
    if not values:
        raise ValueError("时变曲线没有数据。")
    style = infer_style((10.0, 10.0), base_size=20)
    figure, axes = plt.subplots(
        3, 1, figsize=style.figsize, dpi=240, sharex=True)
    time = np.array([value.time for value in values])
    mdot = np.array([value.mdot for value in values])
    magnetic = np.array([value.magnetic_flux for value in values])
    dimensionless = np.array([value.dimensionless_flux for value in values])
    axes[0].plot(time, mdot, linewidth=1.4)
    axes[0].set_ylabel(r"$\dot{M}\ [\mathrm{code\ units}]$")
    axes[1].plot(time, magnetic, linewidth=1.4)
    axes[1].set_ylabel(r"$\Phi_B\ [\mathrm{code\ units}]$")
    axes[2].plot(time, dimensionless, linewidth=1.4)
    axes[2].set_ylabel(r"$\phi_B=\Phi_B/\sqrt{\dot{M}}$")
    axes[2].set_xlabel(r"$t\ [r_g/c]$")
    for axis in axes:
        axis.grid(alpha=0.25)
        axis.tick_params(labelsize=style.fontsize * 0.72)
    radius = values[0].radius
    half_width = values[0].half_width
    figure.suptitle(
        rf"$r={radius:g}\,r_g,\ \Delta r={half_width:g}\,r_g$",
        fontsize=style.fontsize,
    )
    figure.tight_layout()
    paths = save_figure(
        figure, output, formats, dpi=240, pad_inches=0.05)
    plt.close(figure)
    return paths


def write_timeseries_config(
    parameters: dict[str, object],
    output: Path,
) -> Path:
    """Record the time-varying integration parameters in the directory where the graph is located."""
    model = parameters["model"]
    if not isinstance(model, ModelParameters):
        raise TypeError("model must be ModelParameters")
    output.mkdir(parents=True, exist_ok=True)
    path = output / "config.txt"
    lines = [
        "task=timeseries",
        f"input={Path(parameters['input']).as_posix()}",
        f"grid={Path(parameters['grid']).as_posix()}",
        "frames=" + ",".join(
            str(value) for value in tuple(parameters["frames"])),
        f"radius={float(parameters['timeseries_radius']):.17g}",
        "half_width="
        f"{float(parameters['timeseries_half_width']):.17g}",
        "formats=" + ",".join(
            str(value) for value in tuple(parameters["formats"])),
        f"mbh={model.mbh:.17g}",
        f"mdot={model.mdot:.17g}",
        f"mdot_sim={model.mdot_sim:.17g}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def make_timeseries(parameters: dict[str, object]) -> list[Path]:
    """Generate configuration, CSV and time-varying plots."""
    model = parameters["model"]
    if not isinstance(model, ModelParameters):
        raise TypeError("model must be ModelParameters")
    output_root = Path(parameters["output"])
    if not output_root.is_absolute():
        raise ValueError("BHAC output path must be absolute.")
    output = output_root / "timeseries"
    config_path = write_timeseries_config(parameters, output)
    values = calculate_timeseries(
        input_dir=Path(parameters["input"]),
        grid_path=Path(parameters["grid"]),
        frames=tuple(int(value) for value in parameters["frames"]),
        model=model,
        radius=float(parameters["timeseries_radius"]),
        half_width=float(parameters["timeseries_half_width"]),
        cancel_file=parameters.get("cancel_file"),
    )
    csv_path = write_timeseries(values, output / "horizon_flux.csv")
    figures = plot_timeseries(
        values,
        output / "horizon_flux",
        formats=tuple(str(value) for value in parameters["formats"]),
    )
    paths = [config_path, csv_path, *figures]
    for path in paths:
        print(f"timeseries output: {path}")
    return paths
