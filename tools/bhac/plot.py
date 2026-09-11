"""BHAC fluid-plane plots using the established GRMHD figure style."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FormatStrFormatter, MaxNLocator
from scipy.interpolate import griddata

if __package__ and __package__.startswith("tools."):
    from ..lib.save_fig import save_figure
else:
    from lib.save_fig import save_figure

from .quantities import FluidFrame


@dataclass(frozen=True)
class PlotStyle:
    """Font size and line width that scale with the image frame."""

    figsize: tuple[float, float]
    fontsize: int
    linewidth: float


@dataclass(frozen=True)
class QuantityStyle:
    """Color scale, color map, and label for a physical quantity."""

    levels: np.ndarray
    cmap: str
    label: str
    logarithmic: bool
    tick: float


@dataclass(frozen=True)
class PlaneData:
    """Coordinates, physical quantities, and magnetic field components on the selected physical plane."""

    x: np.ndarray
    y: np.ndarray
    quantity: np.ndarray
    bx: np.ndarray
    by: np.ndarray
    sigma: np.ndarray
    be: np.ndarray
    horizon: float


def infer_style(figsize: tuple[float, float], base_size: int = 40) -> PlotStyle:
    """Keep the font size and line width ratio of the old image on different canvas sizes."""
    longest = max(figsize)
    if longest >= 20:
        return PlotStyle(figsize, base_size, 1.0)
    if longest >= 15:
        return PlotStyle(figsize, int(base_size * 0.75), 0.8)
    return PlotStyle(figsize, int(base_size * 0.6), 0.3)


def quantity_style(name: str, plane: str) -> QuantityStyle:
    """Returns the old color palette, color scale, and canonical math labels after migration."""
    if name == "rho":
        limits = (-7.0, 0.0) if plane == "xz" else (-2.0, 1.0)
        return _style(limits, "viridis", r"$\log_{10}\rho$", True, 1.0)
    if name == "rho_cgs":
        return _style((-19.5, -18.5), "viridis", r"$\log_{10}(\rho\,[\mathrm{g\,cm^{-3}}])$", True, 0.5)
    if name == "ne":
        limits = (3.3, 5.3) if plane == "xz" else (4.0, 6.0)
        return _style(limits, "viridis", r"$\log_{10}(n_e\,[\mathrm{cm^{-3}}])$", True, 0.5)
    if name == "Te":
        return _style((9.0, 12.0), "plasma", r"$\log_{10}(T_e\,[\mathrm{K}])$", True, 0.5)
    if name == "sigma":
        limits = (-4.0, 2.0) if plane == "xz" else (-4.0, 1.0)
        return _style(limits, "gist_earth", r"$\log_{10}\sigma$", True, 1.0)
    if name == "beta":
        return _style((-3.0, 3.0), "viridis", r"$\log_{10}\beta$", True, 1.0)
    if name == "vr":
        return _style((-0.5, 0.5), "seismic", r"$v^r$", False, 0.2)
    if name == "omega_b":
        return _style((-0.5, 0.5), "seismic", r"$\Omega_B/\Omega_H$", False, 0.2)
    if name == "eta_b":
        return _style((0.0, 0.5 * np.pi), "Purples", r"$\eta_B$", False, 0.2)
    if name == "bsq":
        return _style((-4.0, 2.0), "hot", r"$\log_{10}b^2$", True, 1.0)
    if name == "btheta_over_b":
        return _style((-1.0, 1.0), "BrBG", r"$B_{\hat\theta}/\sqrt{b^2}$", False, 0.5)
    if name == "f_nth":
        return _style((0.0, 0.5), "magma", r"$n_{\mathrm{nth}}/n_e$", False, 0.1)
    if name == "power":
        return _style((2.0, 10.0), "cool", r"$p$", False, 1.0)
    if name == "gamma_min":
        return _style((0.0, 5.0), "hot", r"$\log_{10}\gamma_{\min}$", True, 1.0)
    raise KeyError(f"No plotting style is defined for BHAC quantity {name!r}")


def plot_plane(
    frame: FluidFrame,
    output_dir: Path,
    quantity: str,
    plane: str,
    *,
    limit: float,
    formats: tuple[str, ...] = ("png",),
    draw_magnetic_field: bool = False,
    draw_jet_boundary: bool = True,
    slice_width: float = 0.1,
    sigma_level: float = 20.0,
    be_level: float = 1.02,
    target_dir: Path | None = None,
) -> list[Path]:
    """Draws a frame of the xz or xy plane."""
    output_dir = Path(output_dir)
    if not output_dir.is_absolute():
        raise ValueError("BHAC plot output path must be absolute.")
    if plane not in {"xz", "xy"}:
        raise ValueError("plane must be 'xz' or 'xy'")
    style = infer_style((20.0, 20.0))
    figure, axis = plt.subplots(figsize=style.figsize, dpi=300)
    data = select_plane(frame, quantity, plane, limit=limit, slice_width=slice_width)
    color = draw_plane(
        axis,
        data,
        quantity,
        plane,
        limit=limit,
        style=style,
        draw_magnetic_field=draw_magnetic_field,
        draw_jet_boundary=draw_jet_boundary,
        sigma_level=sigma_level,
        be_level=be_level,
    )
    axis.set_title(_time_title(frame.time), fontsize=style.fontsize)
    axis.set_xlabel(r"$x\,[r_g]$", fontsize=style.fontsize)
    axis.set_ylabel(r"$z\,[r_g]$" if plane == "xz" else r"$y\,[r_g]$", fontsize=style.fontsize)
    axis.tick_params(labelsize=style.fontsize)
    add_colorbar(figure, axis, color, quantity_style(quantity, plane), style.fontsize)
    paths = save_figure(
        figure,
        (Path(target_dir) if target_dir is not None
         else output_dir / plane) / f"{quantity}_{frame.nt:04d}",
        formats,
        dpi=300,
        pad_inches=0.05,
    )
    plt.close(figure)
    return paths


def plot_two_planes(
    frame: FluidFrame,
    output_dir: Path,
    quantity: str,
    *,
    limit: float,
    formats: tuple[str, ...] = ("png",),
    draw_magnetic_field: bool = False,
    draw_jet_boundary: bool = True,
    slice_width: float = 0.1,
    sigma_level: float = 20.0,
    be_level: float = 1.02,
    target_dir: Path | None = None,
) -> list[Path]:
    """Draws the xz and xy planes in the old one-row-two-column style."""
    output_dir = Path(output_dir)
    if not output_dir.is_absolute():
        raise ValueError("BHAC plot output path must be absolute.")
    style = infer_style((32.0, 16.0))
    figure, axes = plt.subplots(1, 2, figsize=style.figsize, dpi=300)
    figure.subplots_adjust(wspace=0.32)
    for axis, plane in zip(axes, ("xz", "xy")):
        data = select_plane(frame, quantity, plane, limit=limit, slice_width=slice_width)
        color = draw_plane(
            axis,
            data,
            quantity,
            plane,
            limit=limit,
            style=style,
            draw_magnetic_field=draw_magnetic_field,
            draw_jet_boundary=draw_jet_boundary,
            sigma_level=sigma_level,
            be_level=be_level,
        )
        axis.set_title(_time_title(frame.time), fontsize=style.fontsize)
        axis.set_xlabel(r"$x\,[r_g]$", fontsize=style.fontsize)
        axis.set_ylabel(r"$z\,[r_g]$" if plane == "xz" else r"$y\,[r_g]$", fontsize=style.fontsize)
        axis.tick_params(labelsize=style.fontsize)
        add_colorbar(figure, axis, color, quantity_style(quantity, plane), style.fontsize)
    paths = save_figure(
        figure,
        (Path(target_dir) if target_dir is not None
         else output_dir / "xz_xy") / f"{quantity}_{frame.nt:04d}",
        formats,
        dpi=300,
        pad_inches=0.05,
    )
    plt.close(figure)
    return paths


def select_plane(
    frame: FluidFrame,
    quantity: str,
    plane: str,
    *,
    limit: float,
    slice_width: float,
) -> PlaneData:
    """Select a finite thickness plane passing through the black hole from the AMR cell."""
    r = frame.get("r")
    theta = frame.get("theta")
    phi = frame.get("phi")
    radial = (r > frame.horizon) & (r < 1.5 * limit)
    if plane == "xz":
        near_zero = np.abs(np.arctan2(np.sin(phi), np.cos(phi))) <= slice_width
        near_pi = np.abs(np.arctan2(np.sin(phi - np.pi), np.cos(phi - np.pi))) <= slice_width
        mask = radial & (near_zero | near_pi)
        sign = np.where(np.cos(phi[mask]) >= 0.0, 1.0, -1.0)
        x = sign * r[mask] * np.sin(theta[mask])
        y = r[mask] * np.cos(theta[mask])
        bx = sign * (frame.get("Br")[mask] * np.sin(theta[mask]) + frame.get("Btheta")[mask] * np.cos(theta[mask]))
        by = frame.get("Br")[mask] * np.cos(theta[mask]) - frame.get("Btheta")[mask] * np.sin(theta[mask])
    elif plane == "xy":
        mask = radial & (np.abs(theta - 0.5 * np.pi) <= slice_width)
        x = r[mask] * np.cos(phi[mask])
        y = r[mask] * np.sin(phi[mask])
        bx = frame.get("Br")[mask] * np.cos(phi[mask]) - frame.get("Bphi")[mask] * np.sin(phi[mask])
        by = frame.get("Br")[mask] * np.sin(phi[mask]) + frame.get("Bphi")[mask] * np.cos(phi[mask])
    else:
        raise ValueError("plane must be 'xz' or 'xy'")
    if np.count_nonzero(mask) < 3:
        raise ValueError(f"Too few BHAC cells selected for the {plane} plane")
    order = np.lexsort((y, x))
    return PlaneData(
        x=x[order],
        y=y[order],
        quantity=frame.get(quantity)[mask][order],
        bx=bx[order],
        by=by[order],
        sigma=frame.get("sigma")[mask][order],
        be=frame.get("be")[mask][order],
        horizon=frame.horizon,
    )


def draw_plane(
    axis,
    data: PlaneData,
    quantity: str,
    plane: str,
    *,
    limit: float,
    style: PlotStyle,
    draw_magnetic_field: bool,
    draw_jet_boundary: bool,
    sigma_level: float,
    be_level: float,
):
    """Plots the selected plane data to the given coordinate axes."""
    spec = quantity_style(quantity, plane)
    values = np.asarray(data.quantity, dtype=np.float64)
    if spec.logarithmic:
        values = np.log10(np.where(values > 0.0, values, np.nan))
    color = axis.tricontourf(
        data.x,
        data.y,
        np.nan_to_num(values, nan=spec.levels[0]),
        levels=spec.levels,
        cmap=spec.cmap,
        extend="both",
    )
    if plane == "xz" and draw_jet_boundary:
        if np.nanmin(data.sigma) <= sigma_level <= np.nanmax(data.sigma):
            axis.tricontour(data.x, data.y, data.sigma, levels=[sigma_level], colors="darkgreen", linestyles="dashed", linewidths=4)
        if np.nanmin(data.be) <= be_level <= np.nanmax(data.be):
            axis.tricontour(data.x, data.y, data.be, levels=[be_level], colors="darkgreen", linestyles="solid", linewidths=4)
    if draw_magnetic_field:
        X, Y, bx, by = prepare_stream_grid(data.x, data.y, data.bx, data.by)
        axis.streamplot(X, Y, bx, by, color="black", linewidth=style.linewidth, density=5, arrowsize=2, maxlength=1000, integration_direction="both")
    draw_horizon(axis, data.horizon)
    axis.set_xlim(-limit, limit)
    axis.set_ylim(-limit, limit)
    axis.set_aspect("equal", "box")
    axis.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=8))
    axis.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=8))
    return color


def prepare_stream_grid(
    x: np.ndarray,
    y: np.ndarray,
    bx: np.ndarray,
    by: np.ndarray,
    grid_size: int = 300,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Interpolate irregular AMR planar magnetic fields to a regular grid in `streamplot`."""
    x_axis = np.linspace(x.min(), x.max(), grid_size)
    y_axis = np.linspace(y.min(), y.max(), grid_size)
    X, Y = np.meshgrid(x_axis, y_axis)
    bx_grid = griddata((x, y), bx, (X, Y), method="linear")
    by_grid = griddata((x, y), by, (X, Y), method="linear")
    return X, Y, bx_grid, by_grid


