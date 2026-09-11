"""The time shift of the two sets of results is estimated by flux curve cross-correlation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .data import read_rows, write_rows


def read_flux_curve(path: Path) -> np.ndarray:
    """Read the frame number and throughput required for temporal alignment."""
    rows = read_rows(path)
    return np.array([
        (int(row.get("frame", row.get("nt", ""))), float(row["F_nu_Jy"]))
        for row in rows
    ])


@dataclass(frozen=True)
class FluxAlignment:
    """A discrete flux alignment and its complete search criteria."""

    time_shift: float
    lag_steps: int
    correlation: float
    search_left: float
    search_right: float
    min_overlap_fraction: float
    overlap_frames: int
    dt: float


def normalize_curve(values: np.ndarray) -> np.ndarray:
    """The mean is removed and the curve is normalized for calculation of cross-correlation."""
    centered = values - np.mean(values)
    scale = np.linalg.norm(centered)
    return centered if scale == 0.0 else centered / scale


def overlap_at_lag(reference: np.ndarray, target: np.ndarray, lag_steps: int) -> tuple[np.ndarray, np.ndarray]:
    """Intercept the overlap of two curves at a given discrete time delay."""
    if lag_steps > 0:
        return reference[:-lag_steps], target[lag_steps:]
    if lag_steps < 0:
        return reference[-lag_steps:], target[:lag_steps]
    return reference, target


def find_flux_shift(
    reference: np.ndarray,
    target: np.ndarray,
    *,
    dt: float,
    max_lag: float | None = None,
    search_left: float | None = None,
    search_right: float | None = None,
    min_overlap_fraction: float = 0.75,
) -> FluxAlignment:
    """Search for the discrete delay with the largest correlation coefficient."""
    if max_lag is not None:
        if search_left is not None or search_right is not None:
            raise ValueError("Use either max_lag or search_left/search_right.")
        search_left = -max_lag
        search_right = max_lag
    if search_left is None or search_right is None:
        raise ValueError("A finite time-shift search interval is required.")
    if (
        not math.isfinite(search_left)
        or not math.isfinite(search_right)
        or search_left > search_right
        or not math.isfinite(dt)
        or dt <= 0.0
    ):
        raise ValueError("Invalid time-shift search interval or dt.")
    common_nt = np.intersect1d(reference[:, 0].astype(int), target[:, 0].astype(int))
    if common_nt.size == 0:
        raise ValueError("The two flux curves have no common nt range.")
    ref_by_nt = {int(row[0]): float(row[1]) for row in reference}
    target_by_nt = {int(row[0]): float(row[1]) for row in target}
    ref_flux = np.array([ref_by_nt[int(nt)] for nt in common_nt])
    target_flux = np.array([target_by_nt[int(nt)] for nt in common_nt])

    # Production window endpoints usually do not fall on discrete frame times; search the nearest frame shift,
    # But audit records still retain the original double endpoint.
    min_lag_steps = int(round(-search_right / dt))
    max_lag_steps = int(round(-search_left / dt))
    min_overlap = int(math.ceil(min_overlap_fraction * common_nt.size))
    best_lag = 0
    best_corr = -np.inf
    best_overlap = 0
    for lag_steps in range(min_lag_steps, max_lag_steps + 1):
        ref_part, target_part = overlap_at_lag(ref_flux, target_flux, lag_steps)
        if ref_part.size < min_overlap:
            continue
        correlation = float(np.dot(normalize_curve(ref_part), normalize_curve(target_part)))
        if correlation > best_corr:
            best_lag = lag_steps
            best_corr = correlation
            best_overlap = int(ref_part.size)
    if not math.isfinite(best_corr):
        raise ValueError("No candidate time shift satisfies the overlap requirement.")
    return FluxAlignment(
        time_shift=-best_lag * dt,
        lag_steps=best_lag,
        correlation=best_corr,
        search_left=search_left,
        search_right=search_right,
        min_overlap_fraction=min_overlap_fraction,
        overlap_frames=best_overlap,
        dt=dt,
    )


def align_flux(
    *,
    reference: Path,
    target: Path,
    output: Path,
    dt: float,
    max_lag: float | None = None,
    search_left: float | None = None,
    search_right: float | None = None,
    min_overlap_fraction: float = 0.75,
) -> FluxAlignment:
    """Estimating the time shift of the target outcome from an existing flux curve CSV."""
    reference_curve = read_flux_curve(reference / "flux.csv")
    target_curve = read_flux_curve(target / "flux.csv")

    alignment = find_flux_shift(
        reference_curve,
        target_curve,
        dt=dt,
        max_lag=max_lag,
        search_left=search_left,
        search_right=search_right,
        min_overlap_fraction=min_overlap_fraction,
    )
    path = output / "time_alignment.csv"
    write_rows(path, [{
        "lag_steps": alignment.lag_steps,
        "target_lag_rg_over_c": -alignment.time_shift,
        "target_time_shift_rg_over_c": alignment.time_shift,
        "correlation": alignment.correlation,
        "search_left_rg_over_c": alignment.search_left,
        "search_right_rg_over_c": alignment.search_right,
        "min_overlap_fraction": alignment.min_overlap_fraction,
        "overlap_frames": alignment.overlap_frames,
        "dt_rg_over_c": alignment.dt,
    }])
    print(
        f"Target time shift: {alignment.time_shift:.3f} rg/c; "
        f"correlation={alignment.correlation:.6f}")
    print(f"Wrote {path}")
    return alignment
