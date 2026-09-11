"""Verification of temporal linear interpolation errors for GRMHD primitive and fast-light I/Q/U/V images."""

from __future__ import annotations

import math
import hashlib
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from typing import TypeVar

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

if __package__:
    from .bhac.c2p import (
        MagneticGeometry,
        PrimitiveGeometry,
        comoving_b,
        magnetic_geometry,
        primitive_geometry,
        radius_mks,
        to_primitives,
        volume_centers,
    )
    from .bhac.read_bhac import (
        BhacGrid,
        list_frames,
        load_grid,
        read_frame_with_grid,
        read_header,
    )
    from .lib.data import (
        Result,
        find_frames,
        load_csv_map,
        read_key_values,
        read_rows,
        result_from_config,
        stokes_path,
        write_rows,
    )
    from .lib.image_error import image_error, temporal_mean_std
    from .lib.save_fig import save_figure
else:
    from bhac.c2p import (
        MagneticGeometry,
        PrimitiveGeometry,
        comoving_b,
        magnetic_geometry,
        primitive_geometry,
        radius_mks,
        to_primitives,
        volume_centers,
    )
    from bhac.read_bhac import (
        BhacGrid,
        list_frames,
        load_grid,
        read_frame_with_grid,
        read_header,
    )
    from lib.data import (
        Result,
        find_frames,
        load_csv_map,
        read_key_values,
        read_rows,
        result_from_config,
        stokes_path,
        write_rows,
    )
    from lib.image_error import image_error, temporal_mean_std
    from lib.save_fig import save_figure


PRIMITIVE_CSV = "b_interp.csv"
OBSERVATION_CSV = "obs_interp.csv"
OBSERVATION_FRAME_CSV = "obs_interp_t.csv"
PRIM_INPUTS = ("D", "S1", "S2", "S3", "B1", "B2", "B3", "DS", "LFAC", "XI")
STOKES = ("I", "Q", "U", "V")

PRIMITIVE_FIELDS = [
    "dt",  # Reserved frame time interval in rg/c.
    "dt0",  # Raw BHAC frame interval in rg/c.
    "r0",  # Radial shell inner boundary, unit rg.
    "r1",  # Radial shell outer boundary, unit rg.
    "nseg",  # The number of endpoint segments participating in statistics.
    "nmid",  # The actual number of intermediate frames involved in statistics.
    "ncell",  # The cumulative number of cells participating in statistics.
    "w",  # The cumulative weight of the magnetic field strength of the real intermediate frame co-moving system.
    "e",  # The cumulative absolute error of linear interpolation co-moving system magnetic field intensity.
    "db",  # Linear interpolation is the accumulated signed difference between the magnetic field intensity of the co-moving system and the real value.
    "l1",  # The relative L1 error of the magnetic field strength of the linearly interpolated co-moving system is equal to e/w.
    "bias",  # The relative signed deviation of the magnetic field strength of a linearly interpolated co-moving system, equal to db/w.
    "weak",  # The amount of systematic weakening, equal to -bias; a positive value means that the magnetic field becomes weaker after interpolation.
]

OBSERVATION_FIELDS = [
    "dt", "dt0", "stride", "nseg", "nmid", "npix",
    "I_l1", "Q_l1", "U_l1", "V_l1",
    "I_l1_std", "Q_l1_std", "U_l1_std", "V_l1_std",
]

OBSERVATION_FRAME_FIELDS = [
    "dt", "dt0", "stride", "left_frame", "right_frame", "frame",
    "time_rg_over_c", "npix", "I_l1", "Q_l1", "U_l1", "V_l1",
]

TICK_SIZE = 14
LABEL_SIZE = 16
LEGEND_SIZE = 13

Item = TypeVar("Item")
Value = TypeVar("Value")


def configure_parameters() -> dict[str, object]:
    """Centrally set two types of time interpolation error verification parameters."""
    root = Path(r"D:/CoportSL-data")
    run = "output0001"  # Fast light run for verification of observational time interpolation.
    interp_err = root / "result" / "interp_err"
    primitive_output = interp_err / "b_interp"
    observation_output = interp_err / "obs_interp"
    return {
        "dt": (0.2, 0.5, 1.0, 2.0, 4.0, 8.0),  # The retention time interval to be tested in rg/c.
        "load_workers": 1,  # Number of BHAC frame loading threads; mechanical disks use serial reading.
        "workers": 16,  # Memory array conversion and error statistics thread number.
        "formats": ("png", "pdf"),
        "primitive_input": root / "output-0.1M",  # BHAC input frame directory.
        "grid": root / "grid_mks.in",  # BHAC static mesh file.
        "primitive_output": primitive_output,  # b_interp run directory category.
        "shells": ((0.0, 20.0), (20.0, 30.0), (30.0, 50.0), (50.0, 80.0), (80.0, 100.0), (100.0, 200.0)),
        "blocks": None,  # The maximum number of least common multiple blocks to take; None means all.
        "radial_log": True,  # Whether the radial contribution plot uses a logarithmic vertical axis.
        "observation_input": root / "result" / "fast" / run,
        "observation_output": observation_output,  # obs_interp run directory category.
        "nt0": None,  # Temporarily overwrite the starting frame; None means use config.txt.
        "nt1": None,  # Temporarily overwrites the end frame; None means use config.txt.
    }


def read_primitive_errors(input_dir: Path) -> list[dict[str, str]]:
    """Read time interpolation error CSV."""
    path = input_dir / PRIMITIVE_CSV
    if not path.is_file():
        raise FileNotFoundError(f"Missing time interpolation CSV: {path}")
    return read_rows(path)


