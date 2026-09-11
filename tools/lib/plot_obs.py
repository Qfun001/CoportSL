"""Read the observations CSV and plot it over time."""

from __future__ import annotations

from pathlib import Path
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .calc_obs import radius_key
from .data import read_rows, read_time_shift, result_from_config
from .save_fig import save_figure


def output_time_shift(output: Path, count: int) -> float:
    """Multi-curve graphs read time shifts from the output directory; alerts but does not interrupt when files are missing."""
    if count <= 1:
        return 0.0
    path = output / "time_alignment.csv"
    if not path.exists():
        warnings.warn(
            f"No time-alignment file found at {path}; plotting curves without time shift.",
            RuntimeWarning,
            stacklevel=2,
        )
        return 0.0
    return read_time_shift(output)


def input_items(inputs: Path | dict[str, Path], csv_name: str, default_label: str) -> list[tuple[str, Path]]:
    """Convert single or multiple result directories into tagged CSV lists."""
    if isinstance(inputs, Path):
        return [(default_label, inputs / csv_name)]
    items = [(label, path / csv_name) for label, path in inputs.items()]
    if not items:
        raise ValueError("At least one observable CSV is required.")
    return items


def shifted_rows(path: Path, shift: float, time_start: float | None, time_end: float | None) -> list[dict[str, str]]:
    """Read the CSV and filter the rows by the shifted time range."""
    rows = read_rows(path)
    if rows and "time_rg_over_c" not in rows[0]:
        result = result_from_config(path.parent.parent)
        for row in rows:
            frame = int(row.get("frame", row.get("nt", "")))
            row["time_rg_over_c"] = str(result.time(frame))
    if time_start is not None:
        rows = [row for row in rows if float(row["time_rg_over_c"]) + shift >= time_start]
    if time_end is not None:
        rows = [row for row in rows if float(row["time_rg_over_c"]) + shift <= time_end]
    if not rows:
        raise ValueError(f"No observable rows remain in the requested time range: {path}")
    return rows


def plot_flux(
    *,
    inputs: Path | dict[str, Path],
    output: Path,
    formats: tuple[str, ...] = ("png",),
    time_start: float | None = None,
    time_end: float | None = None,
) -> list[Path]:
    """Read an existing flux CSV and plot a flux curve."""
    items = input_items(inputs, "flux.csv", "Flux")
    target_shift = output_time_shift(output, len(items))
    figure, axis = plt.subplots(figsize=(8.0, 4.8), dpi=180)
    flux_ranges = {}
    for index, (label, path) in enumerate(items):
        shift = target_shift if index > 0 else 0.0
        rows = shifted_rows(path, shift, time_start, time_end)
        time = np.array([float(row["time_rg_over_c"]) + shift for row in rows])
        flux = np.array([float(row["F_nu_Jy"]) for row in rows])
        axis.plot(time, flux, label=label, linewidth=1.4)
        flux_ranges[label] = (float(np.min(flux)), float(np.max(flux)))

    axis.set_xlabel(r"$t\ [r_{\mathrm{g}}/c]$")
    axis.set_ylabel(r"$F_\nu\ [\mathrm{Jy}]$")
    axis.grid(True, alpha=0.28)
    if len(items) > 1:
        axis.legend()
    figure.tight_layout()
    paths = save_figure(figure, output / "flux", formats)
    plt.close(figure)

    for label, (minimum, maximum) in flux_ranges.items():
        print(f"{label}: F_nu={minimum:.6e} .. {maximum:.6e} Jy")
    for path in paths:
        print(f"Saved flux figure: {path}")
    return paths


def plot_lp(
    *,
    inputs: Path | dict[str, Path],
    output: Path,
    formats: tuple[str, ...] = ("png",),
    time_start: float | None = None,
    time_end: float | None = None,
) -> list[Path]:
    """Read the existing linear polarization CSV and plot it."""
    items = input_items(inputs, "lp.csv", "LP")
    target_shift = output_time_shift(output, len(items))
    figure, axes = plt.subplots(2, 1, figsize=(8.0, 6.0), sharex=True, dpi=180)
    for index, (label, path) in enumerate(items):
        shift = target_shift if index > 0 else 0.0
        rows = shifted_rows(path, shift, time_start, time_end)
        time = np.array([float(row["time_rg_over_c"]) + shift for row in rows])
        local = np.array([float(row["local_linear_fraction"]) for row in rows])
        net = np.array([float(row["net_linear_fraction"]) for row in rows])
        line, = axes[0].plot(time, local, linewidth=1.3, label=label)
        color = line.get_color()
        axes[1].plot(time, net, color=color, linewidth=1.3, label=label)

    axes[0].set_ylabel(r"$\langle |m| \rangle$")
    axes[1].set_ylabel(r"$m_{\mathrm{net}}$")
    axes[1].set_xlabel(r"$t\ [r_{\mathrm{g}}/c]$")
    for axis in axes:
        axis.grid(alpha=0.28)
        if len(items) > 1:
            axis.legend()
    figure.tight_layout()
    paths = save_figure(figure, output / "lp", formats)
    plt.close(figure)
    for path in paths:
        print(f"Saved LP figure: {path}")
    return paths


def plot_beta2(
    *,
    inputs: Path | dict[str, Path],
    output: Path,
    radii_muas: tuple[float | None, ...] = (None,),
    formats: tuple[str, ...] = ("png",),
    time_start: float | None = None,
    time_end: float | None = None,
) -> list[Path]:
    """Read the existing $\beta_2$ CSV and plot the amplitude and phase."""
    items = input_items(inputs, "beta2.csv", "Beta2")
    target_shift = output_time_shift(output, len(items))
    paths = []
    for radius in radii_muas:
        key = radius_key(radius)
        figure, axes = plt.subplots(2, 1, figsize=(8.0, 6.0), sharex=True, dpi=180)
        for index, (label, path) in enumerate(items):
            shift = target_shift if index > 0 else 0.0
            rows = shifted_rows(path, shift, time_start, time_end)
            time = np.array([float(row["time_rg_over_c"]) + shift for row in rows])
            abs_name = "beta2_abs" if radius is None else f"beta2_{key}_abs"
            angle_name = (
                "beta2_angle_deg" if radius is None
                else f"beta2_{key}_angle_deg"
            )
            magnitude = np.array([float(row[abs_name]) for row in rows])
            angle = np.array([float(row[angle_name]) for row in rows])
            line, = axes[0].plot(time, magnitude, linewidth=1.3, label=label)
            color = line.get_color()
            axes[1].plot(time, angle, color=color, linewidth=1.3, label=label)
        axes[0].set_ylabel(r"$|\beta_2|$")
        axes[1].set_ylabel(r"$\angle\beta_2\ [\mathrm{deg}]$")
        axes[1].set_xlabel(r"$t\ [r_{\mathrm{g}}/c]$")
        for axis in axes:
            axis.grid(alpha=0.28)
            if len(items) > 1:
                axis.legend()
        figure.tight_layout()
        stem = "beta2" if radius is None else f"beta2_{key}"
        paths.extend(save_figure(figure, output / stem, formats))
        plt.close(figure)
    for path in paths:
        print(f"Saved beta2 figure: {path}")
    return paths
