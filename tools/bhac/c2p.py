"""Conversion of BHAC raw/conserved variables to primitive variables."""

from __future__ import annotations

from dataclasses import dataclass
import itertools

import numpy as np

from .read_bhac import BhacFrame, BhacGrid, block_centers, cell_centers


PRIMITIVE_NAMES = ("rho", "u", "u1", "u2", "u3", "B1", "B2", "B3")


@dataclass(frozen=True)
class PrimitiveGeometry:
    """The primitive conversion only relies on geometric quantities of grid coordinates."""

    g11: np.ndarray
    g13: np.ndarray
    g22: np.ndarray
    g33: np.ndarray
    gamma11: np.ndarray
    gamma13: np.ndarray
    gamma22: np.ndarray
    gamma33: np.ndarray
    valid: np.ndarray


@dataclass(frozen=True)
class MagneticGeometry:
    """The calculation of the magnetic field strength of the co-moving system only relies on the geometric quantities of the grid coordinates."""

    g00: np.ndarray
    g01: np.ndarray
    g03: np.ndarray
    g11: np.ndarray
    g13: np.ndarray
    g22: np.ndarray
    g33: np.ndarray
    alpha: np.ndarray
    shift1: np.ndarray
    shift2: np.ndarray
    shift3: np.ndarray


@dataclass(frozen=True)
class PrimitiveFrame:
    """A frame of converted GRMHD primitive variables."""

    frame: BhacFrame
    variables: dict[str, np.ndarray]
    data: np.ndarray | None = None


@dataclass(frozen=True)
class CellGeometry:
    """The volume center of the static mesh and the proper cell volume."""

    coords: np.ndarray  # MKSBHAC Volume center with shape (nleafs, cells, ndim).
    volumes: np.ndarray  # proper cell volume, unit is rg^3.


def to_primitives(
    frame: BhacFrame,
    *,
    spin: float | None = None,
    hslope: float | None = None,
    volume_center: bool = True,
    coords: np.ndarray | None = None,
    geom: PrimitiveGeometry | None = None,
) -> PrimitiveFrame:
    """Convert BHAC raw/conserved variables to primitive variables.

    The current implementation corresponds to the MKSBHAC data path on the C++ side, and the output shape is
    `rho, u, u1, u2, u3, B1, B2, B3` of `(nleafs, cells_per_block)`."""
    if frame.grid is None:
        raise ValueError("Primitive conversion requires a frame read with load_grid/read_frame_with_grid.")

    grid = frame.grid
    spin = grid.header.neqpar_values[3] if spin is None else spin
    hslope = grid.info.hslope if hslope is None else hslope
    if coords is None:
        coords = volume_centers(grid, spin=spin, hslope=hslope) if volume_center else cell_centers(grid)
    data = _convert_mks_bhac(frame, coords=coords, spin=spin, hslope=hslope, geom=geom)
    variables = {name: data[index] for index, name in enumerate(PRIMITIVE_NAMES)}
    return PrimitiveFrame(frame=frame, variables=variables, data=data)


def radius_mks(coords: np.ndarray) -> np.ndarray:
    """Returns the radial radius of the MKSBHAC coordinate."""
    return np.exp(coords[..., 0])


def primitive_geometry(coords: np.ndarray, *, spin: float, hslope: float) -> PrimitiveGeometry:
    """Precompute the fixed geometric quantities required for primitive transformations."""
    g11, g13, g22, g33 = spatial_metric_down_mks(coords, spin=spin, hslope=hslope)
    gamma11, gamma13, gamma22, gamma33 = gamma_up_mks(coords, spin=spin, hslope=hslope)
    valid = np.exp(coords[..., 0]) > 1.0
    return PrimitiveGeometry(
        g11=g11,
        g13=g13,
        g22=g22,
        g33=g33,
        gamma11=gamma11,
        gamma13=gamma13,
        gamma22=gamma22,
        gamma33=gamma33,
        valid=valid,
    )


def magnetic_geometry(coords: np.ndarray, *, spin: float, hslope: float) -> MagneticGeometry:
    """Fixed geometric quantities required to precompute the magnetic field strength of the co-moving system."""
    g00, g01, g03, g11, g13, g22, g33 = metric_down_mks(coords, spin=spin, hslope=hslope)
    gu00, gu01, _, _, _, _ = metric_up_mks(coords, spin=spin, hslope=hslope)
    alpha = 1.0 / np.sqrt(-gu00)
    shift1 = gu01 / (-gu00)
    shift2 = np.zeros_like(shift1)
    shift3 = np.zeros_like(shift1)
    return MagneticGeometry(
        g00=g00,
        g01=g01,
        g03=g03,
        g11=g11,
        g13=g13,
        g22=g22,
        g33=g33,
        alpha=alpha,
        shift1=shift1,
        shift2=shift2,
        shift3=shift3,
    )


