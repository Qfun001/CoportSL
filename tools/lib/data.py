"""Result data description, Stokes file reading and general CSV reading and writing."""

from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import numpy as np

from .constant import C, G, M_SUN, PC, RAD_TO_UAS, SOURCE_DISTANCE_PC

INTENSITY_RE = re.compile(r"I(?P<nt>\d+)\.csv$")


@dataclass(frozen=True)
class Result:
    """A set of calculated paths, time maps, and fixed imaging parameters."""

    path: Path  # Directory where Stokes CSV is located
    nt0: int | None  # The default starting frame is also the frame corresponding to t0
    nt1: int | None  # Default end frame
    dt: float  # Physical time interval between adjacent frames, unit rg/c
    t0: float  # The physical time corresponding to nt0, unit rg/c
    ro: float  # Observer imaging screen radius, unit rg
    fov: float  # Imaging field of view, unit rad
    distance_pc: float  # Source distance in pc
    task: str  # analysis, fast, slow or region_error
    model_signature: str  # Path-independent model signature
    timeline: tuple[tuple[int, float], ...] = ()  # Sparse source frame number and real physical time
    label: str = "Result"  # Names used in legends and multi-set data CSV
    mass_msun: float = 6.5e9  # Black hole mass, unit solar mass; default value corresponds to M87

    def time(self, nt: int, first_nt: int | None = None) -> float:
        """Convert frame number to physical time in $r_g/c$."""
        origin = self.nt0 if self.nt0 is not None else first_nt
        if origin is None:
            raise ValueError("A frame origin is required when nt0 is None.")
        if self.timeline:
            for frame, time in self.timeline:
                if frame == nt:
                    return time
            raise ValueError(f"Frame {nt} is absent from the input timeline.")
        return self.t0 + (nt - origin) * self.dt


def frame_bounds(result: Result, nt_start: int | None, nt_end: int | None) -> tuple[int | None, int | None]:
    """Override the default range in `Result` with a temporary frame range."""
    return (
        result.nt0 if nt_start is None else nt_start,
        result.nt1 if nt_end is None else nt_end,
    )


def stokes_path(result_dir: Path, stokes: str, nt: int) -> Path:
    """Constructs a CSV path specifying the Stokes component and frame number."""
    return result_dir / f"{stokes}{nt:04d}.csv"


def _numeric_lines(path: Path):
    """Line-by-line normalization of MSVC's non-finite floating-point text into a NumPy-recognizable form."""
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            yield line.replace("nan(ind)", "nan")


def load_csv_map(path: Path) -> np.ndarray:
    """Reads a numeric matrix, compatible with `nan(ind)` output by Windows C++."""
    return np.real(np.loadtxt(_numeric_lines(path), delimiter=",")).astype(
        np.float64, copy=False)


def find_frames(
    result_dir: Path,
    nt_start: int | None,
    nt_end: int | None,
    step: int = 1,
    required: str = "I",
    require_nonempty: bool = False,
) -> list[int]:
    """Finds frames with the specified Stokes component in the given range."""
    if step <= 0:
        raise ValueError("Frame step must be positive.")
    frames = []
    for path in result_dir.glob("I*.csv"):
        match = INTENSITY_RE.match(path.name)
        if match is None:
            continue

        nt = int(match.group("nt"))
        if nt_start is not None and nt < nt_start:
            continue
        if nt_end is not None and nt > nt_end:
            continue
        if nt_start is not None and (nt - nt_start) % step != 0:
            continue
        if not all(stokes_path(result_dir, name, nt).exists() for name in required):
            continue
        frames.append(nt)

    frames.sort()
    if require_nonempty and not frames:
        raise ValueError(f"No complete {required} frames found in {result_dir}.")
    return frames


