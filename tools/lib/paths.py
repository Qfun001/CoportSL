"""Number the run directory and post-processing output path."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import re
from typing import Mapping

from .data import (
    Result,
    expected_output_frames,
    find_frames,
    read_key_values,
    read_status,
    result_from_config,
)


RUN_RE = re.compile(r"output[0-9]+")

MODEL_FIELDS = (
    "Config::FLUID_BACKEND",
    "Input::T0", "Input::DT",
    "Config::NPIX", "Config::FOV", "Config::NU", "Config::OBS_T",
    "Config::OBS_R", "Config::OBS_TH", "Config::OBS_PH", "Config::METRIC",
    "Config::SPIN", "Config::HS", "Config::ELECTRON", "Config::MBH",
    "Config::MDOT", "Config::MDOT_SIM", "Config::R_LOW", "Config::R_HIGH",
    "Config::BETA0", "Config::SIGMA_MAX", "Config::THETAE_EMIT",
    "Config::NE_EMIT", "Config::POL_LIMIT", "Config::P_MIN", "Config::P_MAX",
    "Config::GAMMA_RATIO", "Config::BEAM_ANGLE", "Config::BEAM_WIDTH",
    "Config::RAY_ATOL", "Config::RAY_RTOL", "Config::RAY_HMIN",
    "Config::RAY_LMAX", "Config::RAY_H0", "Config::RAY_CELL",
    "Config::RAY_HORIZON", "Config::R_SOURCE",
)

EXACT_MODEL_FIELDS = {
    "Config::FLUID_BACKEND",
    "Config::NPIX", "Config::METRIC", "Config::ELECTRON",
}

MODEL_REL_TOL = 1.0e-11
SHA256_RE = re.compile(r"[0-9a-f]{64}")
NONTHERMAL_FIELDS = (
    "Config::P_MIN", "Config::P_MAX", "Config::GAMMA_RATIO",
)
BEAM_FIELDS = ("Config::BEAM_ANGLE", "Config::BEAM_WIDTH")
CONDITIONAL_MODEL_FIELDS = set(NONTHERMAL_FIELDS + BEAM_FIELDS)
COMMON_MODEL_FIELDS = tuple(
    field for field in MODEL_FIELDS
    if field not in CONDITIONAL_MODEL_FIELDS
)
ELECTRON_VALUES = {"thermal", "powerlaw", "beam", "losscone"}


@dataclass(frozen=True)
class ModelComparison:
    """Post-processing compatibility of two model configurations, as well as tolerance and strict difference fields."""

    compatible: bool
    approximate_fields: tuple[str, ...] = ()
    different_fields: tuple[str, ...] = ()


def compare_model_configs(
    first: Mapping[str, str],
    second: Mapping[str, str],
) -> ModelComparison:
    """The input content is required to be the same, and then the model configurations are compared by field type."""
    different: list[str] = []
    approximate: list[str] = []
    first_input = first.get("input_signature")
    second_input = second.get("input_signature")
    if (
        first_input is None
        or second_input is None
        or SHA256_RE.fullmatch(first_input) is None
        or SHA256_RE.fullmatch(second_input) is None
        or first_input != second_input
    ):
        different.append("input_signature")

    first_electron = first.get("Config::ELECTRON")
    second_electron = second.get("Config::ELECTRON")
    active_fields = list(COMMON_MODEL_FIELDS)
    if first_electron in ELECTRON_VALUES - {"thermal"} or \
            second_electron in ELECTRON_VALUES - {"thermal"}:
        active_fields.extend(NONTHERMAL_FIELDS)
    if first_electron in {"beam", "losscone"} or \
            second_electron in {"beam", "losscone"}:
        active_fields.extend(BEAM_FIELDS)

    for field in active_fields:
        left = first.get(field)
        right = second.get(field)
        if left is None or right is None:
            different.append(field)
            continue
        if field in EXACT_MODEL_FIELDS:
            if field == "Config::NPIX":
                if re.fullmatch(r"[+-]?[0-9]+", left) is None or \
                        re.fullmatch(r"[+-]?[0-9]+", right) is None or \
                        int(left) != int(right):
                    different.append(field)
            elif field == "Config::ELECTRON":
                if left not in ELECTRON_VALUES or right not in ELECTRON_VALUES or \
                        left != right:
                    different.append(field)
            elif not left or not right or left != right:
                different.append(field)
            continue
        try:
            left_value = float(left)
            right_value = float(right)
        except ValueError:
            different.append(field)
            continue
        if not math.isfinite(left_value) or not math.isfinite(right_value):
            different.append(field)
        elif left_value == right_value:
            continue
        elif math.isclose(
            left_value,
            right_value,
            rel_tol=MODEL_REL_TOL,
            abs_tol=0.0,
        ):
            approximate.append(field)
        else:
            different.append(field)
    return ModelComparison(
        compatible=not different,
        approximate_fields=tuple(approximate),
        different_fields=tuple(different),
    )


def require_run(run: str) -> None:
    """Verify that the run number is in the canonical format for the C++ output directory."""
    if RUN_RE.fullmatch(run) is None:
        raise ValueError(f"Invalid run name {run!r}; expected outputNNNN.")
    number = int(run.removeprefix("output"))
    if number <= 0 or f"output{number:04d}" != run:
        raise ValueError(f"Invalid run name {run!r}; expected outputNNNN.")


@dataclass(frozen=True)
class Case:
    """Represent a group of numbered fast- or slow-light runs."""

    light: str
    run: str
    label: str = ""

    def __post_init__(self) -> None:
        if self.light not in {"fast", "slow"}:
            raise ValueError(f"Invalid light type {self.light!r}; expected 'fast' or 'slow'.")
        require_run(self.run)


@dataclass(frozen=True)
class ProjectPaths:
    """Project root path and numbered run path rules."""

    root: Path

    @property
    def result_root(self) -> Path:
        return self.root / "result"

    def result_path(self, case: Case) -> Path:
        return self.result_root / case.light / case.run

    def plot_path(self, case: Case) -> Path:
        return self.result_path(case) / "plot"

    def fast_result_path(self, case: Case) -> Path:
        require_light(case, "fast")
        return self.result_path(case)

    def fast_plot_path(self, case: Case) -> Path:
        require_light(case, "fast")
        return self.plot_path(case)

    def slow_result_path(self, case: Case) -> Path:
        require_light(case, "slow")
        return self.result_path(case)

    def slow_plot_path(self, case: Case) -> Path:
        require_light(case, "slow")
        return self.plot_path(case)

    def slow_alignment_path(self, case: Case) -> Path:
        return self.slow_plot_path(case) / "time_alignment.csv"

    def analysis_input_path(self, run: str) -> Path:
        require_run(run)
        return self.result_root / "analysis" / run

    def analysis_output_path(self, run: str) -> Path:
        return self.analysis_input_path(run) / "plot"

    def comparison_path(self, name: str) -> Path:
        """Returns directories for cross-batch comparison, does not accept path fragments."""
        if not name or Path(name).name != name or name in {".", ".."}:
            raise ValueError(f"Invalid comparison name {name!r}; expected one directory name.")
        return self.result_root / "comparison" / name

    def fast_result(self, case: Case) -> Result:
        return result_from_config(
            self.fast_result_path(case), label=case.label or "Fast light")

    def slow_result(self, case: Case) -> Result:
        return result_from_config(
            self.slow_result_path(case), label=case.label or case.run)


def require_light(case: Case, light: str) -> None:
    if case.light != light:
        raise ValueError(f"Expected a {light}-light case, got {case.light}/{case.run}.")


def case_name(case: Case) -> str:
    return case.label or f"{case.light}/{case.run}"


def complete_result(path: Path, values: dict[str, str]) -> bool:
    """Check that all I/Q/U/V frames required by status and configuration are complete."""
    if read_status(path) != "complete":
        return False
    try:
        result_from_config(path)
        expected = expected_output_frames(values)
        actual = set(find_frames(
            path,
            int(values["Input::NT0"]),
            int(values["Input::NT1"]),
            required="IQUV",
        ))
    except (KeyError, OSError, ValueError):
        return False
    return bool(expected) and all(frame in actual for frame in expected)


def find_fast_result(
    result_path: Path,
    model_signature: str | None = None,
) -> Path | None:
    """Find the highest numbered complete matching flash in the current results root directory."""
    result_path = result_path.resolve()
    if result_path.parent.name != "slow":
        raise ValueError(
            f"Expected a result/slow/outputNNNN path, got {result_path}.")
    if model_signature is None:
        model_signature = read_key_values(
            result_path / "config.txt").get("model_signature")
    if model_signature is None:
        raise KeyError(f"Missing model_signature in {result_path / 'config.txt'}.")

    target_values = read_key_values(result_path / "config.txt")
    candidates: list[tuple[int, int, Path, dict[str, str]]] = []
    fast_root = result_path.parent.parent / "fast"
    if not fast_root.is_dir():
        return None
    for path in fast_root.iterdir():
        if not path.is_dir() or RUN_RE.fullmatch(path.name) is None:
            continue
        try:
            require_run(path.name)
            values = read_key_values(path / "config.txt")
        except (OSError, ValueError):
            continue
        if values.get("Config::TASK") != "fast":
            continue
        exact = values.get("model_signature") == model_signature
        if exact:
            priority = 0
        else:
            comparison = compare_model_configs(values, target_values)
            if not comparison.compatible or not comparison.approximate_fields:
                continue
            priority = 1
        candidates.append((
            priority,
            -int(path.name.removeprefix("output")),
            path,
            values,
        ))

    # Accurate signatures take precedence; peers check integrity starting from the latest number.
    for _, _, path, values in sorted(candidates):
        if complete_result(path, values):
            return path
    return None