def comoving_b(
    primitive: np.ndarray,
    coords: np.ndarray | None = None,
    *,
    spin: float | None = None,
    hslope: float | None = None,
    geom: MagneticGeometry | None = None,
) -> np.ndarray:
    """Reconstruct the magnetic field strength of the co-moving system from primitive variables."""
    if geom is None:
        if coords is None or spin is None or hslope is None:
            raise ValueError("comoving_b requires coords/spin/hslope or a precomputed geom.")
        geom = magnetic_geometry(coords, spin=spin, hslope=hslope)

    u1 = primitive[2]
    u2 = primitive[3]
    u3 = primitive[4]
    B1 = primitive[5]
    B2 = primitive[6]
    B3 = primitive[7]

    gvdot = geom.g11 * u1 * u1 + 2.0 * geom.g13 * u1 * u3 + geom.g22 * u2 * u2 + geom.g33 * u3 * u3
    lfac = np.sqrt(gvdot + 1.0)
    B0 = (
        B1 * (geom.g11 * u1 + geom.g13 * u3) +
        B2 * (geom.g22 * u2) +
        B3 * (geom.g13 * u1 + geom.g33 * u3)
    ) / geom.alpha

    U1 = u1 - geom.shift1 * lfac / geom.alpha
    U2 = u2 - geom.shift2 * lfac / geom.alpha
    U3 = u3 - geom.shift3 * lfac / geom.alpha

    Bu0 = B0
    Bu1 = (B1 + geom.alpha * Bu0 * U1) / lfac
    Bu2 = (B2 + geom.alpha * Bu0 * U2) / lfac
    Bu3 = (B3 + geom.alpha * Bu0 * U3) / lfac

    Bd0 = geom.g00 * Bu0 + geom.g01 * Bu1 + geom.g03 * Bu3
    Bd1 = geom.g01 * Bu0 + geom.g11 * Bu1 + geom.g13 * Bu3
    Bd2 = geom.g22 * Bu2
    Bd3 = geom.g03 * Bu0 + geom.g13 * Bu1 + geom.g33 * Bu3
    bsq = np.abs(Bu0 * Bd0 + Bu1 * Bd1 + Bu2 * Bd2 + Bu3 * Bd3) + 1.0e-6
    return np.sqrt(bsq)


def cell_geometry(grid: BhacGrid, *, spin: float, hslope: float) -> CellGeometry:
    """Calculate the volume center and proper cell volume using 3D Simpson integrals."""
    output = np.empty((grid.header.nleafs, grid.header.cells_per_block, grid.header.ndimini), dtype=np.float64)
    volumes = np.empty((grid.header.nleafs, grid.header.cells_per_block), dtype=np.float64)
    weights_1d = (-1.0, 0.0, 1.0)
    coeff_1d = (1.0, 4.0, 1.0)
    for leaf, block in enumerate(grid.blocks):
        if block.dx is None:
            raise ValueError("Block geometry has not been filled.")
        centers = block_centers(block)
        norm = np.zeros(centers.shape[0], dtype=np.float64)
        moment = np.zeros_like(centers)
        for ix, iy, iz in itertools.product(range(3), repeat=3):
            coeff = coeff_1d[ix] * coeff_1d[iy] * coeff_1d[iz]
            offset = np.array([
                0.5 * block.dx[0] * weights_1d[ix],
                0.5 * block.dx[1] * weights_1d[iy],
                0.5 * block.dx[2] * weights_1d[iz],
            ])
            point = centers + offset
            det = detgamma_mks(point, spin=spin, hslope=hslope)
            weighted = coeff * det
            norm += weighted
            moment += weighted[:, None] * point
        output[leaf] = moment / norm[:, None]
        volumes[leaf] = norm * np.prod(block.dx) / 216.0
    return CellGeometry(coords=output, volumes=volumes)


def volume_centers(grid: BhacGrid, *, spin: float, hslope: float) -> np.ndarray:
    """Calculate volume center by 3D Simpson weights C++ `calc_coord_bar`."""
    return cell_geometry(grid, spin=spin, hslope=hslope).coords


def detgamma_mks(x: np.ndarray, *, spin: float, hslope: float) -> np.ndarray:
    """Computes the square root of the MKSBHAC spatial metric determinant."""
    g11, g13, g22, g33 = spatial_metric_down_mks(x, spin=spin, hslope=hslope)
    det = g22 * (g11 * g33 - g13 * g13)
    return np.sqrt(det)