def file_sha256(path: Path) -> str:
    """Streamingly computes SHA-256 of an input file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def primitive_input_signature(input_dir: Path, grid_path: Path) -> str:
    frames = list_frames(input_dir)
    if not frames:
        raise FileNotFoundError(f"No BHAC frames found in {input_dir}")
    if not grid_path.is_file():
        raise FileNotFoundError(f"Missing BHAC grid: {grid_path}")
    digest = hashlib.sha256()
    digest.update(bytes.fromhex(file_sha256(grid_path)))
    digest.update(bytes.fromhex(file_sha256(frames[0])))
    for frame in frames:
        digest.update(frame.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(float(read_header(frame).time).hex().encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def observation_input_signature(input_dir: Path) -> str:
    config = input_dir / "config.txt"
    values = read_key_values(config)
    signature = values.get("model_signature")
    if signature is None:
        raise KeyError(f"Missing model_signature in {config}")
    frames = find_frames(input_dir, None, None, required="IQUV")
    if not frames:
        raise FileNotFoundError(f"No Stokes frames found in {input_dir}")
    digest = hashlib.sha256()
    digest.update(signature.encode("ascii"))
    for frame in frames:
        digest.update(str(frame).encode("ascii"))
        digest.update(b"\0")
    for stokes in STOKES:
        digest.update(bytes.fromhex(file_sha256(
            stokes_path(input_dir, stokes, frames[0]))))
    return digest.hexdigest()


_PATH_KEYS = ("data", "grid", "output", "analysis")


def allocate_run_directory(category: Path) -> Path:
    """Create the next outputNNNN directory under category and write the running status."""
    category.mkdir(parents=True, exist_ok=True)
    maximum = 0
    for entry in category.iterdir():
        if not entry.is_dir():
            continue
        name = entry.name
        if name.startswith("output") and name[6:].isdigit():
            maximum = max(maximum, int(name[6:]))
    number = maximum + 1
    while True:
        run = category / f"output{number:04d}"
        try:
            run.mkdir()
            write_run_status(run, "running")
            return run
        except FileExistsError:
            number += 1


def write_run_status(
    run: Path,
    status: str,
    nt0: int | None = None,
    nt1: int | None = None,
) -> None:
    """Append a status record to status.txt."""
    line = status
    if nt0 is not None and nt1 is not None:
        line += f" nt0={nt0} nt1={nt1}"
    with (run / "status.txt").open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def write_run_paths(
    run: Path,
    *,
    data: Path,
    grid: Path | None,
    output: Path,
) -> None:
    """Write the path block of status.txt and retain the existing status records."""
    records = []
    status = run / "status.txt"
    if status.is_file():
        for line in status.read_text(encoding="utf-8").splitlines():
            if not line or line.split("=", 1)[0] in _PATH_KEYS:
                continue
            records.append(line)
    grid_text = "" if grid is None else str(grid)
    text = f"data={data}\ngrid={grid_text}\noutput={output}\n"
    if records:
        text += "\n".join(records) + "\n"
    status.write_text(text, encoding="utf-8")


def find_reusable_run(
    category: Path,
    config_values: dict[str, str],
    required_files: dict[str, list[str]],
    validator: Callable[[Path], bool] | None = None,
) -> Path | None:
    """Find reusable runs by config identity with CSV header/data row inspection."""
    if not category.is_dir():
        return None
    runs = sorted(
        (entry for entry in category.iterdir()
         if entry.is_dir() and entry.name.startswith("output")),
        key=lambda entry: entry.name,
        reverse=True,
    )
    for run in runs:
        config = run / "config.txt"
        if not config.is_file():
            continue
        values = read_key_values(config)
        if any(values.get(key) != value for key, value in config_values.items()):
            continue
        if (
            all(csv_complete(run / name, fields)
                for name, fields in required_files.items()) and
            (validator is None or validator(run))
        ):
            return run
    return None


def csv_complete(path: Path, fields: list[str]) -> bool:
    if not path.is_file():
        return False
    try:
        rows = read_rows(path)
    except (OSError, ValueError):
        return False
    return bool(rows) and list(rows[0]) == fields and all(list(row) == fields for row in rows)


def finite_row(row: dict[str, str], fields: list[str]) -> bool:
    try:
        return all(math.isfinite(float(row[field])) for field in fields)
    except (KeyError, ValueError):
        return False


def primitive_result_complete(
    run: Path,
    cases: list[tuple[float, int]],
    shells: tuple[tuple[float, float], ...],
) -> bool:
    """Verify that the primitive summary covers exactly all dt and radial shell combinations."""
    try:
        rows = read_rows(run / PRIMITIVE_CSV)
    except (OSError, ValueError):
        return False
    if not all(finite_row(row, PRIMITIVE_FIELDS) for row in rows):
        return False
    expected = {
        (float(dt), float(r0), float(r1))
        for dt, _ in cases
        for r0, r1 in shells
    }
    actual = [(float(row["dt"]), float(row["r0"]), float(row["r1"])) for row in rows]
    return len(actual) == len(set(actual)) and set(actual) == expected


def expected_observation_rows(
    frames: list[int],
    cases: list[tuple[float, int]],
) -> tuple[set[float], set[tuple[float, int, int, int]]]:
    summary = {float(dt) for dt, _ in cases}
    detail = set()
    for dt, stride in cases:
        for left_index in range(0, len(frames) - stride, stride):
            right_index = left_index + stride
            for target_index in range(left_index + 1, right_index):
                detail.add((
                    float(dt), frames[left_index], frames[right_index],
                    frames[target_index]))
    return summary, detail


def observation_result_complete(
    run: Path,
    frames: list[int],
    cases: list[tuple[float, int]],
) -> bool:
    """Verify that the observation summary and frame-by-frame table cover exactly all expected interpolation combinations."""
    try:
        rows = read_rows(run / OBSERVATION_CSV)
        frame_rows = read_rows(run / OBSERVATION_FRAME_CSV)
    except (OSError, ValueError):
        return False
    if (
        not all(finite_row(row, OBSERVATION_FIELDS) for row in rows) or
        not all(finite_row(row, OBSERVATION_FRAME_FIELDS) for row in frame_rows)
    ):
        return False
    expected, expected_frames = expected_observation_rows(frames, cases)
    actual = [float(row["dt"]) for row in rows]
    actual_frames = [
        (float(row["dt"]), int(row["left_frame"]),
         int(row["right_frame"]), int(row["frame"]))
        for row in frame_rows
    ]
    return (
        len(actual) == len(set(actual)) and set(actual) == expected and
        len(actual_frames) == len(set(actual_frames)) and
        set(actual_frames) == expected_frames
    )


def latest_complete_run(category: Path, required: dict[str, list[str]]) -> Path:
    """Returns the latest and complete CSV structure of the running directory under the category."""
    if not category.is_dir():
        raise FileNotFoundError(f"Missing run category: {category}")
    runs = sorted(
        (entry for entry in category.iterdir()
         if entry.is_dir() and entry.name.startswith("output")),
        key=lambda entry: entry.name,
        reverse=True,
    )
    for run in runs:
        if all(csv_complete(run / name, fields) for name, fields in required.items()):
            return run
    raise FileNotFoundError(f"No complete run under {category}")


def write_config(run: Path, config_values: dict[str, str]) -> None:
    """Write config.txt in the interp_err running directory."""
    text = "".join(f"{key}={value}\n" for key, value in config_values.items())
    (run / "config.txt").write_text(text, encoding="utf-8")


class ShellAccumulator:
    """Accumulate time interpolation errors in a radial shell."""

    def __init__(self, mask: np.ndarray) -> None:
        self.mask = mask
        self.segments: set[int] = set()
        self.targets = 0
        self.cells = 0
        self.w = 0.0
        self.e = 0.0
        self.db = 0.0

    def add(
        self,
        *,
        segment: int,
        b_true: np.ndarray,
        b_linear: np.ndarray,
    ) -> None:
        mask = self.mask
        if not np.any(mask):
            return
        true = b_true[mask]
        linear = b_linear[mask]
        valid = np.isfinite(true) & np.isfinite(linear)
        valid &= true > 0.0
        if not np.any(valid):
            return
        true = true[valid]
        linear = linear[valid]

        self.segments.add(segment)
        self.targets += 1
        self.cells += int(true.size)
        self.w += float(np.sum(true))
        self.e += float(np.sum(np.abs(linear - true)))
        self.db += float(np.sum(linear - true))

    def merge(self, other: "ShellAccumulator") -> None:
        """Combine statistics from another totalizer in the same shell."""
        self.segments.update(other.segments)
        self.targets += other.targets
        self.cells += other.cells
        self.w += other.w
        self.e += other.e
        self.db += other.db

    def row(self, *, dt: float, dt0: float, shell: tuple[float, float]) -> dict[str, float | int]:
        r0, r1 = shell
        if self.cells == 0 or self.w == 0.0:
            nan = float("nan")
            return {
                "dt": dt,
                "dt0": dt0,
                "r0": r0,
                "r1": r1,
                "nseg": len(self.segments),
                "nmid": self.targets,
                "ncell": self.cells,
                "w": 0.0,
                "e": 0.0,
                "db": 0.0,
                "l1": nan,
                "bias": nan,
                "weak": nan,
            }
        return {
            "dt": dt,
            "dt0": dt0,
            "r0": r0,
            "r1": r1,
            "nseg": len(self.segments),
            "nmid": self.targets,
            "ncell": self.cells,
            "w": self.w,
            "e": self.e,
            "db": self.db,
            "l1": self.e / self.w,
            "bias": self.db / self.w,
            "weak": -self.db / self.w,
        }


def thread_map(
    function: Callable[[Item], Value],
    items: Iterable[Item],
    workers: int,
) -> list[Value]:
    """Execute lightweight reading and conversion tasks serially or multi-threaded in input order."""
    values = list(items)
    if workers < 1:
        raise ValueError("workers must be at least 1.")
    if workers == 1 or len(values) < 2:
        return [function(item) for item in values]
    with ThreadPoolExecutor(max_workers=min(workers, len(values))) as executor:
        return list(executor.map(function, values))


def linear_interpolate(left: np.ndarray, right: np.ndarray, weight: float) -> np.ndarray:
    """Interpolates at linear time weights `weight`, with 0 and 1 corresponding to the left and right endpoints respectively."""
    if not np.isfinite(weight) or weight < 0.0 or weight > 1.0:
        raise ValueError(f"Interpolation weight must lie in [0, 1], got {weight}.")
    return (1.0 - weight) * left + weight * right


def dt0_from_times(times: np.ndarray) -> float:
    """The original sequence time intervals are estimated and temporal monotonicity is checked."""
    delta = np.diff(times)
    if np.any(delta <= 0.0):
        raise ValueError("BHAC frame times must be strictly increasing.")
    return float(np.median(delta))


def interval_cases(dts: Iterable[float], dt0: float) -> list[tuple[float, int]]:
    """Convert the time interval under test to an integer step size of the original frame."""
    if not np.isfinite(dt0) or dt0 <= 0.0:
        raise ValueError(f"dt0 must be finite and positive, got {dt0}.")
    cases = []
    for dt in dts:
        requested = float(dt)
        stride = int(round(requested / dt0))
        actual = stride * dt0
        if stride < 2:
            print(f"Skip dt={requested:g}: stride < 2")
            continue
        if abs(actual - requested) > 1.0e-6 * max(1.0, abs(requested)):
            raise ValueError(f"dt={requested:g} is not an integer multiple of dt0={dt0:g}")
        cases.append((actual, stride))
    if not cases:
        raise ValueError("No valid dt remains; each dt must span at least two source frames.")
    return cases


def primitive_cache(
    *,
    grid: BhacGrid,
    frames: list[Path],
    indices: list[int],
    coords: np.ndarray,
    geom: PrimitiveGeometry,
    workers: int,
) -> dict[int, np.ndarray]:
    """Read BHAC frames in a time block in parallel and cache them as primitive arrays."""
    load = partial(
        load_primitive,
        grid=grid,
        frames=frames,
        coords=coords,
        geom=geom,
    )
    return dict(thread_map(load, indices, workers))


def load_primitive(
    index: int,
    *,
    grid: BhacGrid,
    frames: list[Path],
    coords: np.ndarray,
    geom: PrimitiveGeometry,
) -> tuple[int, np.ndarray]:
    """Read and convert a frame of BHAC primitive data."""
    path = frames[index]
    frame = read_frame_with_grid(grid, path, variables=PRIM_INPUTS)
    primitive = to_primitives(frame, coords=coords, geom=geom)
    if primitive.data is None:
        raise ValueError(f"Primitive conversion failed for {path}")
    return index, primitive.data.astype(np.float32)


def magnetic_cache(
    *,
    cache: dict[int, np.ndarray],
    geom: MagneticGeometry,
    workers: int,
) -> dict[int, np.ndarray]:
    """Parallel cache of co-moving magnetic field strengths of real frames."""
    indices = sorted(cache)
    load = partial(load_magnetic_strength, cache=cache, geom=geom)
    return dict(thread_map(load, indices, workers))


def load_magnetic_strength(
    index: int,
    *,
    cache: dict[int, np.ndarray],
    geom: MagneticGeometry,
) -> tuple[int, np.ndarray]:
    """Calculate the magnetic field strength of the co-moving system for one frame from the primitive buffer."""
    return index, comoving_b(cache[index], geom=geom).astype(np.float32)


def compare_task(
    *,
    task: tuple[float, int, int, int, list[int]],
    cache: dict[int, np.ndarray],
    bcache: dict[int, np.ndarray],
    masks: dict[tuple[float, float], np.ndarray],
    times: np.ndarray,
    geom: MagneticGeometry,
) -> tuple[float, dict[tuple[float, float], ShellAccumulator]]:
    """Calculate the interpolation error of all true intermediate frames within an endpoint segment."""
    dt, segment_index, left_index, right_index, targets = task
    left = cache[left_index]
    right = cache[right_index]
    local = {shell: ShellAccumulator(mask) for shell, mask in masks.items()}
    span = times[right_index] - times[left_index]

    for target_index in targets:
        weight = float((times[target_index] - times[left_index]) / span)
        linear = linear_interpolate(left, right, weight)
        b_true = bcache[target_index]
        b_linear = comoving_b(linear, geom=geom)
        for shell, accumulator in local.items():
            accumulator.add(
                segment=segment_index,
                b_true=b_true,
                b_linear=b_linear,
            )
    return dt, local


def compare_block(
    *,
    tasks: list[tuple[float, int, int, int, list[int]]],
    cache: dict[int, np.ndarray],
    bcache: dict[int, np.ndarray],
    masks: dict[tuple[float, float], np.ndarray],
    times: np.ndarray,
    geom: MagneticGeometry,
    workers: int,
) -> list[tuple[float, dict[tuple[float, float], ShellAccumulator]]]:
    """Compute all interpolation errors in a least common multiple time block in parallel."""
    if workers == 1 or len(tasks) < 2:
        return [
            compare_task(
                task=task,
                cache=cache,
                bcache=bcache,
                masks=masks,
                times=times,
                geom=geom,
            )
            for task in tasks
        ]

    nworker = min(workers, len(tasks))
    with ThreadPoolExecutor(max_workers=nworker) as executor:
        futures = [
            executor.submit(
                compare_task,
                task=task,
                cache=cache,
                bcache=bcache,
                masks=masks,
                times=times,
                geom=geom,
            )
            for task in tasks
        ]
        return [future.result() for future in futures]


def calculate_primitive_errors(
    *,
    input_dir: Path,
    grid_path: Path,
    output_dir: Path,
    dts: Iterable[float],
    shells: tuple[tuple[float, float], ...],
    nb: int | None,
    load_workers: int,
    workers: int,
) -> list[dict[str, float | int]]:
    """Calculate the primitive interpolation error under different retention time intervals."""
    frames = list_frames(input_dir)
    if len(frames) < 3:
        raise FileNotFoundError(f"Need at least 3 BHAC frames in {input_dir}")
    grid = load_grid(frames[0], grid_path)
    spin = grid.header.neqpar_values[3]
    hslope = grid.info.hslope
    coords = volume_centers(grid, spin=spin, hslope=hslope)
    pgeom = primitive_geometry(coords, spin=spin, hslope=hslope)
    bgeom = magnetic_geometry(coords, spin=spin, hslope=hslope)
    radius = radius_mks(coords)
    masks = {
        shell: (radius >= shell[0]) & (radius < shell[1])
        for shell in shells
    }
    times = np.array([read_header(path).time for path in frames], dtype=np.float64)
    dt0 = dt0_from_times(times)

    cases = interval_cases(dts, dt0)
    strides = [stride for _, stride in cases]
    accumulators_by_dt = {}
    manifest = [
        f"input={input_dir}",
        f"grid={grid_path}",
        f"frames={len(frames)}",
        f"dt0={dt0:.12g}",
        "xbar=True",
        f"nb={nb}",
        f"load_workers={load_workers}",
        f"workers={workers}",
        "geometry_cache=True",
        "cache_dtype=float32",
    ]

    for dt, stride in cases:
        accumulators_by_dt[dt] = {shell: ShellAccumulator(masks[shell]) for shell in shells}
        manifest.append(f"dt={dt:.12g} stride={stride}")
    block = math.lcm(*strides)
    manifest.append(f"block={block}")
    block_starts = list(range(0, len(frames) - block, block))
    if not block_starts:
        block_starts = [0]
    if nb is not None and len(block_starts) > nb:
        indices = np.linspace(0, len(block_starts) - 1, nb, dtype=int)
        block_starts = [block_starts[index] for index in indices]
    manifest.append(f"blocks={len(block_starts)}")

    by_block: dict[int, list[tuple[float, int, int, int, list[int]]]] = {}
    for block_start in block_starts:
        block_end = min(block_start + block, len(frames) - 1)
        for dt, stride in cases:
            starts = list(range(block_start, block_end - stride + 1, stride))
            print(
                f"dt={dt:g} rg/c block={block_start}..{block_end} "
                f"stride={stride} nseg={len(starts)}"
            )
            for left_index in starts:
                right_index = left_index + stride
                targets = list(range(left_index + 1, right_index))
                by_block.setdefault(block_start, []).append(
                    (dt, left_index, left_index, right_index, targets)
                )

    for block_start, block_tasks in sorted(by_block.items()):
        needed = sorted({
            index
            for _, _, left_index, right_index, targets in block_tasks
            for index in (left_index, right_index, *targets)
        })
        print(
            f"cache block {block_start}..{min(block_start + block, len(frames) - 1)} "
            f"frames={len(needed)} workers={min(load_workers, len(needed))}"
        )
        cache = primitive_cache(
            grid=grid,
            frames=frames,
            indices=needed,
            coords=coords,
            geom=pgeom,
            workers=load_workers,
        )
        print(f"magnetic cache frames={len(cache)} workers={min(workers, len(cache))}")
        bcache = magnetic_cache(
            cache=cache,
            geom=bgeom,
            workers=workers,
        )
        print(f"compare tasks={len(block_tasks)} workers={min(workers, len(block_tasks))}")
        for dt, shell_stats in compare_block(
            tasks=block_tasks,
            cache=cache,
            bcache=bcache,
            masks=masks,
            times=times,
            geom=bgeom,
            workers=workers,
        ):
            for shell, accumulator in shell_stats.items():
                accumulators_by_dt[dt][shell].merge(accumulator)

    rows: list[dict[str, float | int]] = []
    for dt in sorted(accumulators_by_dt):
        for shell, accumulator in accumulators_by_dt[dt].items():
            rows.append(accumulator.row(dt=dt, dt0=dt0, shell=shell))

    csv_path = write_rows(
        output_dir / PRIMITIVE_CSV,
        [{field: row[field] for field in PRIMITIVE_FIELDS} for row in rows],
    )
    print(f"Wrote {csv_path}")
    manifest_path = output_dir / "manifest.txt"
    manifest_path.write_text("\n".join(manifest) + "\n", encoding="utf-8")
    print(f"Wrote {manifest_path}")
    return rows


def _close_value(left: float, right: float) -> bool:
    """Only minimal relative differences caused by rounding of floating point text are incorporated."""
    return math.isclose(left, right, rel_tol=1.0e-11, abs_tol=0.0)


def _unique_close(values: Iterable[float]) -> list[float]:
    """Sorts and merges values that are repeated only within double precision rounding tolerance."""
    result: list[float] = []
    for value in sorted(values):
        if not result or not _close_value(value, result[-1]):
            result.append(value)
    return result


def print_primitive_errors(input_dir: Path) -> None:
    """Prints the overall error for each time interval for quick checking of results."""
    rows = read_primitive_errors(input_dir)
    by_dt: dict[float, list[dict[str, str]]] = {}
    for row in rows:
        by_dt.setdefault(float(row["dt"]), []).append(row)

    for dt, items in sorted(by_dt.items()):
        w = sum(float(row["w"]) for row in items)
        e = sum(float(row["e"]) for row in items)
        db = sum(float(row["db"]) for row in items)
        print(
            f"dt={dt:g} rg/c "
            f"l1={e / w:.6e} "
            f"weak={-db / w:.6e}"
        )


def plot_primitive_errors(
    *,
    input_dir: Path,
    output: Path,
    formats: tuple[str, ...],
    radial_log: bool = False,
) -> list[Path]:
    """Plot the overall time convergence and radius contribution."""
    rows = read_primitive_errors(input_dir)
    dt_values = sorted({float(row["dt"]) for row in rows})
    shells = sorted({
        (float(row["r0"]), float(row["r1"]))
        for row in rows
    })

    l1 = []
    weak = []
    for dt in dt_values:
        items = [row for row in rows if float(row["dt"]) == dt]
        w = sum(float(row["w"]) for row in items)
        e = sum(float(row["e"]) for row in items)
        db = sum(float(row["db"]) for row in items)
        l1.append(100.0 * e / w)
        weak.append(-100.0 * db / w)

    figure, axis = plt.subplots(figsize=(6.4, 4.2), constrained_layout=True)
    axis_right = axis.twinx()
    line_l1 = axis.plot(dt_values, l1, marker="o", label=r"$\epsilon_{L1}$")
    line_weak = axis_right.plot(
        dt_values,
        weak,
        marker="s",
        linestyle="--",
        color="tab:orange",
        label=r"$-\Delta b/b$",
    )
    axis_right.axhline(0.0, color="0.35", linewidth=0.8, linestyle=":")
    axis.set_xticks(dt_values)
    axis.set_xticklabels([f"{dt:g}" for dt in dt_values], rotation=60, ha="right")
    axis.set_xlabel(r"$\Delta t\ [r_{\mathrm{g}}/c]$", fontsize=LABEL_SIZE)
    axis.set_ylabel(r"$\epsilon_{L1}\ [\%]$", fontsize=LABEL_SIZE)
    axis_right.set_ylabel(r"$-\Delta b/b\ [\%]$", fontsize=LABEL_SIZE)
    axis.tick_params(axis="both", which="major", labelsize=TICK_SIZE)
    axis_right.tick_params(axis="y", which="major", labelsize=TICK_SIZE)
    axis.grid(alpha=0.25)
    lines = line_l1 + line_weak
    axis.legend(lines, [line.get_label() for line in lines], fontsize=LEGEND_SIZE)
    paths = save_figure(figure, output.with_name("error_dt"), formats, dpi=220)
    plt.close(figure)
    for path in paths:
        print(f"Wrote {path}")

    shell_labels = [f"{r0:g}-{r1:g}" for r0, r1 in shells]
    index = np.arange(len(shells), dtype=float)
    figure, axis = plt.subplots(figsize=(8.4, 4.5), constrained_layout=True)
    axis_right = axis.twinx()
    colors = plt.get_cmap("tab10")(np.linspace(0.0, 1.0, max(1, len(dt_values))))
    bar_width = 0.82 / max(1, 2 * len(dt_values))
    weak_all = []
    l1_bars = []
    weak_bars = []
    labels = []
    for i, dt in enumerate(dt_values):
        offset = -0.41 + (2 * i + 0.5) * bar_width
        label = rf"$\Delta t={dt:g}$"
        items = [row for row in rows if float(row["dt"]) == dt]
        e_total = sum(float(row["e"]) for row in items)
        weak_total = sum(-float(row["db"]) for row in items)
        l1_contrib = []
        weak_contrib = []
        for r0, r1 in shells:
            selected = [
                row for row in items
                if float(row["r0"]) == r0 and float(row["r1"]) == r1
            ]
            e = sum(float(row["e"]) for row in selected)
            db = sum(float(row["db"]) for row in selected)
            l1_contrib.append(100.0 * e / e_total if e_total > 0.0 else float("nan"))
            weak_contrib.append(100.0 * (-db) / weak_total if weak_total != 0.0 else float("nan"))
        weak_all.extend(weak_contrib)
        l1_bar = axis.bar(
            index + offset,
            l1_contrib,
            width=bar_width,
            color=colors[i],
        )
        weak_bar = axis_right.bar(
            index + offset + bar_width,
            weak_contrib,
            width=bar_width,
            color=colors[i],
            alpha=0.35,
            hatch="//",
            edgecolor=colors[i],
        )
        l1_bars.append(l1_bar)
        weak_bars.append(weak_bar)
        labels.append(label)
    axis_right.axhline(0.0, color="0.35", linewidth=0.8, linestyle=":")
    axis.set_xticks(index)
    axis.set_xticklabels(shell_labels, rotation=25, ha="right")
    axis.set_xlabel(r"$r\ [r_{\mathrm{g}}]$", fontsize=LABEL_SIZE)
    axis.set_ylabel(r"$C_{L1,r}\ [\%]$", fontsize=LABEL_SIZE)
    axis_right.set_ylabel(r"$C_{\rm weak,r}\ [\%]$", fontsize=LABEL_SIZE)
    axis.tick_params(axis="both", which="major", labelsize=TICK_SIZE)
    axis_right.tick_params(axis="y", which="major", labelsize=TICK_SIZE)
    axis.grid(alpha=0.25, axis="y")
    if radial_log:
        axis.set_yscale("log")
        if weak_all and all(value > 0.0 for value in weak_all):
            axis_right.set_yscale("log")
        else:
            axis_right.set_yscale("symlog", linthresh=1.0e-3)
    legend_l1 = axis.legend(
        l1_bars,
        labels,
        fontsize=LEGEND_SIZE,
        ncols=2,
        title=r"$C_{L1,r}$",
        title_fontsize=LEGEND_SIZE,
        loc="upper right",
    )
    axis.add_artist(legend_l1)
    axis_right.legend(
        weak_bars,
        labels,
        fontsize=LEGEND_SIZE,
        ncols=2,
        title=r"$C_{\rm weak,r}$",
        title_fontsize=LEGEND_SIZE,
        loc="center right",
    )
    paths.extend(save_figure(figure, output.with_name("error_r"), formats, dpi=220))
    plt.close(figure)
    for path in paths:
        if path.stem == "error_r":
            print(f"Wrote {path}")
    return paths


class ImageErrorAccumulator:
    """Accumulate frame-by-frame I/Q/U/V image errors for a retention time interval."""

    def __init__(self) -> None:
        self.segments: set[int] = set()
        self.targets = 0
        self.pixels = 0
        self.errors: list[np.ndarray] = []

    def add(
        self,
        *,
        segment: int,
        true: np.ndarray,
        linear: np.ndarray,
    ) -> np.ndarray:
        self.segments.add(segment)
        self.targets += 1
        self.pixels += int(true.shape[-2] * true.shape[-1])
        error = image_error(linear, true)
        self.errors.append(error)
        return error

    def row(
        self,
        *,
        dt: float,
        dt0: float,
        stride: int,
    ) -> dict[str, float | int]:
        if not self.errors:
            raise ValueError(
                f"No target frame is available for dt={dt:g} rg/c.")
        mean, std = temporal_mean_std(np.stack(self.errors))
        return {
            "dt": dt,
            "dt0": dt0,
            "stride": stride,
            "nseg": len(self.segments),
            "nmid": self.targets,
            "npix": self.pixels,
            "I_l1": float(mean[0]),
            "Q_l1": float(mean[1]),
            "U_l1": float(mean[2]),
            "V_l1": float(mean[3]),
            "I_l1_std": float(std[0]),
            "Q_l1_std": float(std[1]),
            "U_l1_std": float(std[2]),
            "V_l1_std": float(std[3]),
        }


def observation_frames(
    result: Result,
    nt_start: int | None,
    nt_end: int | None,
) -> list[int]:
    """Read the serial fast light frame numbers involved in the analysis."""
    start = result.nt0 if nt_start is None else nt_start
    end = result.nt1 if nt_end is None else nt_end
    frames = find_frames(result.path, start, end)
    if len(frames) < 3:
        raise FileNotFoundError(f"Need at least 3 fast-light frames in {result.path}")
    if any(right - left != 1 for left, right in zip(frames, frames[1:])):
        raise ValueError("Fast-light frame numbers must be consecutive for time interpolation analysis.")
    return frames


def load_stokes_frame(result_dir: Path, nt: int) -> np.ndarray:
    """Read a complete frame of I/Q/U/V image and return a float32 array with shape `(4, ny, nx)`."""
    maps = []
    for stokes in STOKES:
        path = stokes_path(result_dir, stokes, nt)
        if not path.is_file():
            raise FileNotFoundError(f"Missing Stokes file: {path}")
        maps.append(load_csv_map(path).astype(np.float32))
    return np.stack(maps, axis=0)


def load_stokes_cube(*, result: Result, frames: list[int], workers: int) -> np.ndarray:
    """Read all flash frames into memory in parallel."""
    first = load_stokes_frame(result.path, frames[0])
    cube = np.empty((len(frames), *first.shape), dtype=np.float32)
    cube[0] = first

    tasks = enumerate(frames[1:], start=1)
    load = partial(load_indexed_stokes, result_dir=result.path)
    for index, data in thread_map(load, tasks, workers):
        cube[index] = data
    gib = cube.nbytes / 1024**3
    print(
        f"Loaded IQUV cube: frames={cube.shape[0]} "
        f"shape={cube.shape[2:]} memory={gib:.2f} GiB")
    return cube


def load_indexed_stokes(
    item: tuple[int, int],
    *,
    result_dir: Path,
) -> tuple[int, np.ndarray]:
    """Read a frame of Stokes image with cache index."""
    index, nt = item
    return index, load_stokes_frame(result_dir, nt)


def calculate_observation_errors(
    *,
    input_dir: Path,
    output_dir: Path,
    dts: Iterable[float],
    nt_start: int | None,
    nt_end: int | None,
    workers: int,
) -> list[dict[str, float | int]]:
    """Calculate frame-by-frame normalized fast-light image interpolation errors under different retention time intervals."""
    result = result_from_config(input_dir, label="Fast light")
    frames = observation_frames(result, nt_start, nt_end)
    dt0 = result.dt
    cases = interval_cases(dts, dt0)
    cube = load_stokes_cube(result=result, frames=frames, workers=workers)

    rows = []
    frame_rows = []
    for dt, stride in cases:
        accumulator = ImageErrorAccumulator()
        for left_index in range(0, len(frames) - stride, stride):
            right_index = left_index + stride
            left = cube[left_index]
            right = cube[right_index]
            left_time = result.time(frames[left_index], frames[0])
            span = result.time(frames[right_index], frames[0]) - left_time
            for target_index in range(left_index + 1, right_index):
                target_time = result.time(frames[target_index], frames[0])
                weight = (target_time - left_time) / span
                true = cube[target_index]
                linear = linear_interpolate(left, right, weight)
                error = accumulator.add(
                    segment=frames[left_index], true=true, linear=linear)
                frame_rows.append({
                    "dt": dt,
                    "dt0": dt0,
                    "stride": stride,
                    "left_frame": frames[left_index],
                    "right_frame": frames[right_index],
                    "frame": frames[target_index],
                    "time_rg_over_c": target_time,
                    "npix": int(true.shape[-2] * true.shape[-1]),
                    "I_l1": float(error[0]),
                    "Q_l1": float(error[1]),
                    "U_l1": float(error[2]),
                    "V_l1": float(error[3]),
                })
        row = accumulator.row(dt=dt, dt0=dt0, stride=stride)
        rows.append(row)
        print(
            f"dt={dt:g} rg/c nseg={row['nseg']} nmid={row['nmid']} "
            f"I_l1={row['I_l1']:.6e} +/- {row['I_l1_std']:.6e}")

    frame_csv_path = write_rows(
        output_dir / OBSERVATION_FRAME_CSV, frame_rows)
    csv_path = write_rows(output_dir / OBSERVATION_CSV, rows)
    print(f"Wrote {frame_csv_path}")
    print(f"Wrote {csv_path}")
    manifest = [
        f"input={input_dir}",
        f"frames={len(frames)}",
        f"first_frame={frames[0]}",
        f"last_frame={frames[-1]}",
        f"dt0={dt0:.12g}",
        f"workers={workers}",
        "cache_dtype=float32",
    ]
    manifest_path = output_dir / "manifest.txt"
    manifest_path.write_text("\n".join(manifest) + "\n", encoding="utf-8")
    print(f"Wrote {manifest_path}")
    return rows


def read_observation_errors(input_dir: Path) -> list[dict[str, str]]:
    """Read the fast light I/Q/U/V image time interpolation error CSV."""
    path = input_dir / OBSERVATION_CSV
    if not path.is_file():
        raise FileNotFoundError(f"Missing observable interpolation CSV: {path}")
    return read_rows(path)


def plot_observation_errors(
    *,
    input_dir: Path,
    output_dir: Path,
    formats: tuple[str, ...],
) -> list[Path]:
    """Plot I/Q/U/V image interpolation error."""
    rows = read_observation_errors(input_dir)
    dt = np.array([float(row["dt"]) for row in rows])
    figure, axis = plt.subplots(figsize=(6.6, 4.2), constrained_layout=True)
    for name, label in zip(STOKES, (r"$I$", r"$Q$", r"$U$", r"$V$")):
        error = 100.0 * np.array([float(row[f"{name}_l1"]) for row in rows])
        std = 100.0 * np.array([
            float(row[f"{name}_l1_std"])
            for row in rows
        ])
        axis.errorbar(
            dt,
            error,
            yerr=std,
            marker="o",
            capsize=3,
            label=label,
        )
    axis.set_xticks(dt)
    axis.set_xticklabels([f"{value:g}" for value in dt], rotation=45, ha="right")
    axis.set_xlabel(r"$\Delta t\ [r_{\mathrm{g}}/c]$", fontsize=LABEL_SIZE)
    axis.set_ylabel(r"$\epsilon_{\rm image}\ [\%]$", fontsize=LABEL_SIZE)
    axis.tick_params(axis="both", which="major", labelsize=TICK_SIZE)
    axis.grid(alpha=0.25)
    axis.set_ylim(bottom=0.0)
    axis.legend(fontsize=LEGEND_SIZE, ncols=2)
    paths = save_figure(figure, output_dir / "error_img", formats, dpi=220)
    plt.close(figure)

    for path in paths:
        print(f"Wrote {path}")
    return paths


def path_parameter(parameters: dict[str, object], name: str) -> Path:
    """Read a path parameter and check the type before running the task."""
    value = parameters[name]
    if not isinstance(value, Path):
        raise TypeError(f"{name} must be a pathlib.Path value.")
    return value


def calculate_primitive(parameters: dict[str, object]) -> None:
    """Calculate the primitive time interpolation error according to the current configuration and reuse the completed results."""
    input_dir = path_parameter(parameters, "primitive_input")
    grid_path = path_parameter(parameters, "grid")
    category = path_parameter(parameters, "primitive_output")
    blocks = parameters["blocks"]
    dts = tuple(float(value) for value in parameters["dt"])
    shells = tuple(
        tuple(float(edge) for edge in shell) for shell in parameters["shells"])

    config_values = {
        "Config::TASK": "interp_err_primitive",
        "input_signature": primitive_input_signature(input_dir, grid_path),
        "dt": ",".join(f"{value:g}" for value in dts),
        "shells": ";".join(f"{r0:g},{r1:g}" for r0, r1 in shells),
        "blocks": "" if blocks is None else str(blocks),
    }
    frames = list_frames(input_dir)
    if len(frames) < 3:
        raise FileNotFoundError(f"Need at least 3 BHAC frames in {input_dir}")
    times = np.array([read_header(path).time for path in frames], dtype=np.float64)
    cases = interval_cases(dts, dt0_from_times(times))
    if (reused := find_reusable_run(
        category,
        config_values,
        {PRIMITIVE_CSV: PRIMITIVE_FIELDS},
        lambda run: primitive_result_complete(run, cases, shells),
    )) is not None:
        print(f"Reusing primitive interpolation result: {reused}")
        parameters["primitive_output"] = reused
        return

    run = allocate_run_directory(category)
    write_run_paths(run, data=input_dir, grid=grid_path, output=category)
    write_config(run, config_values)
    try:
        calculate_primitive_errors(
            input_dir=input_dir,
            grid_path=grid_path,
            output_dir=run,
            dts=dts,
            shells=shells,
            nb=None if blocks is None else int(blocks),
            load_workers=int(parameters["load_workers"]),
            workers=int(parameters["workers"]),
        )
        write_run_status(run, "complete")
    except Exception:
        write_run_status(run, "failed")
        raise
    parameters["primitive_output"] = run


def plot_primitive(parameters: dict[str, object]) -> None:
    """Print the primitive error summary and redraw the convergence plot."""
    run = latest_complete_run(
        path_parameter(parameters, "primitive_output"),
        {PRIMITIVE_CSV: PRIMITIVE_FIELDS},
    )
    parameters["primitive_output"] = run
    print_primitive_errors(run)
    plot_primitive_errors(
        input_dir=run,
        output=run / "plot" / "summary",
        formats=tuple(str(value) for value in parameters["formats"]),
        radial_log=bool(parameters["radial_log"]),
    )


def calculate_observation(parameters: dict[str, object]) -> None:
    """Calculate the fast light I/Q/U/V image time interpolation error according to the current configuration and reuse the completed results."""
    input_dir = path_parameter(parameters, "observation_input")
    category = path_parameter(parameters, "observation_output")
    dts = tuple(float(value) for value in parameters["dt"])
    nt0 = parameters["nt0"]
    nt1 = parameters["nt1"]

    config_values = {
        "Config::TASK": "interp_err_observation",
        "input_signature": observation_input_signature(input_dir),
        "dt": ",".join(f"{value:g}" for value in dts),
        "nt0": "" if nt0 is None else str(nt0),
        "nt1": "" if nt1 is None else str(nt1),
    }
    result = result_from_config(input_dir, label="Fast light")
    frames = observation_frames(result, nt0, nt1)
    cases = interval_cases(dts, result.dt)
    if (reused := find_reusable_run(
        category,
        config_values,
        {
            OBSERVATION_CSV: OBSERVATION_FIELDS,
            OBSERVATION_FRAME_CSV: OBSERVATION_FRAME_FIELDS,
        },
        lambda run: observation_result_complete(run, frames, cases),
    )) is not None:
        print(f"Reusing observation interpolation result: {reused}")
        parameters["observation_output"] = reused
        return

    run = allocate_run_directory(category)
    write_run_paths(run, data=input_dir, grid=None, output=category)
    write_config(run, config_values)
    try:
        calculate_observation_errors(
            input_dir=input_dir,
            output_dir=run,
            dts=dts,
            nt_start=nt0,
            nt_end=nt1,
            workers=int(parameters["workers"]),
        )
        write_run_status(run, "complete")
    except Exception:
        write_run_status(run, "failed")
        raise
    parameters["observation_output"] = run


def plot_observation(parameters: dict[str, object]) -> None:
    """Redraw fast light I/Q/U/V image time interpolation error plot."""
    run = latest_complete_run(
        path_parameter(parameters, "observation_output"),
        {
            OBSERVATION_CSV: OBSERVATION_FIELDS,
            OBSERVATION_FRAME_CSV: OBSERVATION_FRAME_FIELDS,
        },
    )
    parameters["observation_output"] = run
    plot_observation_errors(
        input_dir=run,
        output_dir=run / "plot",
        formats=tuple(str(value) for value in parameters["formats"]),
    )


def print_paths(parameters: dict[str, object]) -> None:
    """Print the input and output paths of the current two types of verification."""
    print("Primitive interpolation")
    print(f"  input:  {path_parameter(parameters, 'primitive_input')}")
    print(f"  grid:   {path_parameter(parameters, 'grid')}")
    print(f"  output: {path_parameter(parameters, 'primitive_output')}")
    print("Observation interpolation")
    print(f"  input:  {path_parameter(parameters, 'observation_input')}")
    print(f"  output: {path_parameter(parameters, 'observation_output')}")


def main() -> None:
    parameters = configure_parameters()
    print_paths(parameters)

    # calculate_primitive(parameters)
    # plot_primitive(parameters)
    # calculate_observation(parameters)
    # plot_observation(parameters)

    pass


if __name__ == "__main__":
    main()