def draw_horizon(axis, radius: float) -> None:
    """Draw an old style black event horizon section."""
    x = np.linspace(-radius, radius, 100)
    z = np.sqrt(np.maximum(radius * radius - x * x, 0.0))
    axis.fill_between(x, z, -z, color="black", zorder=10)


def add_colorbar(figure, axis, color, spec: QuantityStyle, fontsize: int) -> None:
    """Added color bars that follow the old plot format."""
    bar = figure.colorbar(color, ax=axis, fraction=0.046, pad=0.06)
    bar.ax.set_ylabel(spec.label, fontsize=fontsize, rotation=90, labelpad=20)
    start = np.ceil(spec.levels[0] / spec.tick) * spec.tick
    end = np.floor(spec.levels[-1] / spec.tick) * spec.tick
    bar.set_ticks(np.arange(start, end + 0.5 * spec.tick, spec.tick))
    bar.formatter = FormatStrFormatter("%.1f" if spec.tick < 1.0 else "%.0f")
    bar.ax.tick_params(labelsize=fontsize)
    bar.update_ticks()


def _style(limits: tuple[float, float], cmap: str, label: str, logarithmic: bool, tick: float) -> QuantityStyle:
    return QuantityStyle(np.linspace(limits[0], limits[1], 100), cmap, label, logarithmic, tick)


def _time_title(time: float) -> str:
    return rf"$t={time:g}\,r_g/c$"