def spatial_metric_down_mks(
    x: np.ndarray,
    *,
    spin: float,
    hslope: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Returns the nonzero components `g11, g13, g22, g33` of the MKSBHAC spatial covariance metric."""
    r = np.exp(x[..., 0])
    theta = x[..., 1] + 0.5 * hslope * np.sin(2.0 * x[..., 1])
    sinth = np.sin(theta)
    sin2th = sinth * sinth
    costh = np.cos(theta)
    rho2 = r * r + spin * spin * costh * costh
    rfac = r
    hfac = 1.0 + hslope * np.cos(2.0 * x[..., 1])
    g11 = (1.0 + 2.0 * r / rho2) * rfac * rfac
    g13 = -spin * sin2th * (1.0 + 2.0 * r / rho2) * rfac
    g22 = rho2 * hfac * hfac
    g33 = sin2th * (rho2 + spin * spin * sin2th * (1.0 + 2.0 * r / rho2))
    return g11, g13, g22, g33


def metric_down_mks(
    x: np.ndarray,
    *,
    spin: float,
    hslope: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Returns the nonzero components of the MKSBHAC covariance metric."""
    r = np.exp(x[..., 0])
    theta = x[..., 1] + 0.5 * hslope * np.sin(2.0 * x[..., 1])
    sinth = np.sin(theta)
    sin2th = sinth * sinth
    costh = np.cos(theta)
    rho2 = r * r + spin * spin * costh * costh
    rfac = r
    hfac = 1.0 + hslope * np.cos(2.0 * x[..., 1])
    g00 = -1.0 + 2.0 * r / rho2
    g01 = (2.0 * r / rho2) * rfac
    g03 = -2.0 * spin * r * sin2th / rho2
    g11 = (1.0 + 2.0 * r / rho2) * rfac * rfac
    g13 = -spin * sin2th * (1.0 + 2.0 * r / rho2) * rfac
    g22 = rho2 * hfac * hfac
    g33 = sin2th * (rho2 + spin * spin * sin2th * (1.0 + 2.0 * r / rho2))
    return g00, g01, g03, g11, g13, g22, g33


def metric_up_mks(
    x: np.ndarray,
    *,
    spin: float,
    hslope: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Returns the nonzero components of the MKSBHAC inverse metric."""
    r = np.exp(x[..., 0])
    theta = x[..., 1] + 0.5 * hslope * np.sin(2.0 * x[..., 1])
    sinth = np.sin(theta)
    sin2th = sinth * sinth
    costh = np.cos(theta)
    irho2 = 1.0 / (r * r + spin * spin * costh * costh)
    hfac = 1.0 + hslope * np.cos(2.0 * x[..., 1])
    g00 = -1.0 - 2.0 * r * irho2
    g01 = 2.0 * irho2
    g11 = irho2 * (r * (r - 2.0) + spin * spin) / (r * r)
    g13 = spin * irho2 / r
    g22 = irho2 / (hfac * hfac)
    g33 = irho2 / sin2th
    return g00, g01, g11, g13, g22, g33


def gamma_up_mks(
    x: np.ndarray,
    *,
    spin: float,
    hslope: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Returns the spatially inverse trimetric components used by C++ `convert2prim`."""
    g00, g01, g11, g13, g22, g33 = metric_up_mks(x, spin=spin, hslope=hslope)

    gamma11 = g11 + g01 * g01 / (-g00)
    gamma13 = g13
    gamma22 = g22
    gamma33 = g33
    return gamma11, gamma13, gamma22, gamma33


def _convert_mks_bhac(
    frame: BhacFrame,
    *,
    coords: np.ndarray,
    spin: float,
    hslope: float,
    geom: PrimitiveGeometry | None = None,
) -> np.ndarray:
    names = frame.variables
    required = ("D", "S1", "S2", "S3", "B1", "B2", "B3", "LFAC", "XI")
    missing = [name for name in required if name not in names]
    if missing:
        raise KeyError(f"Missing BHAC variables for primitive conversion: {', '.join(missing)}")

    D = np.asarray(names["D"], dtype=np.float64)
    S1 = np.asarray(names["S1"], dtype=np.float64)
    S2 = np.asarray(names["S2"], dtype=np.float64)
    S3 = np.asarray(names["S3"], dtype=np.float64)
    B1 = np.asarray(names["B1"], dtype=np.float64)
    B2 = np.asarray(names["B2"], dtype=np.float64)
    B3 = np.asarray(names["B3"], dtype=np.float64)
    lfac = np.asarray(names["LFAC"], dtype=np.float64)
    xi = np.asarray(names["XI"], dtype=np.float64)
    gam = frame.header.neqpar_values[0]

    if geom is None:
        geom = primitive_geometry(coords, spin=spin, hslope=hslope)

    bs = S1 * B1 + S2 * B2 + S3 * B3
    bsq = geom.g11 * B1 * B1 + 2.0 * geom.g13 * B1 * B3 + geom.g22 * B2 * B2 + geom.g33 * B3 * B3
    Su1 = geom.gamma11 * S1 + geom.gamma13 * S3
    Su2 = geom.gamma22 * S2
    Su3 = geom.gamma13 * S1 + geom.gamma33 * S3

    rho = D / lfac
    u = (xi / (lfac * lfac) - rho) / gam
    if "DS" in names:
        entropy_u = (np.asarray(names["DS"], dtype=np.float64) / D) * np.power(rho, gam - 1.0) / (gam - 1.0)
        u = np.where(u < 0.0, entropy_u, u)
    u = np.where(u < 0.0, 1.0e-14, u)

    denom = xi + bsq
    u1 = lfac * (Su1 / denom + B1 * bs / (xi * denom))
    u2 = lfac * (Su2 / denom + B2 * bs / (xi * denom))
    u3 = lfac * (Su3 / denom + B3 * bs / (xi * denom))

    data = np.stack((rho, u, u1, u2, u3, B1, B2, B3), axis=0)
    data[:, ~geom.valid] = 0.0
    return data
