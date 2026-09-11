"""Plot a selected slow-light region's weighted time window and pixel time span."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.axes_grid1 import make_axes_locatable

from .data import analysis_fov_muas, read_key_values, read_rows
from .save_fig import save_figure


def selected_region_keys(values: dict[str, str]) -> list[str]:
    """Read stable region keys from a production slow-light configuration."""
    keys = [key for key in values.get("SlowLight::REGION_KEYS", "").split(";") if key]
    if not keys:
        raise KeyError("Missing SlowLight::REGION_KEYS in slow config.")
    return keys


def combine_histograms(
    analysis: Path,
    region_keys: list[str],
) -> tuple[np.ndarray, np.ndarray]:
    """Outer join and sum multiple single-region sample count histograms with an integer `frame_offset`."""
    combined: dict[int, int] = {}
    for key in region_keys:
        rows = read_rows(
            analysis / "regions" / key / "offset_histogram.csv")
        if not rows:
            raise ValueError(f"No offset histogram rows for region {key}.")
        for row in rows:
            if "count" not in row:
                raise ValueError(
                    f"Offset histogram for {key} uses the obsolete 'weight' "
                    "header; re-run the Analysis with the current implementation.")
            offset = int(row["frame_offset"])
            count = int(row["count"])
            if count < 0:
                raise ValueError(f"Invalid offset count for region {key}.")
            combined[offset] = combined.get(offset, 0) + count
    offsets = np.array(sorted(combined), dtype=np.int64)
    counts = np.array([combined[int(offset)] for offset in offsets])
    if offsets.size == 0 or counts.sum() <= 0:
        raise ValueError("Selected regions have no positive offset count.")
    return offsets, counts


def plot_selected_time_window(
    *,
    result: Path,
    analysis: Path,
    output: Path,
    formats: tuple[str, ...] = ("pdf",),
) -> list[Path]:
    """Plot the selected regions' integer offset weights and exact production window."""
    values = read_key_values(result / "config.txt")
    dt = float(values["Input::DT"])
    left = float(values["SlowLight::LEFT"])
    right = float(values["SlowLight::RIGHT"])
    offsets, counts = combine_histograms(
        analysis, selected_region_keys(values))
    probability = counts / counts.sum()
    centers = offsets.astype(np.float64) * dt + 0.5 * dt

    figure, axis = plt.subplots(figsize=(7.2, 4.5), constrained_layout=True)
    axis.bar(centers, probability, width=dt, color="tab:blue", align="center")
    axis.axvspan(left, right, color="tab:red", alpha=0.16)
    axis.axvline(left, color="tab:red", linestyle="--", linewidth=1.2)
    axis.axvline(right, color="tab:red", linestyle="--", linewidth=1.2)
    axis.set_xlabel(r"$\Delta t\ [r_{\mathrm{g}}/c]$")
    axis.set_ylabel(r"$P_{\rm sam}$")
    axis.grid(alpha=0.25)
    paths = save_figure(figure, output / "time_window", formats, dpi=180)
    plt.close(figure)
    return paths


def plot_result_time_span(
    *,
    result: Path,
    output: Path,
    formats: tuple[str, ...] = ("pdf",),
) -> list[Path]:
    """Plot the selected combined time span in the production slow-light result directory."""
    time_span = np.loadtxt(result / "time_span.csv", delimiter=",")
    time_span = np.ma.masked_invalid(np.flipud(time_span))
    fov_uas = analysis_fov_muas(result / "config.txt")
    half_fov = 0.5 * fov_uas

    figure, axis = plt.subplots(figsize=(7.5, 6.5), constrained_layout=True)
    image = axis.imshow(
        time_span,
        origin="lower",
        cmap="magma",
        extent=(-half_fov, half_fov, -half_fov, half_fov),
        vmin=0.0,
    )
    axis.set_xlabel(r"$x\ [\mu\mathrm{as}]$")
    axis.set_ylabel(r"$y\ [\mu\mathrm{as}]$")
    axis.set_aspect("equal")
    divider = make_axes_locatable(axis)
    colorbar_axis = divider.append_axes("right", size="4%", pad=0.10)
    colorbar = figure.colorbar(image, cax=colorbar_axis)
    colorbar.set_label(r"$\Delta t_{\rm span}\ [r_{\mathrm{g}}/c]$")
    paths = save_figure(figure, output / "time_span", formats, dpi=180)
    plt.close(figure)
    return paths
