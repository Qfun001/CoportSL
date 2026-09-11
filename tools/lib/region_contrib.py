"""Plot the reduced region absolute contribution as a fixed discrete heat map."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm

from .data import read_rows
from .save_fig import save_figure

COEFFICIENTS = (
    ("jI_abs", r"$j_I$"),
    ("jP_abs", r"$j_P$"),
    ("aI_abs", r"$\alpha_I$"),
    ("aP_abs", r"$\alpha_P$"),
    ("rhoV_abs", r"$\rho_V$"),
    ("rhoC_abs", r"$\rho_C$"),
)


def mean_region_fractions(input: Path) -> tuple[list[str], np.ndarray]:
    """The absolute contributions of the six categories are normalized frame by frame, and then the effective frames are temporally averaged."""
    index_rows = read_rows(input / "regions" / "index.csv")
    if not index_rows:
        raise ValueError("regions/index.csv contains no regions.")
    keys = [row["key"] for row in index_rows]
    region_values: list[dict[int, dict[str, float]]] = []
    all_frames: set[int] = set()
    for key in keys:
        rows = read_rows(input / "regions" / key / "contribution.csv")
        values = {
            int(row["frame"]): {
                name: float(row[name])
                for name, _ in COEFFICIENTS
            }
            for row in rows
        }
        if not values:
            raise ValueError(f"No contribution rows found for {key}.")
        all_frames.update(values)
        region_values.append(values)

    if any(set(values) != all_frames for values in region_values):
        raise ValueError("Region contribution files do not contain the same frames.")
    result = np.zeros((len(COEFFICIENTS), len(keys)), dtype=np.float64)
    counts = np.zeros(len(COEFFICIENTS), dtype=np.int64)
    for frame in sorted(all_frames):
        for coefficient, (name, _) in enumerate(COEFFICIENTS):
            absolute = np.array([
                values.get(frame, {}).get(name, 0.0)
                for values in region_values
            ])
            if not np.all(np.isfinite(absolute)) or np.any(absolute < 0.0):
                raise ValueError(
                    f"Invalid {name} contribution at frame {frame}.")
            total = float(np.sum(absolute))
            if total <= 0.0:
                continue
            result[coefficient] += absolute / total
            counts[coefficient] += 1
    for coefficient, count in enumerate(counts):
        if count:
            result[coefficient] /= count
    active = counts > 0
    if not np.any(active):
        raise ValueError("No active regional coefficients were found.")
    if not np.allclose(
        np.sum(result[active], axis=1), 1.0, rtol=0.0, atol=1.0e-10
    ):
        raise ValueError("Time-mean regional fractions do not sum to one.")
    return keys, result


def plot_region_contribution(
    *,
    input: Path,
    output: Path,
    formats: tuple[str, ...] = ("pdf",),
) -> list[Path]:
    """Generate a $6\times N_{\rm region}$ discrete contribution heat map."""
    keys, values = mean_region_fractions(input)
    masked = np.ma.masked_less_equal(values, 0.0)
    positive = values[values > 0.0]
    norm = None
    if positive.size and float(np.max(positive) / np.min(positive)) > 1.0e3:
        norm = LogNorm(vmin=float(np.min(positive)), vmax=float(np.max(positive)))
    figure, axis = plt.subplots(
        figsize=(max(6.0, 0.55 * len(keys) + 2.0), 4.5),
        constrained_layout=True,
    )
    image = axis.imshow(
        masked,
        aspect="auto",
        interpolation="nearest",
        cmap="viridis",
        norm=norm,
    )
    axis.set_xticks(np.arange(len(keys)), labels=np.arange(len(keys)))
    axis.set_yticks(
        np.arange(len(COEFFICIENTS)),
        labels=[label for _, label in COEFFICIENTS],
    )
    axis.set_xlabel("Region index")
    axis.set_ylabel("Transfer coefficient")
    colorbar = figure.colorbar(image, ax=axis)
    colorbar.set_label("Time-mean contribution fraction")
    paths = save_figure(figure, output / "contribution", formats, dpi=180)
    plt.close(figure)
    return paths