def load_iqu(result_dir: Path, nt: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Reads a frame of Stokes I, Q, U images by matrix arrangement and values from a file."""
    i_map = load_csv_map(stokes_path(result_dir, "I", nt))
    q_map = load_csv_map(stokes_path(result_dir, "Q", nt))
    u_map = load_csv_map(stokes_path(result_dir, "U", nt))
    if not (
        i_map.shape == q_map.shape == u_map.shape
        and i_map.shape[0] == i_map.shape[1]
    ):
        raise ValueError(
            f"Stokes frame {nt} is not a square NPIX x NPIX matrix: "
            f"I={i_map.shape} Q={q_map.shape} U={u_map.shape}.")
    return i_map, q_map, u_map


def rg_cm(result: Result) -> float:
    """Calculate the gravitational radius of the current observation source, in cm."""
    return G * result.mass_msun * M_SUN / (C * C)


def observer_fov_muas(*, ro: float, fov: float, distance_pc: float, mass_msun: float) -> float:
    """The angular scale corresponding to the entire imaging field of view is calculated based on the viewer's setting, and the unit is micro-arcseconds."""
    rg = G * mass_msun * M_SUN / (C * C)
    distance_cm = distance_pc * PC
    return ro * rg / distance_cm * fov * RAD_TO_UAS


def read_key_values(path: Path) -> dict[str, str]:
    """Read the configuration file in the form of `key=value`."""
    values: dict[str, str] = {}
    with path.open() as stream:
        for line in stream:
            text = line.strip()
            if not text or text.startswith("#") or "=" not in text:
                continue
            key, value = text.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def read_status_paths(result_dir: Path) -> dict[str, str]:
    """Read the path block of status.txt (data/grid/output/analysis)."""
    status = result_dir / "status.txt"
    values: dict[str, str] = {}
    if not status.is_file():
        return values
    with status.open() as stream:
        for line in stream:
            text = line.strip()
            if not text or "=" not in text:
                continue
            key, value = text.split("=", 1)
            key = key.strip()
            if key in {"data", "grid", "output", "analysis"}:
                values[key] = value.strip()
    return values


def read_status(result_dir: Path) -> str:
    """Read the last status word in the appended status file."""
    path = result_dir / "status.txt"
    value = ""
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            fields = line.split()
            if fields and fields[0] in {
                    "running", "complete", "failed", "cancelled"}:
                value = fields[0]
    except OSError:
        return ""
    return value


def input_timeline(values: Mapping[str, str]) -> tuple[tuple[int, float], ...]:
    """Read equally spaced legacy configurations or explicit non-uniform input timelines."""
    try:
        nt0 = int(values["Input::NT0"])
        nt1 = int(values["Input::NT1"])
        t0 = float(values["Input::T0"])
        dt = float(values["Input::DT"])
    except KeyError as exc:
        raise KeyError(f"Missing {exc.args[0]} in input timeline.") from exc
    if nt1 < nt0 or not math.isfinite(t0) or not math.isfinite(dt) or dt <= 0.0:
        raise ValueError("Invalid input timeline.")

    cadence = values.get("Input::CADENCE", "uniform")
    if cadence == "uniform":
        return tuple(
            (frame, t0 + (frame - nt0) * dt)
            for frame in range(nt0, nt1 + 1)
        )
    if cadence != "irregular":
        raise ValueError(f"Unknown Input::CADENCE: {cadence!r}")
    try:
        count = int(values["Input::FRAME_COUNT"])
        timeline = tuple(
            (
                int(values[f"Input::FRAME.{index}.INDEX"]),
                float(values[f"Input::FRAME.{index}.TIME"]),
            )
            for index in range(count)
        )
    except KeyError as exc:
        raise KeyError(f"Missing {exc.args[0]} in irregular timeline.") from exc
    if count < 2 or len(timeline) != count:
        raise ValueError("Irregular input timeline must contain at least two frames.")
    if timeline[0] != (nt0, t0) or timeline[-1][0] != nt1:
        raise ValueError("Irregular timeline endpoints do not match Input::NT0/NT1/T0.")
    for previous, current in zip(timeline, timeline[1:]):
        if current[0] <= previous[0] or not math.isfinite(current[1]) \
                or current[1] <= previous[1]:
            raise ValueError("Irregular input frames and times must increase.")
    return timeline


def result_from_config(path: Path, label: str = "Result") -> Result:
    """Constructs `Result` from `config.txt` in the results directory."""
    config = path / "config.txt"
    values = read_key_values(config)
    try:
        task = values["Config::TASK"]
        model_signature = values["model_signature"]
        nt0 = int(values["Input::NT0"])
        nt1 = int(values["Input::NT1"])
        dt = float(values["Input::DT"])
        t0 = float(values["Input::T0"])
        ro = float(values["Config::OBS_R"])
        fov = float(values["Config::FOV"])
        mass_msun = float(values["Config::MBH"])
    except KeyError as exc:
        raise KeyError(f"Missing {exc.args[0]} in {config}.") from exc

    if task not in {"analysis", "fast", "slow", "region_error"}:
        raise ValueError(f"Invalid Config::TASK in {config}: {task!r}")
    if not re.fullmatch(r"[0-9a-f]{64}", model_signature):
        raise ValueError(f"Invalid model_signature in {config}.")
    timeline = input_timeline(values)
    if not np.isfinite(dt) or dt <= 0.0:
        raise ValueError(f"Invalid Input::DT in {config}: {dt}")
    if not np.isfinite(t0):
        raise ValueError(f"Invalid Input::T0 in {config}: {t0}")
    for name, value in (
        ("Config::OBS_R", ro),
        ("Config::FOV", fov),
        ("Config::MBH", mass_msun),
    ):
        if not np.isfinite(value) or value <= 0.0:
            raise ValueError(f"Invalid {name} in {config}: {value}")

    return Result(
        path=path,
        nt0=nt0,
        nt1=nt1,
        dt=dt,
        t0=t0,
        ro=ro,
        fov=fov,
        distance_pc=SOURCE_DISTANCE_PC,
        task=task,
        model_signature=model_signature,
        timeline=timeline if values.get("Input::CADENCE") == "irregular" else (),
        label=label,
        mass_msun=mass_msun,
    )


def expected_output_frames(values: Mapping[str, str]) -> list[int]:
    """The output frame a full run should have is derived only from the current configuration semantics."""
    try:
        task = values["Config::TASK"]
    except KeyError as exc:
        raise KeyError(f"Missing {exc.args[0]} in result configuration.") from exc
    timeline = input_timeline(values)
    frames = [frame for frame, _time in timeline]
    if task == "fast":
        return frames
    if task == "slow":
        try:
            left = float(values["SlowLight::LEFT"])
            right = float(values["SlowLight::RIGHT"])
        except KeyError as exc:
            raise KeyError(f"Missing {exc.args[0]} in slow result configuration.") from exc
        if not math.isfinite(left) or not math.isfinite(right) or left > right:
            raise ValueError("Invalid slow-light window in result configuration.")
        first_time = timeline[0][1]
        last_time = timeline[-1][1]
        return [
            frame
            for frame, time in timeline
            if first_time <= time + left
            and time + right <= last_time
        ]
    if task == "region_error":
        text = values.get("RegionError::FRAMES", "")
        if not text:
            raise KeyError("Missing RegionError::FRAMES in result configuration.")
        frames = [int(value) for value in text.split(";")]
        available = set(frame for frame, _time in timeline)
        if any(frame not in available for frame in frames):
            raise ValueError("RegionError frame is outside the input timeline.")
        return frames
    if task == "analysis":
        return []
    raise ValueError(f"Unknown Config::TASK: {task!r}")


def analysis_fov_muas(path: Path) -> float:
    """Read the upstream imaging settings from the GRRT pre-analysis configuration and calculate the angular scale."""
    values = read_key_values(path)
    try:
        ro = float(values["Config::OBS_R"])
        fov = float(values["Config::FOV"])
        mass_msun = float(values["Config::MBH"])
    except KeyError as exc:
        raise KeyError(f"Missing {exc.args[0]} in {path}.") from exc
    return observer_fov_muas(
        ro=ro,
        fov=fov,
        distance_pc=SOURCE_DISTANCE_PC,
        mass_msun=mass_msun,
    )


def fov_muas(result: Result) -> float:
    """Calculate the angular scale corresponding to the entire imaging field of view, in microarcseconds."""
    return observer_fov_muas(
        ro=result.ro,
        fov=result.fov,
        distance_pc=result.distance_pc,
        mass_msun=result.mass_msun,
    )


def read_rows(path: Path) -> list[dict[str, str]]:
    """Read a headered CSV as a row-organized list of dictionaries."""
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def read_time_shift(directory: Path | None, fallback: float = 0.0) -> float:
    """Read the time shift of the target result from `time_alignment.csv` in the plot directory."""
    if directory is None:
        return fallback
    target = directory / "time_alignment.csv"
    if not target.exists():
        return fallback
    rows = read_rows(target)
    if not rows:
        raise ValueError(f"No time-alignment rows found in {target}.")
    row = rows[0]
    return float(row.get("target_time_shift_rg_over_c", row.get("slow_time_shift_rg_over_c", fallback)))


def write_rows(path: Path, rows: list[dict[str, float | int | str]]) -> Path:
    """Write dictionary rows with the same field to CSV."""
    if not rows:
        raise ValueError(f"No rows to write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path
