"""Calculate common image observables in one pass and write them to CSV."""

from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np

from .cancel import throw_if_cancelled
from .constant import JY, PC
from .data import Result, find_frames, fov_muas, frame_bounds, load_iqu, rg_cm, write_rows
from .parallel import process_tasks


def radius_key(radius_muas: float | None) -> str:
    """Convert ring radius to a short identifier suitable for CSV fields and file names."""
    if radius_muas is None:
        return "full"
    return f"{radius_muas:g}".replace(".", "p") + "muas"


def observable_paths(output: Path) -> dict[str, Path]:
    """Returns a fixed CSV path of three types of derived observations."""
    return {
        "flux": output / "flux.csv",
        "lp": output / "lp.csv",
        "beta2": output / "beta2.csv",
    }


def _csv_frames(
    path: Path,
    required_fields: set[str],
) -> list[int] | None:
    try:
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            fields = set(reader.fieldnames or ())
            if not required_fields <= fields:
                return None
            rows = list(reader)
        if not rows:
            return None
        return [int(row["frame"]) for row in rows]
    except (OSError, KeyError, TypeError, ValueError):
        return None


def reusable_observables(
    *,
    result: Result,
    output: Path,
    nt_start: int | None = None,
    nt_end: int | None = None,
    radii_muas: tuple[float | None, ...] = (None,),
) -> dict[str, Path] | None:
    """Verify the fields and frame sequences of the existing observation CSV, and return the path if they are compatible."""
    start, end = frame_bounds(result, nt_start, nt_end)
    frames = find_frames(result.path, start, end, required="IQU")
    if not frames:
        return None
    paths = observable_paths(output)
    required = {
        "flux": {"frame", "F_nu_Jy"},
        "lp": {
            "frame", "local_linear_fraction", "net_linear_fraction",
        },
        "beta2": {"frame"},
    }
    for radius in radii_muas:
        if radius is None:
            required["beta2"].update({"beta2_abs", "beta2_angle_deg"})
        else:
            key = radius_key(radius)
            required["beta2"].update({
                f"beta2_{key}_abs",
                f"beta2_{key}_angle_deg",
            })
    for name, path in paths.items():
        if _csv_frames(path, required[name]) != frames:
            return None
    return paths


def calc_flux(image: np.ndarray, result: Result) -> tuple[float, float]:
    """Calculate flux density and total intensity from an intensity map."""
    image = np.real(np.asarray(image, dtype=np.float64))
    total_i = float(np.nansum(image))
    npix = int(image.shape[0])

    # Normalization of screen integrals, photometric and observed fluxes is consistent with the MATLAB reference implementation.
    screen_flux = total_i * (2.0 * math.pi / (npix * npix)) * (1.0 - math.cos(result.fov / 2.0))
    rg = rg_cm(result)
    luminosity_density = 4.0 * math.pi * result.ro**2 * rg * rg * screen_flux
    distance_cm = result.distance_pc * PC
    flux_jy = luminosity_density / (4.0 * math.pi * distance_cm * distance_cm) / JY
    return flux_jy, total_i


def calc_linear_fractions(
    i_map: np.ndarray,
    q_map: np.ndarray,
    u_map: np.ndarray,
) -> tuple[float, float]:
    """Calculate the local linear polarization degree and net linear polarization degree of a single frame."""
    total_i = float(np.nansum(i_map))
    if total_i == 0.0:
        return math.nan, math.nan
    local = float(np.nansum(np.hypot(q_map, u_map)) / total_i)
    net = float(math.hypot(float(np.nansum(q_map)), float(np.nansum(u_map))) / total_i)
    return local, net


