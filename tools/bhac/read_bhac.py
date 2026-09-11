"""Python IO reading BHAC `dataNNNN.dat` binary frames.

This module is only responsible for file IO and static mesh parsing. The first `nw` quantities in the BHAC file are the original
conserved/raw variables; primitive quantities used for radiative transfer on the C++ side require additional metric transformations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import re
import struct
from typing import BinaryIO

import numpy as np


HEADER_TAIL_BYTES = 40
INT = np.dtype("<i4")
FLOAT = np.dtype("<f8")


@dataclass(frozen=True)
class BhacHeader:
    """BHAC file trailer metadata."""

    nleafs: int
    levmax: int
    ndimini: int
    ndir: int
    nw: int
    nws: int
    neqpar: int
    it: int
    time: float
    nx: tuple[int, ...]
    neqpar_values: tuple[float, ...]

    @property
    def cells_per_block(self) -> int:
        """The number of cells in each leaf block."""
        cells = 1
        for value in self.nx:
            cells *= value
        return cells

    @property
    def staggered_cells_per_block(self) -> int:
        """The number of staggered cells in each leaf block."""
        cells = 1
        for value in self.nx:
            cells *= value + 1
        return cells

    @property
    def block_bytes(self) -> int:
        """The number of non-staggered raw variable bytes in a leaf block."""
        return self.cells_per_block * self.nw * FLOAT.itemsize

    @property
    def staggered_block_bytes(self) -> int:
        """The number of staggered raw variable bytes in a leaf block."""
        return self.staggered_cells_per_block * self.nws * FLOAT.itemsize

    @property
    def tree_offset(self) -> int:
        """The starting byte position of the AMR tree structure in the file."""
        return self.nleafs * (self.block_bytes + self.staggered_block_bytes)

    @property
    def active_cells(self) -> int:
        """The number of active cells in all leaf blocks."""
        return self.nleafs * self.cells_per_block


@dataclass(frozen=True)
class GridInfo:
    """Information related to AMR tree parsing in static BHAC mesh files."""

    nxlone: tuple[int, int, int]
    xprobmin: tuple[float, float, float]
    xprobmax: tuple[float, float, float]
    hslope: float


@dataclass(frozen=True)
class BlockInfo:
    """The position of the leaf block in the AMR tree."""

    index: tuple[int, int, int]
    level: int
    lower: tuple[float, float, float] | None = None
    dx: tuple[float, float, float] | None = None
    size: tuple[int, int, int] | None = None


@dataclass(frozen=True)
class BhacGrid:
    """Reusable BHAC static meshes and AMR trees."""

    frame_path: Path
    grid_path: Path
    header: BhacHeader
    info: GridInfo
    blocks: tuple[BlockInfo, ...]
    names: tuple[str, ...]


@dataclass(frozen=True)
class BhacFrame:
    """One frame of BHAC data."""

    path: Path
    header: BhacHeader
    variables: dict[str, np.ndarray]
    data: np.ndarray | None = None
    grid: BhacGrid | None = None


def _read_blocks(path: Path, header: BhacHeader) -> np.ndarray:
    """Read all non-staggered leaf block data in file order."""
    path = Path(path)
    if path.stat().st_size < header.tree_offset:
        raise EOFError(
            f"BHAC block data is shorter than expected in {path}: "
            f"need at least {header.tree_offset} bytes."
        )
    data = np.empty(
        (header.nleafs, header.nw, header.cells_per_block),
        dtype=FLOAT,
        order="C",
    )
    with path.open("rb", buffering=0) as stream:
        for leaf in range(header.nleafs):
            target = memoryview(data[leaf]).cast("B")
            offset = 0
            while offset < target.nbytes:
                count = stream.readinto(target[offset:])
                if count is None or count == 0:
                    raise EOFError(
                        f"Unexpected end of BHAC block data in {path}: "
                        f"leaf {leaf} of {header.nleafs}."
                    )
                offset += count
            stream.seek(header.staggered_block_bytes, 1)
    return data


def _frame_data(
    path: Path,
    header: BhacHeader,
    variables: tuple[int | str, ...] | None,
    names: tuple[str, ...],
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """Read the entire frame and build a view for the selected variables."""
    selected: tuple[int | str, ...]
    selected = tuple(range(header.nw)) if variables is None else variables
    indices = [variable_index(header, variable) for variable in selected]
    values = _read_blocks(path, header)
    data = {}
    for index in indices:
        data[names[index]] = values[:, index, :]
    return data, values


def read_header(path: Path) -> BhacHeader:
    """Only read BHAC frame trailer metadata."""
    path = Path(path)
    with path.open("rb") as stream:
        stream.seek(-HEADER_TAIL_BYTES, 2)
        values = stream.read(HEADER_TAIL_BYTES)
        if len(values) != HEADER_TAIL_BYTES:
            raise ValueError(f"Cannot read BHAC metadata tail: {path}")
        nleafs, levmax, ndimini, ndir, nw, nws, neqpar, it, time = struct.unpack("<8id", values)

        extra_bytes = ndimini * INT.itemsize + neqpar * FLOAT.itemsize
        stream.seek(-(HEADER_TAIL_BYTES + extra_bytes), 2)
        nx = tuple(int(value) for value in np.fromfile(stream, dtype=INT, count=ndimini))
        neqpar_values = tuple(float(value) for value in np.fromfile(stream, dtype=FLOAT, count=neqpar))

    return BhacHeader(
        nleafs=nleafs,
        levmax=levmax,
        ndimini=ndimini,
        ndir=ndir,
        nw=nw,
        nws=nws,
        neqpar=neqpar,
        it=it,
        time=time,
        nx=nx,
        neqpar_values=neqpar_values,
    )


def frame_number(path: Path) -> int:
    """Read frame number from `dataNNNN.dat` filename."""
    match = re.fullmatch(r"data(\d+)", Path(path).stem)
    if match is None:
        raise ValueError(f"Invalid BHAC frame name: {path}")
    return int(match.group(1))


def list_frames(directory: Path) -> list[Path]:
    """List the BHAC frame files in a directory, sorted by frame number."""
    return sorted(Path(directory).glob("data*.dat"), key=frame_number)


def variable_names(nw: int) -> tuple[str, ...]:
    """Generate the names of raw/conserved variables in the current file."""
    base = ["D", "S1", "S2", "S3", "TAU", "B1", "B2", "B3", "DS"]
    names = [base[index] if index < len(base) else f"w{index}" for index in range(nw)]
    if nw >= 10:
        names[-2] = "LFAC"
        names[-1] = "XI"
    return tuple(names)


def variable_index(header: BhacHeader, variable: int | str) -> int:
    """Convert variable name or variable number to array index."""
    if isinstance(variable, int):
        if variable < 0 or variable >= header.nw:
            raise IndexError(f"BHAC variable index out of range: {variable}")
        return variable
    names = variable_names(header.nw)
    try:
        return names.index(variable)
    except ValueError as exc:
        raise KeyError(f"Unknown BHAC variable {variable!r}; available: {', '.join(names)}") from exc


def read_frame(path: Path, variables: tuple[int | str, ...] | None = None) -> BhacFrame:
    """Read a frame of BHAC raw/conserved variables.

    `variables=None` means exposing all non-staggered primitive variables. whole frame press
    `leaf block-variable-cell` files are sequentially read into continuous memory to avoid cross-block seeking on the mechanical disk."""
    path = Path(path)
    header = read_header(path)
    names = variable_names(header.nw)
    data, values = _frame_data(path, header, variables, names)
    return BhacFrame(path=path, header=header, variables=data, data=values)


def load_grid(frame_path: Path, grid_path: Path, *, mks_periodic: bool = True) -> BhacGrid:
    """Read static mesh and AMR leaf block information once for multiple frame reuse."""
    frame_path = Path(frame_path)
    grid_path = Path(grid_path)
    header = read_header(frame_path)
    info = parse_grid(grid_path)
    if mks_periodic:
        info = GridInfo(
            nxlone=info.nxlone,
            xprobmin=(info.xprobmin[0], info.xprobmin[1] * 2.0 * math.pi, info.xprobmin[2] * 2.0 * math.pi),
            xprobmax=(info.xprobmax[0], info.xprobmax[1] * 2.0 * math.pi, info.xprobmax[2] * 2.0 * math.pi),
            hslope=info.hslope,
        )
    blocks = tuple(fill_block_geometry(read_forest(frame_path, info), header, info))
    return BhacGrid(
        frame_path=frame_path,
        grid_path=grid_path,
        header=header,
        info=info,
        blocks=blocks,
        names=variable_names(header.nw),
    )


def validate_header(reference: BhacHeader, current: BhacHeader, path: Path) -> None:
    """Confirm that a frame can reuse an existing grid."""
    checks = (
        reference.nleafs == current.nleafs,
        reference.ndimini == current.ndimini,
        reference.nw == current.nw,
        reference.nws == current.nws,
        reference.neqpar == current.neqpar,
        reference.nx == current.nx,
    )
    if not all(checks):
        raise ValueError(f"BHAC frame metadata changed; cannot reuse grid for {path}")
    if len(reference.neqpar_values) == len(current.neqpar_values):
        for expected, value in zip(reference.neqpar_values, current.neqpar_values):
            scale = 1.0 + abs(expected)
            if abs(value - expected) > 1.0e-12 * scale:
                raise ValueError(f"BHAC equation parameters changed; cannot reuse grid for {path}")


def read_frame_with_grid(
    grid: BhacGrid,
    path: Path,
    variables: tuple[int | str, ...] | None = None,
) -> BhacFrame:
    """Read a frame of raw/conserved data using the read static mesh."""
    path = Path(path)
    header = read_header(path)
    validate_header(grid.header, header, path)
    data, values = _frame_data(path, header, variables, grid.names)
    return BhacFrame(path=path, header=header, variables=data, data=values, grid=grid)


def fill_block_geometry(
    blocks: list[BlockInfo],
    header: BhacHeader,
    grid: GridInfo,
) -> list[BlockInfo]:
    """Supplement the lower left corner and cell size of each AMR leaf block."""
    dx_root = tuple(
        (grid.xprobmax[index] - grid.xprobmin[index]) /
        (grid.nxlone[index] // header.nx[index])
        for index in range(header.ndimini)
    )
    dx_cell = tuple(
        (grid.xprobmax[index] - grid.xprobmin[index]) / grid.nxlone[index]
        for index in range(header.ndimini)
    )
    filled = []
    size = tuple(header.nx[index] for index in range(header.ndimini))
    for block in blocks:
        factor = 2.0 ** (block.level - 1)
        lower = tuple(
            grid.xprobmin[index] + block.index[index] * dx_root[index] / factor
            for index in range(header.ndimini)
        )
        dx = tuple(dx_cell[index] / factor for index in range(header.ndimini))
        filled.append(BlockInfo(index=block.index, level=block.level, lower=lower, dx=dx, size=size))
    return filled


def block_centers(block: BlockInfo) -> np.ndarray:
    """Calculate the center coordinates of all cells in a leaf block, the shape is `(cells, ndim)`."""
    if block.lower is None or block.dx is None or block.size is None:
        raise ValueError("Block geometry has not been filled.")
    axes = [
        block.lower[axis] + (np.arange(block.size[axis], dtype=np.float64) + 0.5) * block.dx[axis]
        for axis in range(len(block.size))
    ]
    mesh = np.meshgrid(*axes, indexing="ij")
    return np.stack([axis.ravel(order="F") for axis in mesh], axis=1)


def cell_centers(grid: BhacGrid) -> np.ndarray:
    """Calculate the center coordinates of all leaf block cells, with the shape of `(nleafs, cells, ndim)`."""
    return np.stack([block_centers(block) for block in grid.blocks], axis=0)


def read_times(paths: list[Path]) -> list[dict[str, float | int | str]]:
    """Read frame numbers and file header times in batches."""
    rows = []
    for path in paths:
        header = read_header(path)
        rows.append({
            "path": str(path),
            "nt": frame_number(path),
            "it": header.it,
            "time": header.time,
        })
    return rows


def parse_grid(path: Path) -> GridInfo:
    """Read the global grid extents in `grid_mks.in`."""
    values: list[float] = []
    with Path(path).open() as stream:
        for line in stream:
            parts = line.split()
            if not parts:
                continue
            try:
                values.append(float(parts[-1]))
            except ValueError:
                continue
    if len(values) < 10:
        raise ValueError(f"Cannot parse BHAC grid file: {path}")
    return GridInfo(
        nxlone=(int(values[0]), int(values[1]), int(values[2])),
        xprobmin=(values[3], values[4], values[5]),
        xprobmax=(values[6], values[7], values[8]),
        hslope=values[9],
    )


def read_forest(path: Path, grid: GridInfo) -> list[BlockInfo]:
    """Read leaf block information in the AMR tree."""
    path = Path(path)
    header = read_header(path)
    ng = tuple(grid.nxlone[index] // header.nx[index] for index in range(header.ndimini))
    blocks: list[BlockInfo] = []
    with path.open("rb") as stream:
        stream.seek(header.tree_offset)
        for k in range(ng[2] if header.ndimini == 3 else 1):
            for j in range(ng[1]):
                for i in range(ng[0]):
                    _read_node(stream, header.ndimini, 1, i, j, k, blocks)
    if len(blocks) != header.nleafs:
        raise ValueError(f"AMR tree leaf count mismatch in {path}: {len(blocks)} != {header.nleafs}")
    return blocks


def _read_node(
    stream: BinaryIO,
    ndim: int,
    level: int,
    i: int,
    j: int,
    k: int,
    blocks: list[BlockInfo],
) -> None:
    raw = stream.read(INT.itemsize)
    if len(raw) != INT.itemsize:
        raise EOFError("Unexpected end of BHAC AMR tree.")
    leaf = struct.unpack("<i", raw)[0]
    if leaf:
        blocks.append(BlockInfo(index=(i, j, k), level=level))
        return
    for child in range(2 ** ndim):
        if ndim == 2:
            child_i = 2 * i + child % 2
            child_j = 2 * j + child // 2
            child_k = 0
        else:
            child_i = 2 * i + child % 2
            child_j = 2 * j + (child // 2) % 2
            child_k = 2 * k + child // 4
        _read_node(stream, ndim, level + 1, child_i, child_j, child_k, blocks)
