"""Read the Stokes image and plot the electric vector position angle (EVPA) short-line plot."""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.colors import LogNorm, Normalize

from .cancel import throw_if_cancelled
from .data import (
    Result,
    find_frames,
    fov_muas,
    frame_bounds,
    load_csv_map,
    stokes_path,
)
from .save_fig import save_figure
from .parallel import process_tasks


def clean_stokes(
    i_map: np.ndarray,
    q_map: np.ndarray,
    u_map: np.ndarray,
    v_map: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Cleans up the amount of polarization in non-finite, negative and no-light pixels."""
    i_map = np.real(np.asarray(i_map, dtype=np.float64))
    q_map = np.real(np.asarray(q_map, dtype=np.float64))
    u_map = np.real(np.asarray(u_map, dtype=np.float64))
    v_map = np.real(np.asarray(v_map, dtype=np.float64))
    bad_i = ~np.isfinite(i_map) | (i_map < 0.0)
    i_map[bad_i] = 0.0
    bad = ~np.isfinite(q_map) | ~np.isfinite(u_map) | ~np.isfinite(v_map) | (i_map <= 0.0)
    q_map[bad] = 0.0
    u_map[bad] = 0.0
    v_map[bad] = 0.0
    return i_map, q_map, u_map, v_map


def load_stokes(input: Path, nt: int, *, flip_u: bool = False) -> tuple[np.ndarray, ...]:
    """Read and clean a full Stokes image."""
    maps = [load_csv_map(
        stokes_path(input, stokes, nt)) for stokes in "IQUV"]
    if flip_u:
        maps[2] = -maps[2]
    return clean_stokes(*maps)


def orient_map(image: np.ndarray, flip_rows: bool) -> np.ndarray:
    """Apply the vertical image orientation required by the plotting convention."""
    return np.flipud(image) if flip_rows else image


def tick_pixels(npix: int, muas: float, result: Result) -> float:
    """Convert the microarcsecond scale length to the number of image pixels."""
    return npix / fov_muas(result) * muas


def make_evpa_segments(
    q_map: np.ndarray,
    u_map: np.ndarray,
    i_map: np.ndarray,
    *,
    vmax: float,
    stride: int,
    line_length: float,
    min_i_fraction: float,
    flip_rows: bool,
    polarization_percentile: float = 95.0,
    polarization_reference: float | None = None,
) -> LineCollection:
    """Generate a collection of EVPA stubs based on Q, U directions and linear polarization intensity."""
    i_show = orient_map(i_map, flip_rows)
    q_show = orient_map(q_map, flip_rows)
    u_show = orient_map(u_map, flip_rows)
    npix = i_show.shape[0]
    coords = np.arange(0, npix, stride)
    if coords[-1] != npix - 1:
        coords = np.append(coords, npix - 1)

    candidates = []
    for y in coords:
        for x in coords:
            if i_show[y, x] <= min_i_fraction * vmax:
                continue
            q = q_show[y, x]
            u = u_show[y, x]
            if not np.isfinite(q) or not np.isfinite(u) or (q == 0.0 and u == 0.0):
                continue
            candidates.append((x, y, float(q), float(u), math.hypot(float(q), float(u))))

    if polarization_reference is not None:
        p_ref = float(polarization_reference)
    elif candidates:
        p_values = np.array([item[4] for item in candidates], dtype=np.float64)
        p_ref = float(np.percentile(p_values, polarization_percentile))
        if not np.isfinite(p_ref) or p_ref <= 0.0:
            p_ref = float(np.max(p_values))
    else:
        p_ref = 1.0

    segments = []
    for x, y, q, u, p_value in candidates:
        angle = 0.5 * math.atan2(float(u), float(q))
        length = line_length * (min(p_value / p_ref, 1.0) if p_ref > 0.0 else 0.0)
        half = 0.5 * length
        dx = half * math.cos(angle)
        dy = -half * math.sin(angle)
        segments.append([(x - dx, y - dy), (x + dx, y + dy)])
    return LineCollection(segments, colors="white", linewidths=0.8, alpha=0.92)


def intensity_norm(vmin: float, vmax: float, log: bool) -> Normalize | LogNorm:
    """Generates a light intensity map color normalized object."""
    if vmax <= vmin:
        raise ValueError("intensity_vmax must be greater than intensity_vmin.")
    if log:
        if vmin <= 0.0:
            raise ValueError("intensity_vmin must be positive when intensity_log is True.")
        return LogNorm(vmin=vmin, vmax=vmax)
    return Normalize(vmin=vmin, vmax=vmax)


def plot_evpa_frame(
    task: tuple[
        Result, Path, int, int, tuple[str, ...], float, float, bool, int, float,
        float, bool, bool, float | None, bool, Path | None,
    ],
) -> list[Path]:
    """Draw single-frame EVPA graphs for serial or multi-process task calls."""
    (
        result, output, nt, first_nt, formats, intensity_vmin, intensity_vmax,
        intensity_log, stride, line_length, min_i_fraction, flip_u, flip_rows,
        scale_bar_uas, reuse, cancel_file,
    ) = task
    throw_if_cancelled(cancel_file)
    paths = [output / f"evpa{nt:04d}.{name.lstrip('.')}" for name in formats]
    if reuse and all(path.exists() for path in paths):
        return paths

    i_map, q_map, u_map, _ = load_stokes(result.path, nt, flip_u=flip_u)
    throw_if_cancelled(cancel_file)
    npix = i_map.shape[0]
    figure, axis = plt.subplots(figsize=(5.4, 5.1), dpi=220)
    image = axis.imshow(
        orient_map(i_map, flip_rows), origin="lower", cmap="inferno",
        norm=intensity_norm(intensity_vmin, intensity_vmax, intensity_log),
    )
    axis.add_collection(make_evpa_segments(
        q_map, u_map, i_map, vmax=intensity_vmax, stride=stride,
        line_length=line_length, min_i_fraction=min_i_fraction, flip_rows=flip_rows,
    ))
    if scale_bar_uas is not None:
        bar = tick_pixels(npix, scale_bar_uas, result)
        x0 = y0 = 0.06 * (npix - 1)
        axis.plot([x0, x0 + bar], [y0, y0], color="white", linewidth=1.0)
        axis.text(x0 + 0.5 * bar, y0, rf"${scale_bar_uas:g}\ \mu as$",
                  color="white", fontsize=8, ha="center", va="bottom")
    axis.set_xlim(0, npix - 1)
    axis.set_ylim(0, npix - 1)
    axis.set_aspect("equal")
    axis.set_xticks([])
    axis.set_yticks([])
    time = result.time(nt, first_nt)
    axis.set_title(rf"$t={time:.1f}\ [r_\mathrm{{g}}/c]$")
    figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04).set_label(r"$I_\nu$")
    figure.tight_layout()
    paths = save_figure(figure, output / f"evpa{nt:04d}", formats)
    plt.close(figure)
    return paths


def plot_evpa(
    *,
    result: Result,
    output: Path,
    nt_start: int | None = None,
    nt_end: int | None = None,
    formats: tuple[str, ...] = ("png",),
    step: int = 1,
    intensity_vmin: float = 0.0,
    intensity_vmax: float = 1.0e-3,
    intensity_log: bool = False,
    stride: int = 32,
    line_length: float = 12.0,
    min_i_fraction: float = 0.02,
    flip_u: bool = True,
    flip_rows: bool = True,
    scale_bar_uas: float | None = 20.0,
    reuse: bool = True,
    workers: int = 1,
    cancel_file: Path | None = None,
) -> list[Path]:
    """EVPA plots are drawn frame by frame, with the complete output already available for reuse as needed."""
    nt_start, nt_end = frame_bounds(result, nt_start, nt_end)
    if nt_start is None or nt_end is None:
        raise ValueError("EVPA plotting requires nt_start and nt_end.")
    if not formats:
        raise ValueError("At least one figure format is required.")
    intensity_norm(intensity_vmin, intensity_vmax, intensity_log)
    output_dir = output / "evpa"
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = (
        (
            result, output_dir, nt, nt_start, formats, intensity_vmin, intensity_vmax,
            intensity_log, stride, line_length, min_i_fraction, flip_u, flip_rows,
            scale_bar_uas, reuse, cancel_file,
        )
        for nt in find_frames(
            result.path,
            nt_start,
            nt_end,
            step=step,
            required="IQUV",
            require_nonempty=True,
        )
    )
    paths = [path for frame_paths in process_tasks(plot_evpa_frame, tasks, workers) for path in frame_paths]
    print(f"Wrote {len(paths)} EVPA figures to {output_dir}")
    return paths
