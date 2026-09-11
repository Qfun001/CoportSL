"""Page sharing logic: job assembly, unit conversion, event analysis and result scanning.

Only the fields that are actually parsed by the C++ runtime configuration (``src/config/Runtime.cpp``) are assembled here;
Unknown keys are never silently discarded, but a Chinese error is reported immediately when the job is generated."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import re
from typing import Any
import uuid
from datetime import datetime

from ..config import update_job
from ..engine import capabilities, default_config
from ..widgets.fields import parse_number_expression

# ---------------------------------------------------------------------------
# Capability list and default values (with caching; Worker contract command starts quickly)
# ---------------------------------------------------------------------------

_defaults_cache: dict[str, dict[str, Any]] = {}
_capabilities_cache: dict[str, dict[str, Any]] = {}


def load_defaults(kind: str) -> dict[str, Any]:
    if kind not in _defaults_cache:
        _defaults_cache[kind] = default_config(kind)
    return deepcopy(_defaults_cache[kind])


def load_capabilities(kind: str) -> dict[str, Any]:
    if kind not in _capabilities_cache:
        _capabilities_cache[kind] = capabilities(kind)
    return deepcopy(_capabilities_cache[kind])


# ---------------------------------------------------------------------------
# Domain constants
# ---------------------------------------------------------------------------

ELECTRON_CHOICES = (
    ("THERMAL", "thermal"),
    ("POWER_LAW", "powerlaw"),
    ("BEAM", "beam"),
    ("LOSS_CONE", "losscone"),
)

# Integer encoding of Config::ELECTRON in config.txt (see apps/grrt/GRRTConfig.h).
ELECTRON_FROM_CODE = {
    "0": "thermal",
    "1": "powerlaw",
    "2": "beam",
    "3": "losscone",
}

TASK_CHOICES = (
    ("慢光前置分析", "analysis"),
    ("快光成像", "fast"),
    ("慢光成像", "slow"),
    ("区域截断误差", "region_error"),
)

TASK_DIR_NAMES = ("analysis", "fast", "slow", "region_error", "benchmark")

WINDOW_CHOICES = ("p90", "p95", "p99", "p99.9", "full")

MANUAL_SET_NAMES = ("r20", "r30", "r50", "r80", "r100", "r200")

# The whitelist of fields allowed to be written to the job is consistent with the parsing of src/config/Runtime.cpp.
CAMERA_KEYS = (
    "npix", "fov_rad", "nu_hz", "frequencies_hz",
    "observer_t", "observer_r_rg", "observer_theta_rad", "observer_phi_rad",
)
MODEL_KEYS = (
    "metric", "fluid_backend", "electron", "mbh_msun", "spin", "hs",
    "mdot_msun_per_year", "mdot_sim", "r_low", "r_high", "beta0",
    "sigma_max", "thetae_emit", "ne_emit_cm3", "pol_limit", "p_min",
    "p_max", "gamma_ratio", "beam_angle_rad", "beam_width", "r_source_rg",
)
RAY_KEYS = (
    "atol", "rtol", "hmin", "lmax", "h0", "cell_fraction", "horizon_factor",
)
TOLERANCE_KEYS = ("jI", "jP", "aI", "aP", "rhoV", "rhoC")


# ---------------------------------------------------------------------------
# Unit conversion
# ---------------------------------------------------------------------------

NumberSource = float | int | str


def ghz_to_hz(value: NumberSource) -> float | str:
    if isinstance(value, str):
        return f"({value})*1e9"
    return float(value) * 1.0e9


def hz_to_ghz(value: float) -> float:
    return float(value) / 1.0e9


def deg_to_rad(value: NumberSource) -> float | str:
    if isinstance(value, str):
        return f"({value})*pi/180"
    return math.radians(float(value))


def rad_to_deg(value: float) -> float:
    return math.degrees(float(value))


def new_job_id() -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{uuid.uuid4().hex[:6]}"


# ---------------------------------------------------------------------------
# Job assembly
# ---------------------------------------------------------------------------

def _apply(job: dict[str, Any], section: str, values: dict[str, Any],
           allowed: tuple[str, ...]) -> None:
    target = job.setdefault(section, {})
    for key, value in values.items():
        if key not in allowed:
            raise ValueError(f"内部错误：尝试写入未接入字段 {section}.{key}")
        target[key] = value


def _numeric_value(value: NumberSource) -> float:
    return parse_number_expression(value) if isinstance(value, str) \
        else float(value)


def _require_positive(value: NumberSource, label: str) -> None:
    numeric = _numeric_value(value)
    if not math.isfinite(numeric) or numeric <= 0:
        raise ValueError(f"{label}无效（实际值 {value}）：必须为正数。")


def build_grrt_job(
    defaults: dict[str, Any],
    *,
    data: Path,
    grid: Path,
    output: Path,
    task: str,
    npix: int,
    frequency_ghz: NumberSource,
    fov_deg: NumberSource,
    electron: str,
    mdot: NumberSource,
    postprocess: bool,
    frame_start: int | None = None,
    frame_end: int | None = None,
    model_extra: dict[str, Any] | None = None,
    camera_extra: dict[str, Any] | None = None,
    ray: dict[str, Any] | None = None,
    analysis: dict[str, Any] | None = None,
    slow: dict[str, Any] | None = None,
    region_error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the GRRT job; only include C++-wired fields."""
    if task not in {value for _, value in TASK_CHOICES}:
        raise ValueError(f"未知 GRRT 任务：{task}")
    _require_positive(frequency_ghz, "观测频率")
    _require_positive(fov_deg, "视场角")
    _require_positive(mdot, "物理吸积率")
    if int(npix) <= 0:
        raise ValueError(f"图像分辨率无效（camera.npix={npix}）：必须为正整数。")

    job = update_job(
        defaults,
        data=data,
        grid=grid,
        output=output,
        task=task,
        npix=int(npix),
        frequency_ghz=frequency_ghz,
        electron=electron,
        mdot=mdot,
        postprocess=bool(postprocess),
    )
    if frame_start is not None or frame_end is not None:
        if frame_start is None or frame_end is None:
            raise ValueError("输出帧范围必须同时填写起始帧和结束帧。")
        if int(frame_start) > int(frame_end):
            raise ValueError("输出起始帧不能大于结束帧。")
        job["grrt"]["frame_start"] = int(frame_start)
        job["grrt"]["frame_end"] = int(frame_end)
    camera: dict[str, Any] = {"fov_rad": deg_to_rad(fov_deg)}
    if camera_extra:
        camera.update(camera_extra)
    _apply(job, "camera", camera, CAMERA_KEYS)
    if model_extra:
        _apply(job, "model", model_extra, MODEL_KEYS)
    if ray:
        _apply(job, "ray", ray, RAY_KEYS)

    if analysis:
        values = dict(analysis)
        tolerances = values.pop("region_tolerances", None)
        _apply(job, "analysis", values, ("sample_dt_rg_over_c",))
        if tolerances is not None:
            for key in tolerances:
                if key not in TOLERANCE_KEYS:
                    raise ValueError(f"未知区域容限键：{key}")
            _apply(job, "analysis", {"region_tolerances": tolerances},
                   ("region_tolerances",))
    if slow:
        _apply(job, "slow", slow, (
            "partition", "region_mode", "window", "manual_set",
            "region_sets",
        ))
    if region_error:
        job["region_error"] = {}
        _apply(job, "region_error", region_error, ("frame_step",))

    _drop_irrelevant_sections(job, task)
    if task == "region_error" and analysis is None:
        job.pop("analysis", None)
    return job


