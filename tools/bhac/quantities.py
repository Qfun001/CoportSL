"""Construct the fluid physical quantities required for plotting and statistics from BHAC primitives."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

if __package__ and __package__.startswith("tools."):
    from ..lib.constant import C, G, K_B, M_E, M_P, M_SUN, YEAR_SECONDS
else:
    from lib.constant import C, G, K_B, M_E, M_P, M_SUN, YEAR_SECONDS

from .c2p import (
    CellGeometry,
    MagneticGeometry,
    PrimitiveGeometry,
    cell_geometry,
    magnetic_geometry,
    primitive_geometry,
    to_primitives,
)
from .read_bhac import BhacGrid, list_frames, load_grid, read_frame_with_grid


MP_OVER_ME = 0.0015033 / (M_E * C * C)


@dataclass(frozen=True)
class ModelParameters:
    """Physical normalization and electron-model parameters for GRMHD data."""

    mbh: float = 6.5e9  # Black hole mass, unit mass of the sun.
    mdot: float = 2.46e-4  # Physical accretion rate, unit solar mass per year.
    mdot_sim: float = 50.0  # Simulated accretion rate normalized in MBH/T_unit.
    r_low: float = 10.0
    r_high: float = 100.0
    beta0: float = 1.0
    p_min: float = 2.001
    p_max: float = 10.0
    gamma_ratio: float = 1.0e5


@dataclass(frozen=True)
class BhacRun:
    """A set of grids, coordinates, and metric metrics shared by BHAC frames."""

    input_dir: Path
    grid_path: Path
    paths: tuple[Path, ...]
    grid: BhacGrid
    cells: CellGeometry
    primitive_geom: PrimitiveGeometry
    magnetic_geom: MagneticGeometry
    spin: float
    hslope: float
    gamma: float


@dataclass(frozen=True)
class FluidFrame:
    """One frame of flat physical quantities used for GRMHD plotting and statistics."""

    path: Path
    nt: int
    time: float  # Unit rg/c.
    horizon: float  # Event horizon radius, in rg.
    values: dict[str, np.ndarray]
    volume: np.ndarray  # proper cell volume, unit rg^3.
    coordinate_volume: np.ndarray  # MKSBHAC coordinate element volume dx1 dx2 dx3.

    def get(self, name: str) -> np.ndarray:
        """Returns the physical quantity by domain name."""
        try:
            return self.values[name]
        except KeyError as exc:
            available = ", ".join(sorted(self.values))
            raise KeyError(f"Unknown BHAC quantity {name!r}; available: {available}") from exc


def prepare_run(input_dir: Path, grid_path: Path) -> BhacRun:
    """Read the static grid once and precompute geometry reused by all frames."""
    input_dir = Path(input_dir)
    grid_path = Path(grid_path)
    if not input_dir.is_absolute() or not grid_path.is_absolute():
        raise ValueError("BHAC input and grid paths must be absolute.")
    paths = tuple(list_frames(input_dir))
    if not paths:
        raise FileNotFoundError(f"No dataNNNN.dat frames found in {input_dir}")
    grid = load_grid(paths[0], grid_path)
    if len(grid.header.neqpar_values) < 4:
        raise ValueError(f"BHAC header does not contain spin and adiabatic index: {paths[0]}")
    gamma = grid.header.neqpar_values[0]
    spin = grid.header.neqpar_values[3]
    hslope = grid.info.hslope
    cells = cell_geometry(grid, spin=spin, hslope=hslope)
    return BhacRun(
        input_dir=input_dir,
        grid_path=grid_path,
        paths=paths,
        grid=grid,
        cells=cells,
        primitive_geom=primitive_geometry(cells.coords, spin=spin, hslope=hslope),
        magnetic_geom=magnetic_geometry(cells.coords, spin=spin, hslope=hslope),
        spin=spin,
        hslope=hslope,
        gamma=gamma,
    )


def path_for_frame(run: BhacRun, nt: int) -> Path:
    """Returns the path to the BHAC frame at the specified number and checks for file existence."""
    path = run.input_dir / f"data{nt:04d}.dat"
    if not path.is_file():
        raise FileNotFoundError(f"Missing BHAC frame: {path}")
    return path


def load_fluid_frame(run: BhacRun, path: Path, model: ModelParameters) -> FluidFrame:
    """Reads a frame and calculates the main fluid physics used by the current C++ model."""
    raw = read_frame_with_grid(run.grid, path)
    primitive = to_primitives(raw, coords=run.cells.coords, geom=run.primitive_geom)
    if primitive.data is None:
        raise ValueError(f"Primitive conversion returned no data for {path}")

    rho, u, u1, u2, u3, B1, B2, B3 = primitive.data
    coords = run.cells.coords
    x1 = coords[..., 0]
    x2 = coords[..., 1]
    r = np.exp(x1)
    hfac = 1.0 + run.hslope * np.cos(2.0 * x2)
    theta = x2 + 0.5 * run.hslope * np.sin(2.0 * x2)
    phi = coords[..., 2]
    geom = run.magnetic_geom

    lfac = np.sqrt(
        geom.g11 * u1 * u1
        + 2.0 * geom.g13 * u1 * u3
        + geom.g22 * u2 * u2
        + geom.g33 * u3 * u3
        + 1.0
    )
    U0 = lfac / geom.alpha
    U1_mks = u1 - geom.shift1 * U0
    U2_mks = u2 - geom.shift2 * U0
    U3_mks = u3 - geom.shift3 * U0

    b0 = (
        B1 * (geom.g11 * u1 + geom.g13 * u3)
        + B2 * geom.g22 * u2
        + B3 * (geom.g13 * u1 + geom.g33 * u3)
    ) / geom.alpha
    b1_mks = (B1 + geom.alpha * b0 * U1_mks) / lfac
    b2_mks = (B2 + geom.alpha * b0 * U2_mks) / lfac
    b3_mks = (B3 + geom.alpha * b0 * U3_mks) / lfac
    bd0 = geom.g00 * b0 + geom.g01 * b1_mks + geom.g03 * b3_mks
    bd1 = geom.g01 * b0 + geom.g11 * b1_mks + geom.g13 * b3_mks
    bd2 = geom.g22 * b2_mks
    bd3 = geom.g03 * b0 + geom.g13 * b1_mks + geom.g33 * b3_mks
    bsq = np.abs(b0 * bd0 + b1_mks * bd1 + b2_mks * bd2 + b3_mks * bd3) + 1.0e-6

    # contravariant MKS components are converted to KS components.
    Ur = r * U1_mks
    Utheta = hfac * U2_mks
    Uphi = U3_mks
    Br = r * B1
    Btheta = hfac * B2
    Bphi = B3

    sin_theta = np.sin(theta)
    sin2_theta = sin_theta * sin_theta
    cos_theta = np.cos(theta)
    sigma2 = r * r + run.spin * run.spin * cos_theta * cos_theta
    g00_ks = -1.0 + 2.0 * r / sigma2
    g01_ks = 2.0 * r / sigma2
    g03_ks = -2.0 * run.spin * r * sin2_theta / sigma2
    g11_ks = 1.0 + 2.0 * r / sigma2
    g22_ks = sigma2
    g33_ks = sin2_theta * (sigma2 + run.spin * run.spin * g11_ks * sin2_theta)
    u_t = g00_ks * U0 + g01_ks * Ur + g03_ks * Uphi

    pg = (run.gamma - 1.0) * u
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        enthalpy = (rho + u + pg) / rho
        bernoulli = -enthalpy * u_t
        beta = pg / (0.5 * (bsq + 1.0e-6))
        sigma = bsq / rho
        beta2 = np.square(beta / model.beta0)
        trat = (model.r_high * beta2 + model.r_low) / (1.0 + beta2)
        thetae = (pg / rho) * MP_OVER_ME / (trat + 1.0)

    units = _units(model)
    rho_cgs = rho * units["rho"] / (C * C)
    pg_cgs = pg * units["rho"]
    ne = rho * units["ne"] + 1.0e-6
    B = np.sqrt(bsq) * units["B"]
    Te = thetae * M_E * C * C / K_B

    Bp2 = g11_ks * Br * Br + g22_ks * Btheta * Btheta
    vp_dot_bp = g11_ks * (Ur / U0) * Br + g22_ks * (Utheta / U0) * Btheta
    horizon = 1.0 + np.sqrt(1.0 - run.spin * run.spin)
    omega_h = run.spin / (2.0 * horizon)
    with np.errstate(divide="ignore", invalid="ignore"):
        omega_b = (Uphi / U0 - Bphi * vp_dot_bp / Bp2) / omega_h
        eta_b = np.arctan2(np.sqrt(g33_ks) * np.abs(Bphi), np.sqrt(Bp2))
        btheta_over_b = np.sqrt(g22_ks) * Btheta / np.sqrt(bsq)
        vr = Ur / U0

    safe_sigma = np.maximum(sigma, 1.0e-300)
    power = (
        1.8
        + 0.7 / np.sqrt(safe_sigma)
        + 3.7 / np.power(safe_sigma, 0.19)
        * np.tanh(beta * 23.4 * np.power(safe_sigma, 0.26))
    )
    power = np.clip(power, model.p_min, model.p_max)
    fthetae = (6.0 + 15.0 * thetae) / (4.0 + 5.0 * thetae)
    gamma_min = np.maximum(1.0, 1.0 + thetae * fthetae)
    gamma_max = model.gamma_ratio * gamma_min
    epsilon = (
        1.0
        - 1.0 / (4.2 * np.power(safe_sigma, 0.55) + 1.0)
        + 0.64 * np.power(safe_sigma, 0.07)
        * np.tanh(-68.0 * np.power(safe_sigma, 0.13) * beta)
    )
    epsilon = np.clip(epsilon, 0.0, 1.0)
    uth = fthetae * thetae
    unth = (power - 1.0) / (power - 2.0) * gamma_min - 1.0
    denominator = (1.0 - epsilon) * unth + epsilon * uth
    f_nth = np.divide(
        epsilon * uth,
        denominator,
        out=np.zeros_like(denominator),
        where=np.abs(denominator) > 1.0e-300,
    )
    f_nth = np.clip(f_nth, 0.0, 1.0)

    values = {
        "r": r.ravel(),
        "theta": theta.ravel(),
        "phi": phi.ravel(),
        "rho": rho.ravel(),
        "rho_cgs": rho_cgs.ravel(),
        "u": u.ravel(),
        "pg": pg.ravel(),
        "pg_cgs": pg_cgs.ravel(),
        "u0": U0.ravel(),
        "ur": Ur.ravel(),
        "utheta": Utheta.ravel(),
        "uphi": Uphi.ravel(),
        "Br": Br.ravel(),
        "Btheta": Btheta.ravel(),
        "Bphi": Bphi.ravel(),
        "B": B.ravel(),
        "bsq": bsq.ravel(),
        "beta": beta.ravel(),
        "sigma": sigma.ravel(),
        "thetae": thetae.ravel(),
        "Te": Te.ravel(),
        "ne": ne.ravel(),
        "be": bernoulli.ravel(),
        "omega_b": omega_b.ravel(),
        "eta_b": eta_b.ravel(),
        "vr": vr.ravel(),
        "btheta_over_b": btheta_over_b.ravel(),
        "power": power.ravel(),
        "gamma_min": gamma_min.ravel(),
        "gamma_max": gamma_max.ravel(),
        "f_nth": f_nth.ravel(),
        "sqrt_neg_g": (
            sigma2 * np.abs(sin_theta) * r * hfac
        ).ravel(),
    }
    count = raw.header.active_cells
    if any(array.size != count for array in values.values()):
        raise ValueError(f"Derived BHAC array length mismatch in {path}")
    coordinate_volume = np.empty_like(run.cells.volumes)
    for leaf, block in enumerate(run.grid.blocks):
        if block.dx is None:
            raise ValueError("BHAC block geometry is incomplete.")
        coordinate_volume[leaf] = np.prod(block.dx)
    return FluidFrame(
        path=Path(path),
        nt=int(Path(path).stem.removeprefix("data")),
        time=raw.header.time,
        horizon=horizon,
        values=values,
        volume=run.cells.volumes.ravel(),
        coordinate_volume=coordinate_volume.ravel(),
    )


def _units(model: ModelParameters) -> dict[str, float]:
    """Reproduce the GRMHD unit normalization of `src/physics/Constants.h`."""
    mbh = model.mbh * M_SUN
    length = G * mbh / (C * C)
    time = length / C
    mdot_sim = model.mdot_sim * mbh / time
    mdot = model.mdot * M_SUN / YEAR_SECONDS
    ratio = mdot / mdot_sim
    rho = mbh / (time * time * length) * ratio
    ne = rho / ((M_P + M_E) * C * C)
    return {"rho": rho, "ne": ne, "B": np.sqrt(4.0 * np.pi * rho)}
