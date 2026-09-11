"""Volume weighted radial and polar angular distribution of BHAC fluid volume."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

if __package__ and __package__.startswith("tools."):
    from ..lib.save_fig import save_figure
else:
    from lib.save_fig import save_figure

from .plot import infer_style
from .quantities import FluidFrame


@dataclass(frozen=True)
class Profile:
    """One-dimensional binning statistics and the effective volume of each bin."""

    coordinate: np.ndarray
    value: np.ndarray
    weight: np.ndarray
    coordinate_name: str
    quantity: str


def radial_profile(
    frame: FluidFrame,
    quantity: str,
    *,
    r_min: float,
    r_max: float,
    bins: int | np.ndarray = 100,
) -> Profile:
    """Computes the proper-volume weighted average of a physical quantity with radius."""
    edges = _bin_edges(bins, r_min, r_max)
    r = frame.get("r")
    mask = (r >= r_min) & (r <= r_max) & (r > frame.horizon)
    return weighted_profile(
        r[mask],
        frame.get(quantity)[mask],
        frame.volume[mask],
        edges,
        coordinate_name="r",
        quantity=quantity,
    )


def theta_profile(
    frame: FluidFrame,
    quantity: str,
    *,
    r_min: float,
    r_max: float,
    bins: int | np.ndarray = 90,
) -> Profile:
    """Calculate the volume-weighted average of physical quantities within a given radial shell with polar angle."""
    theta = np.degrees(frame.get("theta"))
    r = frame.get("r")
    edges = _bin_edges(bins, 0.0, 180.0)
    mask = (r >= r_min) & (r <= r_max) & (r > frame.horizon)
    return weighted_profile(
        theta[mask],
        frame.get(quantity)[mask],
        frame.volume[mask],
        edges,
        coordinate_name="theta_deg",
        quantity=quantity,
    )


def weighted_profile(
    coordinate: np.ndarray,
    values: np.ndarray,
    weights: np.ndarray,
    edges: np.ndarray,
    *,
    coordinate_name: str,
    quantity: str,
) -> Profile:
    """Computes a weighted average of finite values with given bounds."""
    coordinate = np.asarray(coordinate, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    valid = np.isfinite(coordinate) & np.isfinite(values) & np.isfinite(weights) & (weights > 0.0)
    index = np.digitize(coordinate[valid], edges) - 1
    inside = (index >= 0) & (index < edges.size - 1)
    index = index[inside]
    value = values[valid][inside]
    weight = weights[valid][inside]
    count = edges.size - 1
    weight_sum = np.bincount(index, weights=weight, minlength=count)
    value_sum = np.bincount(index, weights=value * weight, minlength=count)
    mean = np.divide(value_sum, weight_sum, out=np.full(count, np.nan), where=weight_sum > 0.0)
    centers = 0.5 * (edges[:-1] + edges[1:])
    return Profile(centers, mean, weight_sum, coordinate_name, quantity)


def smooth_profile(profile: Profile, window: int = 5) -> Profile:
    """Performs a bounds-preserving moving average on valid bins."""
    if window <= 1 or profile.value.size < window:
        return profile
    if window % 2 == 0:
        raise ValueError("Profile smoothing window must be odd.")
    pad = window // 2
    value = profile.value.copy()
    for index in range(pad, value.size - pad):
        section = profile.value[index - pad:index + pad + 1]
        finite = section[np.isfinite(section)]
        if finite.size:
            value[index] = np.mean(finite)
    return Profile(profile.coordinate, value, profile.weight, profile.coordinate_name, profile.quantity)


def write_profile(profile: Profile, output: Path) -> Path:
    """Write one-dimensional statistics as headered CSV."""
    output = Path(output)
    if not output.is_absolute():
        raise ValueError("BHAC profile output path must be absolute.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow((profile.coordinate_name, profile.quantity, "volume"))
        writer.writerows(zip(profile.coordinate, profile.value, profile.weight))
    return output


def plot_profile(
    frame: FluidFrame,
    profile: Profile,
    output: Path,
    *,
    formats: tuple[str, ...] = ("png",),
    logarithmic: bool = False,
    boundaries: tuple[float, ...] = (),
) -> list[Path]:
    """Draw a one-dimensional profile using the old large font style."""
    output = Path(output)
    if not output.is_absolute():
        raise ValueError("BHAC profile output path must be absolute.")
    style = infer_style((10.0, 6.0), base_size=24)
    figure, axis = plt.subplots(figsize=style.figsize, dpi=300)
    values = profile.value
    symbol = _quantity_label(profile.quantity)
    ylabel = rf"$\langle {symbol}\rangle_V$"
    if logarithmic:
        values = np.log10(np.where(values > 0.0, values, np.nan))
        ylabel = rf"$\log_{{10}}\langle {symbol}\rangle_V$"
    axis.plot(profile.coordinate, values, linewidth=2.0)
    for boundary in boundaries:
        axis.axvline(boundary, color="darkgreen", linestyle="--", linewidth=1.5)
    axis.set_title(rf"$t={frame.time:g}\,r_g/c$", fontsize=style.fontsize)
    if profile.coordinate_name == "theta_deg":
        axis.set_xlabel(r"$\theta\,[\mathrm{deg}]$", fontsize=style.fontsize)
        axis.set_xlim(0.0, 180.0)
    else:
        axis.set_xlabel(r"$r\,[r_g]$", fontsize=style.fontsize)
    axis.set_ylabel(ylabel, fontsize=style.fontsize)
    axis.tick_params(labelsize=style.fontsize)
    axis.grid(alpha=0.25)
    paths = save_figure(figure, output, formats, dpi=300, pad_inches=0.05)
    plt.close(figure)
    return paths


def boundary_angles(
    frames: list[FluidFrame],
    quantity: str,
    *,
    threshold: float,
    tolerance: float,
    r_min: float,
    r_max: float,
) -> tuple[float | None, float | None]:
    """Estimates the average polar angle for a given threshold of a physical quantity in the northern and southern hemispheres."""
    north_values = []
    north_weights = []
    south_values = []
    south_weights = []
    for frame in frames:
        r = frame.get("r")
        theta = np.degrees(frame.get("theta"))
        values = frame.get(quantity)
        mask = (
            (r >= r_min)
            & (r <= r_max)
            & (r > frame.horizon)
            & np.isfinite(values)
            & (np.abs(values - threshold) <= tolerance)
        )
        north = mask & (theta <= 90.0)
        south = mask & (theta > 90.0)
        north_values.append(theta[north])
        north_weights.append(frame.volume[north])
        south_values.append(theta[south])
        south_weights.append(frame.volume[south])
    return (
        _combined_average(north_values, north_weights),
        _combined_average(south_values, south_weights),
    )


def _combined_average(values: list[np.ndarray], weights: list[np.ndarray]) -> float | None:
    count = sum(array.size for array in values)
    if count == 0:
        return None
    value = np.concatenate(values)
    weight = np.concatenate(weights)
    return float(np.average(value, weights=weight))


def _bin_edges(bins: int | np.ndarray, start: float, end: float) -> np.ndarray:
    if isinstance(bins, int):
        if bins <= 0:
            raise ValueError("Profile bin count must be positive.")
        return np.linspace(start, end, bins + 1)
    edges = np.asarray(bins, dtype=np.float64)
    if edges.ndim != 1 or edges.size < 2 or np.any(np.diff(edges) <= 0.0):
        raise ValueError("Profile bin edges must be a strictly increasing one-dimensional array.")
    return edges


def _quantity_label(name: str) -> str:
    labels = {
        "rho": r"\rho",
        "rho_cgs": r"\rho",
        "u": "u",
        "pg": "p_g",
        "ne": "n_e",
        "B": "B",
        "bsq": "b^2",
        "beta": r"\beta",
        "sigma": r"\sigma",
        "thetae": r"\Theta_e",
        "Te": "T_e",
        "be": r"\mathrm{Be}",
        "omega_b": r"\Omega_B/\Omega_H",
        "eta_b": r"\eta_B",
        "vr": "v^r",
        "power": "p",
        "gamma_min": r"\gamma_{\min}",
        "f_nth": r"n_{\mathrm{nth}}/n_e",
    }
    return labels.get(name, rf"\mathrm{{{name}}}")