def _drop_irrelevant_sections(job: dict[str, Any], task: str) -> None:
    """Prune configuration sections according to tasks to avoid misleading Worker verification."""
    keep = {"schema_version", "job_id", "kind", "paths", "camera", "model",
            "ray", "grrt"}
    if task == "analysis":
        keep.update({"analysis", "slow"})
    elif task == "slow":
        keep.update({"analysis", "slow"})
    elif task == "region_error":
        keep.update({"region_error", "slow"})
    for section in list(job):
        if section not in keep:
            del job[section]


def build_flux_job(
    defaults: dict[str, Any],
    *,
    data: Path,
    grid: Path,
    npix: int,
    fov_deg: NumberSource,
    frequencies_ghz: list[NumberSource],
    electron: str,
    mdot: NumberSource,
    frame_start: int,
    frame_end: int,
    frame_step: int,
    target_flux_jy: NumberSource,
    distance_pc: NumberSource,
    model_extra: dict[str, Any] | None = None,
    camera_extra: dict[str, Any] | None = None,
    ray: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the Flux job (Flux does not write the output directory, and the results are printed to the standard output)."""
    if not frequencies_ghz:
        raise ValueError("频率列表不能为空：请至少填写一个频率。")
    for value in frequencies_ghz:
        _require_positive(value, "频率")
    _require_positive(fov_deg, "视场角")
    _require_positive(mdot, "物理吸积率")
    _require_positive(target_flux_jy, "目标通量密度")
    _require_positive(distance_pc, "源距离")
    if int(npix) <= 0:
        raise ValueError(
            f"图像边长无效（camera.npix={npix}）：必须为正整数。")
    if frame_start > frame_end:
        raise ValueError(
            f"帧范围无效（flux.frame_start={frame_start} > "
            f"flux.frame_end={frame_end}）：起始帧不能大于结束帧。")
    if frame_step <= 0:
        raise ValueError("帧步长无效：必须为正整数。")

    job = deepcopy(defaults)
    job["schema_version"] = 1
    job["kind"] = "flux"
    job["paths"] = {
        "data": str(data.resolve()),
        "grid": str(grid.resolve()),
    }
    camera = {
        "npix": int(npix),
        "fov_rad": deg_to_rad(fov_deg),
        "frequencies_hz": [ghz_to_hz(value) for value in frequencies_ghz],
    }
    if camera_extra:
        camera.update(camera_extra)
    _apply(job, "camera", camera, CAMERA_KEYS)
    _apply(job, "model", {"electron": electron,
                          "mdot_msun_per_year": mdot}, MODEL_KEYS)
    if model_extra:
        _apply(job, "model", model_extra, MODEL_KEYS)
    if ray:
        _apply(job, "ray", ray, RAY_KEYS)
    _apply(job, "flux", {
        "frame_start": int(frame_start),
        "frame_end": int(frame_end),
        "frame_step": int(frame_step),
        "target_flux_jy": target_flux_jy,
        "distance_pc": distance_pc,
    }, ("frame_start", "frame_end", "frame_step",
        "target_flux_jy", "distance_pc"))
    for section in ("analysis", "slow", "region_error", "grrt", "benchmark"):
        job.pop(section, None)
    return job


def build_benchmark_job(
    defaults: dict[str, Any],
    *,
    data: Path,
    grid: Path,
    output: Path,
    frame_start: int,
    frame_end: int,
    frame_step: int,
    npix_list: list[int],
    core_counts: list[int],
    repeats: int,
    warmup_frames: int,
    run_fast: bool,
    run_slow: bool,
    electron: str | None = None,
    model_extra: dict[str, Any] | None = None,
    core_modes: list[str] | None = None,
) -> dict[str, Any]:
    """Benchmark job that assembles GRMHD data adaptation parameters and performance sweep parameters."""
    if frame_start > frame_end:
        raise ValueError(
            f"帧范围无效（benchmark.frame_start={frame_start} > "
            f"benchmark.frame_end={frame_end}）：起始帧不能大于结束帧。")
    if frame_step <= 0:
        raise ValueError("帧步长无效：必须为正整数。")
    if not npix_list:
        raise ValueError("图像边长列表不能为空。")
    if not core_counts:
        raise ValueError("物理核心数列表不能为空。")
    for value in npix_list:
        if int(value) <= 0:
            raise ValueError(
                f"图像边长列表项无效（{value}）：必须为正整数。")
    for value in core_counts:
        if int(value) <= 0:
            raise ValueError(f"物理核心数列表项无效（{value}）：必须为正整数。")
    if repeats <= 0:
        raise ValueError("重复次数无效：必须为正整数。")
    if warmup_frames < 0:
        raise ValueError("预热帧数无效：不能为负数。")
    if not (run_fast or run_slow):
        raise ValueError("请至少选择一种传播模型（快光或慢光）。")
    allowed_modes = {
        "physical_cores", "performance_cores", "efficiency_cores",
    }
    if core_modes is not None:
        if len(core_modes) != 1:
            raise ValueError("核心组必须且只能选择一种物理核心类型。")
        unknown = sorted(set(core_modes) - allowed_modes)
        if unknown:
            raise ValueError(f"未知核心组：{', '.join(unknown)}")

    job = deepcopy(defaults)
    job["schema_version"] = 1
    job["kind"] = "benchmark"
    job["paths"] = {
        "data": str(data.resolve()),
        "grid": str(grid.resolve()),
        "output": str(output.resolve()),
    }
    model: dict[str, Any] = {}
    if electron is not None:
        model["electron"] = electron
    if model_extra:
        model.update(model_extra)
    if model:
        _apply(job, "model", model, MODEL_KEYS)
    values: dict[str, Any] = {
        "frame_start": int(frame_start),
        "frame_end": int(frame_end),
        "frame_step": int(frame_step),
        "npix_list": sorted({int(value) for value in npix_list}),
        "core_counts": sorted({int(value) for value in core_counts}),
        "repeats": int(repeats),
        "warmup_frames": int(warmup_frames),
        "run_fast": bool(run_fast),
        "run_slow": bool(run_slow),
    }
    if core_modes is not None:
        values["core_modes"] = list(dict.fromkeys(core_modes))
    _apply(job, "benchmark", values, (
        "frame_start", "frame_end", "frame_step", "npix_list", "core_counts",
        "repeats", "warmup_frames", "run_fast", "run_slow",
        "partition", "window", "core_modes",
    ))
    for section in ("slow", "region_error", "grrt", "flux"):
        job.pop(section, None)
    return job


# ---------------------------------------------------------------------------
# Worker output parsing
# ---------------------------------------------------------------------------

EVENT_PREFIX = "COPORTSL_EVENT "


def parse_event_line(line: str) -> dict[str, Any] | None:
    """Parses a line of Worker standard output; returns a dict for event lines and None for normal lines."""
    if not line.startswith(EVENT_PREFIX):
        return None
    try:
        value = json.loads(line[len(EVENT_PREFIX):])
    except json.JSONDecodeError:
        return None
    if not isinstance(value, dict) or "type" not in value:
        return None
    return value


@dataclass(frozen=True)
class FluxSummary:
    nu_ghz: float
    frame_count: int
    mean_flux_jy: float
    min_flux_jy: float
    max_flux_jy: float
    std_flux_jy: float
    target_flux_jy: float
    current_mdot: float
    suggested_mdot_linear: float
    suggested_mdot_sqrt: float


def parse_flux_summaries(text: str) -> list[FluxSummary]:
    """Parses summary cards for each frequency from the Flux Worker's standard output."""
    summaries: list[FluxSummary] = []
    current: dict[str, float] | None = None
    for line in text.splitlines():
        line = line.strip()
        if line == "Flux summary":
            if current is not None:
                _append_summary(summaries, current)
            current = {}
        elif current is not None and "=" in line:
            key, _, raw = line.partition("=")
            key = key.strip()
            try:
                current[key] = float(raw.strip())
            except ValueError:
                continue
    if current is not None:
        _append_summary(summaries, current)
    return summaries


def _append_summary(summaries: list[FluxSummary], values: dict[str, float]) -> None:
    try:
        summaries.append(FluxSummary(
            nu_ghz=values["nu_GHz"],
            frame_count=int(values["frame_count"]),
            mean_flux_jy=values["mean_flux_jy"],
            min_flux_jy=values["min_flux_jy"],
            max_flux_jy=values["max_flux_jy"],
            std_flux_jy=values["std_flux_jy"],
            target_flux_jy=values["target_flux_jy"],
            current_mdot=values["current_mdot_msun_per_year"],
            suggested_mdot_linear=values["suggested_mdot_linear"],
            suggested_mdot_sqrt=values["suggested_mdot_sqrt"],
        ))
    except KeyError:
        pass  # Incomplete summary blocks are skipped directly without falsifying results.


# ---------------------------------------------------------------------------
# Results directory scan
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ResultRecord:
    task: str
    index: int
    path: Path
    status: str
    fields: dict[str, str] = field(default_factory=dict)
    plot_status: str = ""
    plot_summary: str = ""
    integrity_reason: str = ""

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def signature_short(self) -> str:
        signature = self.fields.get("model_signature", "")
        return signature[:12] if signature else ""


def parse_config_txt(text: str) -> dict[str, str]:
    """Parse config.txt (key=value lines) in the results directory."""
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        fields[key.strip()] = value.strip()
    return fields


def _read_status(path: Path) -> str:
    try:
        value = ""
        for line in path.read_text(
            encoding="utf-8", errors="replace").splitlines():
            if not line:
                continue
            key = line.split("=", 1)[0] if "=" in line else line.split(" ", 1)[0]
            if key in {"data", "grid", "output", "analysis"}:
                continue
            value = line.split(" ", 1)[0]
        return value
    except OSError:
        return ""


def _plot_summary(plot: Path) -> str:
    """Prioritize reading the task list and use the actual product to be compatible with the old results."""
    labels: list[str] = []
    manifest = plot / "tasks.json"
    if manifest.is_file():
        try:
            value = json.loads(manifest.read_text(encoding="utf-8"))
            for item in value.get("tasks", []):
                if item.get("status") == "complete":
                    label = str(item.get("label", "")).strip()
                    if label:
                        labels.append(label)
            if value.get("status") == "failed":
                labels.append("任务失败")
        except (OSError, json.JSONDecodeError, TypeError):
            labels.append("清单损坏")
    artifacts = (
        ("积分观测量", any((plot / name).is_file()
                       for name in ("flux.csv", "lp.csv", "beta2.csv"))),
        ("EVPA", (plot / "evpa").is_dir() and
         any((plot / "evpa").glob("*.png"))),
        ("EVPA 视频", (plot / "evpa.mp4").is_file()),
        ("快慢光对齐", (plot / "time_alignment.csv").is_file()),
    )
    for label, exists in artifacts:
        if exists:
            labels.append(label)
    return "、".join(dict.fromkeys(labels))


def scan_results(output_root: Path) -> list[ResultRecord]:
    """The specification outputNNNN directory of each task in the scan result root directory.

    Status and configuration use status.txt / config.txt as the source of truth;
    Leave the corresponding fields blank for damaged or missing files and do not guess."""
    records: list[ResultRecord] = []
    if not output_root.is_dir():
        return records
    pattern = re.compile(r"^output(\d+)$")
    for task in TASK_DIR_NAMES:
        task_dir = output_root / task
        if not task_dir.is_dir():
            continue
        for child in sorted(task_dir.iterdir()):
            match = pattern.fullmatch(child.name)
            if not child.is_dir() or not match:
                continue
            config_path = child / "config.txt"
            fields: dict[str, str] = {}
            if config_path.is_file():
                try:
                    fields = parse_config_txt(
                        config_path.read_text(
                            encoding="utf-8", errors="replace"))
                except OSError:
                    fields = {}
            status = _read_status(child / "status.txt")
            records.append(ResultRecord(
                task=task,
                index=int(match.group(1)),
                path=child,
                status=status,
                fields=fields,
                plot_status=_read_status(child / "plot" / "status.txt"),
                plot_summary=_plot_summary(child / "plot"),
                integrity_reason="",
            ))
    return records


def format_electron(fields: dict[str, str]) -> str:
    code = fields.get("Config::ELECTRON", "")
    return ELECTRON_FROM_CODE.get(code, code)
