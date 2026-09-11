"""EVPA plots comparing two sets of results side by side at the same physical moment."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .evpa import intensity_norm, load_stokes, make_evpa_segments, orient_map, tick_pixels
from .data import Result, read_time_shift


def frame_from_time(time: float, *, t0: float, nt_start: int, dt: float) -> int:
    """Convert the target physics time to the nearest frame number."""
    return int(round(nt_start + (time - t0) / dt))


def plot_evpa_comparison(
    *,
    reference: Result,
    target: Result,
    output: Path,
    times: tuple[float, ...],
    intensity_vmin: float = 0.0,
    intensity_vmax: float = 1.0e-3,
    intensity_log: bool = False,
    stride: int = 32,
    line_length: float = 12.0,
    min_i_fraction: float = 0.02,
    flip_u: bool = True,
    flip_rows: bool = True,
    scale_bar_uas: float | None = 20.0,
    reference_label: str = "fast",
    target_label: str = "slow",
    dpi: int = 220,
) -> Path:
    """Plot multi-moment EVPA of reference results versus target results."""
    if reference.nt0 is None or target.nt0 is None:
        raise ValueError("EVPA comparison requires nt0 for both results.")
    if not times:
        raise ValueError("At least one comparison time is required.")
    norm = intensity_norm(intensity_vmin, intensity_vmax, intensity_log)
    target_shift = read_time_shift(output)
    figure, axes = plt.subplots(
        2,
        len(times),
        figsize=(11.2, 5.6),
        constrained_layout=True,
        squeeze=False,
    )
    image = None
    for col, time in enumerate(times):
        for row, (result, shift) in enumerate(((reference, 0.0), (target, target_shift))):
            nt = frame_from_time(
                time - shift,
                t0=result.t0,
                nt_start=result.nt0,
                dt=result.dt,
            )
            i_map, q_map, u_map, _ = load_stokes(result.path, nt, flip_u=flip_u)
            axis = axes[row, col]
            image = axis.imshow(
                orient_map(i_map, flip_rows), origin="lower", cmap="inferno",
                norm=norm,
            )
            axis.add_collection(make_evpa_segments(
                q_map, u_map, i_map, vmax=intensity_vmax, stride=stride,
                line_length=line_length, min_i_fraction=min_i_fraction, flip_rows=flip_rows,
            ))
            axis.set_xlim(0, i_map.shape[0] - 1)
            axis.set_ylim(0, i_map.shape[0] - 1)
            axis.set_aspect("equal")
            axis.set_xticks([])
            axis.set_yticks([])
        axes[0, col].set_title(rf"$t={time:.0f}\,r_{{\mathrm{{g}}}}/c$", fontsize=9)

    axes[0, 0].set_ylabel(reference_label, fontsize=9)
    axes[1, 0].set_ylabel(target_label, fontsize=9)
    if scale_bar_uas is not None and image is not None:
        npix = image.get_array().shape[0]
        bar = tick_pixels(npix, scale_bar_uas, target)
        x0 = y0 = 0.06 * (npix - 1)
        axes[1, 0].plot([x0, x0 + bar], [y0, y0], color="white", linewidth=1.0)
        axes[1, 0].text(
            x0 + 0.5 * bar, y0, rf"${scale_bar_uas:g}\ \mu as$",
            color="white", fontsize=7, ha="center", va="bottom",
        )
    if image is not None:
        figure.colorbar(image, ax=axes, fraction=0.028, pad=0.01).set_label(r"$I_\nu$")
    path = output / "evpa.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=dpi)
    plt.close(figure)
    print(f"Wrote {path}")
    return path
