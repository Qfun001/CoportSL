"""Plot the I/Q/U/V error convergence curve for the named slow-light region approximation."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

from .data import read_key_values, read_rows, write_rows
from .image_error import temporal_mean_std
from .save_fig import save_figure


STOKES = (
    ("I", r"$I$", "tab:blue"),
    ("Q", r"$Q$", "tab:orange"),
    ("U", r"$U$", "tab:green"),
    ("V", r"$V$", "tab:purple"),
)
MODES = (
    ("emission", "Outside emission off", "-"),
    ("all", "Outside all coefficients off", "--"),
)


def configured_region_sets(result: Path) -> tuple[list[str], list[int]]:
    """Read the collection of named regions and representative frames in the configured write order."""
    values = read_key_values(result / "config.txt")
    scanned = values.get("RegionError::SETS", "")
    selected = values.get("RegionError::SET", "")
    prefix = "RegionError::SET."
    definitions = {
        key.removeprefix(prefix): value
        for key, value in values.items()
        if key.startswith(prefix)
    }
    if scanned:
        names = scanned.split(";")
        if any(name not in definitions for name in names):
            raise ValueError(
                "RegionError::SETS does not match RegionError::SET.* definitions.")
    elif selected:
        names = [selected]
    else:
        raise KeyError(
            "Missing RegionError::SETS or RegionError::SET in config.")
    if not names or any(not name for name in names) or len(set(names)) != len(names):
        raise ValueError("RegionError config requires unique named region sets.")
    text = values.get("RegionError::FRAMES", "")
    if not text:
        raise KeyError("Missing RegionError::FRAMES in RegionError config.")
    frames = [int(value) for value in text.split(";")]
    if not frames or len(set(frames)) != len(frames):
        raise ValueError("RegionError config requires unique representative frames.")
    return names, frames


def read_region_error_rows(result: Path, names: list[str]) -> list[dict[str, str]]:
    """Read the error results saved in named collections and directories."""
    files = [result / name / "error.csv" for name in names]
    missing = next((path for path in files if not path.is_file()), None)
    if missing is not None:
        raise FileNotFoundError(
            f"RegionError result is missing scoped CSV: {missing}")
    rows = []
    for name, path in zip(names, files, strict=True):
        for row in read_rows(path):
            if "region_set" in row and row["region_set"] != name:
                raise ValueError(
                    f"RegionError scoped CSV disagrees with directory {name}.")
            rows.append({**row, "region_set": name})
    return rows


def summarize_region_errors(
    result: Path,
) -> tuple[
    list[str],
    list[int],
    dict[tuple[str, str], np.ndarray],
    dict[tuple[str, str], np.ndarray],
]:
    """Verify frame-by-frame errors and summarize representative frame averages and sample standard deviations."""
    names, frames = configured_region_sets(result)
    rows = read_region_error_rows(result, names)
    if not rows:
        raise ValueError("RegionError error.csv contains no rows.")
    expected_names = set(names)
    actual_names = {row["region_set"] for row in rows}
    if actual_names != expected_names:
        raise ValueError(
            "RegionError error.csv region sets do not match config.txt.")
    actual_modes = {row["mode"] for row in rows}
    expected_modes = {mode for mode, _, _ in MODES}
    if actual_modes != expected_modes:
        raise ValueError("RegionError error.csv contains unexpected modes.")

    expected_frames = set(frames)
    means: dict[tuple[str, str], np.ndarray] = {}
    stds: dict[tuple[str, str], np.ndarray] = {}
    for name in names:
        for mode, _, _ in MODES:
            selected = [
                row for row in rows
                if row["region_set"] == name and row["mode"] == mode
            ]
            selected_frames = [int(row["frame"]) for row in selected]
            if (
                len(selected_frames) != len(expected_frames)
                or set(selected_frames) != expected_frames
            ):
                raise ValueError(
                    f"RegionError rows are incomplete for {name}/{mode}.")
            values = np.array([
                [float(row[f"{stokes}_error"]) for stokes, _, _ in STOKES]
                for row in selected
            ])
            if not np.all(np.isfinite(values)) or np.any(values < 0.0):
                raise ValueError(
                    f"RegionError contains invalid values for {name}/{mode}.")
            mean, std = temporal_mean_std(values)
            means[(name, mode)] = mean
            stds[(name, mode)] = std
    return names, frames, means, stds


def summary_rows(
    names: list[str],
    means: dict[tuple[str, str], np.ndarray],
    stds: dict[tuple[str, str], np.ndarray],
    n_frames: int,
) -> list[dict[str, float | int | str]]:
    """Convert RegionError time statistics into a stable summary table."""
    rows = []
    for name in names:
        for mode, _, _ in MODES:
            row: dict[str, float | int | str] = {
                "region_set": name,
                "mode": mode,
                "n_frames": n_frames,
            }
            for index, (stokes, _, _) in enumerate(STOKES):
                row[f"{stokes}_mean"] = float(means[(name, mode)][index])
                row[f"{stokes}_std"] = float(stds[(name, mode)][index])
            rows.append(row)
    return rows


def plot_region_error(
    *,
    result: Path,
    output: Path,
    formats: tuple[str, ...] = ("pdf",),
) -> list[Path]:
    """Generates a single-panel average error convergence plot with representative frame standard deviations."""
    names, frames, means, stds = summarize_region_errors(result)
    summary = summary_rows(names, means, stds, len(frames))
    summary_path = write_rows(output / "error_summary.csv", summary)
    x = np.arange(len(names))
    figure, axis = plt.subplots(figsize=(7.6, 4.8), constrained_layout=True)
    for mode, _, linestyle in MODES:
        for stokes_index, (stokes, _, color) in enumerate(STOKES):
            error = np.array([
                means[(name, mode)][stokes_index]
                for name in names
            ])
            std = np.array([
                stds[(name, mode)][stokes_index]
                for name in names
            ])
            axis.errorbar(
                x,
                error,
                yerr=std,
                color=color,
                linestyle=linestyle,
                marker="o",
                linewidth=1.4,
                capsize=3,
            )

    axis.set_xticks(x, names, rotation=25, ha="right")
    axis.set_xlabel("Named slow-light region")
    axis.set_ylabel(r"$\langle\epsilon_S\rangle_t$")
    axis.grid(alpha=0.25)
    axis.set_ylim(bottom=0.0)
    stokes_handles = [
        Line2D([0], [0], color=color, marker="o", label=label)
        for _, label, color in STOKES
    ]
    mode_handles = [
        Line2D([0], [0], color="0.2", linestyle=linestyle, label=label)
        for _, label, linestyle in MODES
    ]
    stokes_legend = axis.legend(
        handles=stokes_handles,
        loc="upper right",
        ncols=2,
        frameon=False,
        title="Stokes",
    )
    axis.add_artist(stokes_legend)
    axis.legend(
        handles=mode_handles,
        loc="upper center",
        frameon=False,
        title="Approximation",
    )
    paths = save_figure(figure, output / "error", formats, dpi=180)
    plt.close(figure)
    print(f"Wrote {summary_path}")
    return paths