def calc_beta2(
    i_map: np.ndarray,
    q_map: np.ndarray,
    u_map: np.ndarray,
    result: Result,
    *,
    radius_muas: float | None,
) -> tuple[float, float]:
    """Calculate the amplitude and phase of $\beta_2$ within the specified ring area of a single frame."""
    npix = int(i_map.shape[0])
    y_indices, x_indices = np.meshgrid(np.arange(npix), np.arange(npix))
    center = (npix - 1) / 2.0
    rho_sq = (x_indices - center) ** 2 + (y_indices - center) ** 2
    phi = np.arctan2(-(x_indices - center), y_indices - center)

    # `None` uses the imaging disk; for the given radius, a ring with a width of 4 pixels is used.
    if radius_muas is None:
        mask = rho_sq <= (npix / 2.0) ** 2
    else:
        radius_pixels = radius_muas * npix / fov_muas(result)
        mask = (rho_sq >= (radius_pixels - 2.0) ** 2) & (rho_sq <= (radius_pixels + 2.0) ** 2)
    total_i = float(np.nansum(i_map[mask]))
    if total_i == 0.0:
        return math.nan, math.nan
    value = np.nansum((q_map[mask] + 1j * u_map[mask]) * np.exp(-2j * phi[mask])) / total_i
    return float(np.abs(value)), float(np.degrees(np.angle(value)))


def calc_observable_frame(
    task: tuple[Result, int, tuple[float | None, ...], Path | None],
) -> tuple[dict[str, float | int], dict[str, float | int], dict[str, float | int]]:
    """Read a single frame of Stokes I/Q/U and calculate flux, linear polarization and $\beta_2$."""
    result, nt, radii_muas, cancel_file = task
    throw_if_cancelled(cancel_file)
    i_map, q_map, u_map = load_iqu(result.path, nt)
    throw_if_cancelled(cancel_file)
    flux_jy, _ = calc_flux(i_map, result)
    local_lp, net_lp = calc_linear_fractions(i_map, q_map, u_map)

    flux_row = {
        "frame": nt,
        "F_nu_Jy": flux_jy,
    }
    lp_row = {
        "frame": nt,
        "local_linear_fraction": local_lp,
        "net_linear_fraction": net_lp,
    }
    beta2_row: dict[str, float | int] = {
        "frame": nt,
    }
    for radius in radii_muas:
        magnitude, angle = calc_beta2(i_map, q_map, u_map, result, radius_muas=radius)
        if radius is None:
            beta2_row["beta2_abs"] = magnitude
            beta2_row["beta2_angle_deg"] = angle
        else:
            key = radius_key(radius)
            beta2_row[f"beta2_{key}_abs"] = magnitude
            beta2_row[f"beta2_{key}_angle_deg"] = angle
    return flux_row, lp_row, beta2_row


def calc_observables(
    *,
    result: Result,
    output: Path,
    nt_start: int | None = None,
    nt_end: int | None = None,
    radii_muas: tuple[float | None, ...] = (None,),
    workers: int = 1,
    cancel_file: Path | None = None,
) -> dict[str, Path]:
    """Calculate flux, linear polarization, and $\beta_2$ all at once, and write out CSV respectively."""
    start, end = frame_bounds(result, nt_start, nt_end)
    frames = find_frames(result.path, start, end)
    if not frames:
        raise ValueError(f"No intensity files found in {result.path}.")

    tasks = ((result, nt, radii_muas, cancel_file) for nt in frames)
    rows = process_tasks(calc_observable_frame, tasks, workers)
    flux_rows = [item[0] for item in rows]
    lp_rows = [item[1] for item in rows]
    beta2_rows = [item[2] for item in rows]
    targets = observable_paths(output)
    paths = {
        "flux": write_rows(targets["flux"], flux_rows),
        "lp": write_rows(targets["lp"], lp_rows),
        "beta2": write_rows(targets["beta2"], beta2_rows),
    }
    for path in paths.values():
        print(f"Saved observable data: {path}")
    flux_values = [float(row["F_nu_Jy"]) for row in flux_rows]
    print(f"Frames: {len(rows)}; F_nu={min(flux_values):.6e} .. {max(flux_values):.6e} Jy")
    return paths
