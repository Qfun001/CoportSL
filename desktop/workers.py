"""Freeze the Python post-processing Worker reused by the main program."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import sys
from typing import Callable

from .config import read_json, write_json


def emit(event_type: str, **fields: object) -> None:
    value = {"type": event_type, **fields}
    print(
        "COPORTSL_EVENT " +
        json.dumps(value, ensure_ascii=False, separators=(",", ":")),
        flush=True,
    )


def _cancel_file(job: dict[str, object]) -> Path | None:
    paths = job.get("paths")
    if not isinstance(paths, dict):
        return None
    value = paths.get("cancel_file")
    return Path(str(value)).resolve() if value else None


def _throw_if_cancelled(job: dict[str, object]) -> None:
    from tools.lib.cancel import throw_if_cancelled

    throw_if_cancelled(_cancel_file(job))


def run_postprocess(job: dict[str, object]) -> None:
    from tools.postprocess import postprocess_result

    result = Path(str(job["result"])).resolve()
    output = result / "plot"
    output.mkdir(parents=True, exist_ok=True)
    status = output / "status.txt"
    status.write_text("running\n", encoding="utf-8")
    emit("stage", name="postprocess")
    try:
        postprocess_result(
            result,
            formats=tuple(str(value) for value in job.get(
                "formats", ["pdf"])),
            workers=int(job.get("workers", 1)),
        )
    except Exception:
        status.write_text("failed\n", encoding="utf-8")
        raise
    status.write_text("complete\n", encoding="utf-8")
    emit("result", path=str(output), reused=False)


def run_evpa(job: dict[str, object]) -> None:
    from tools.lib.data import result_from_config
    from tools.lib.evpa import plot_evpa

    result_path = Path(str(job["result"])).resolve()
    result = result_from_config(result_path)
    formats = tuple(str(value) for value in job.get("formats", ["png", "pdf"]))
    workers = int(job.get("workers", 1))
    emit("stage", name="evpa")
    paths = plot_evpa(
        result=result,
        output=result_path / "plot",
        formats=formats,
        workers=workers,
        reuse=bool(job.get("reuse", True)),
        cancel_file=_cancel_file(job),
    )
    emit("result", path=str(result_path / "plot"), reused=False)
    print(f"Generated {len(paths)} EVPA files.")


def _paths(values) -> list[str]:
    if values is None:
        return []
    if isinstance(values, dict):
        values = values.values()
    if isinstance(values, (str, Path)):
        values = [values]
    return [str(Path(value).resolve()) for value in values]


def _finish(output: Path, values=None) -> None:
    paths = _paths(values)
    emit("result", path=str(output.resolve()), reused=False, files=paths)
    print(f"Generated {len(paths)} files.")


def run_observables(job: dict[str, object]) -> None:
    from tools.lib.calc_obs import calc_observables, radius_key
    from tools.lib.data import result_from_config
    from tools.lib.plot_obs import plot_beta2, plot_flux, plot_lp

    result_path = Path(str(job["result"])).resolve()
    output = Path(str(job.get("output", result_path / "plot"))).resolve()
    radii = tuple(
        None if value is None else float(value)
        for value in job.get("radii_muas", [None, 20.0])
    )
    formats = tuple(str(value) for value in job.get(
        "formats", ["png", "pdf"]))
    if not formats:
        raise ValueError("observables requires at least one figure format.")
    data_paths = {
        "flux": output / "flux.csv",
        "lp": output / "lp.csv",
        "beta2": output / "beta2.csv",
    }
    reuse_data = bool(job.get("reuse_data", False))
    if reuse_data and not all(path.is_file() for path in data_paths.values()):
        reuse_data = False
    if reuse_data:
        beta2_lines = data_paths["beta2"].read_text(
            encoding="utf-8").splitlines()
        if not beta2_lines:
            reuse_data = False
        else:
            beta2_fields = set(beta2_lines[0].split(","))
            required = {"beta2_abs", "beta2_angle_deg"}
            for radius in radii:
                if radius is not None:
                    key = radius_key(radius)
                    required.update({
                        f"beta2_{key}_abs",
                        f"beta2_{key}_angle_deg",
                    })
            reuse_data = required <= beta2_fields

    emit("stage", name="observables")
    if reuse_data:
        print(f"Reusing observable CSV files in {output}.")
    else:
        data_paths = calc_observables(
            result=result_from_config(result_path),
            output=output,
            nt_start=job.get("frame_start"),
            nt_end=job.get("frame_end"),
            radii_muas=radii,
            workers=int(job.get("workers", 1)),
            cancel_file=_cancel_file(job),
        )

    emit("stage", name="observables_plot")
    figure_paths = []
    figure_paths.extend(
        plot_flux(inputs=output, output=output, formats=formats))
    figure_paths.extend(
        plot_lp(inputs=output, output=output, formats=formats))
    figure_paths.extend(plot_beta2(
        inputs=output,
        output=output,
        radii_muas=radii,
        formats=formats,
    ))
    _finish(output, [*data_paths.values(), *figure_paths])


def run_align(job: dict[str, object]) -> None:
    from tools.lib.align import align_flux
    from tools.lib.data import result_from_config

    reference = Path(str(job["reference"])).resolve()
    target = Path(str(job["target"])).resolve()
    output = Path(str(job.get("output", target / "plot"))).resolve()
    emit("stage", name="align")
    result = align_flux(
        reference=reference / "plot",
        target=target / "plot",
        output=output,
        dt=result_from_config(reference).dt,
        max_lag=float(job.get("max_lag", 300.0)),
        min_overlap_fraction=float(job.get("min_overlap_fraction", 0.75)),
    )
    _finish(output, output / "time_alignment.csv")
    print(f"correlation={result.correlation:.17g}")


def run_compare(job: dict[str, object]) -> None:
    from tools.lib.plot_obs import plot_beta2, plot_flux, plot_lp

    reference = Path(str(job["reference"])).resolve()
    target = Path(str(job["target"])).resolve()
    output = Path(str(job.get("output", target / "plot"))).resolve()
    inputs = {
        str(job.get("reference_label", "快光")): reference / "plot",
        str(job.get("target_label", "慢光")): target / "plot",
    }
    formats = tuple(str(value) for value in job.get("formats", ["png"]))
    radii = tuple(
        None if value is None else float(value)
        for value in job.get("radii_muas", [None, 20.0])
    )
    emit("stage", name="compare")
    paths = []
    paths.extend(plot_flux(inputs=inputs, output=output, formats=formats))
    paths.extend(plot_lp(inputs=inputs, output=output, formats=formats))
    paths.extend(plot_beta2(
        inputs=inputs, output=output, radii_muas=radii, formats=formats))
    _finish(output, paths)


def run_result_diagnostics(job: dict[str, object]) -> None:
    """Generate exclusive scientific research graphs for Analysis, Slow or RegionError."""
    from tools.lib.data import read_key_values
    from tools.lib.region_contrib import plot_region_contribution
    from tools.lib.region_error import plot_region_error
    from tools.lib.time_offset import (
        plot_result_time_span,
        plot_selected_time_window,
    )
    from tools.postprocess import require_task, resolve_analysis

    result = Path(str(job["result"])).resolve()
    output = result / "plot"
    formats = tuple(str(value) for value in job.get("formats", ["png", "pdf"]))
    values = read_key_values(result / "config.txt")
    task = require_task(result, values)
    emit("stage", name="result_diagnostics")
    if task == "analysis":
        paths = plot_region_contribution(
            input=result, output=output, formats=formats)
    elif task == "slow":
        analysis = resolve_analysis(result, values)
        paths = []
        paths.extend(plot_selected_time_window(
            result=result, analysis=analysis, output=output, formats=formats))
        paths.extend(plot_result_time_span(
            result=result, output=output, formats=formats))
    elif task == "region_error":
        paths = plot_region_error(
            result=result, output=output, formats=formats)
    else:
        raise ValueError("任务专属图件只适用于 Analysis、Slow 和 RegionError。")
    _finish(output, paths)


def run_evpa_compare(job: dict[str, object]) -> None:
    from tools.lib.data import result_from_config
    from tools.lib.evpa_cmp import plot_evpa_comparison

    reference = Path(str(job["reference"])).resolve()
    target = Path(str(job["target"])).resolve()
    output = Path(str(job.get("output", target / "plot"))).resolve()
    times = tuple(float(value) for value in job.get("times", []))
    emit("stage", name="evpa_compare")
    path = plot_evpa_comparison(
        reference=result_from_config(reference, label=str(job.get(
            "reference_label", "快光"))),
        target=result_from_config(target, label=str(job.get(
            "target_label", "慢光"))),
        output=output,
        times=times,
        intensity_vmin=float(job.get("intensity_vmin", 0.0)),
        intensity_vmax=float(job.get("intensity_vmax", 1.0e-3)),
        stride=int(job.get("stride", 32)),
        line_length=float(job.get("line_length", 12.0)),
        min_i_fraction=float(job.get("min_i_fraction", 0.02)),
        reference_label=str(job.get("reference_label", "快光")),
        target_label=str(job.get("target_label", "慢光")),
    )
    _finish(output, path)


def _model_parameters(job: dict[str, object]):
    from tools.bhac.quantities import ModelParameters

    values = job.get("model", {})
    if not isinstance(values, dict):
        raise TypeError("model must be an object.")
    return ModelParameters(
        mbh=float(values.get("mbh", 6.5e9)),
        mdot=float(values.get("mdot", 2.46e-4)),
        mdot_sim=float(values.get("mdot_sim", 50.0)),
        r_low=float(values.get("r_low", 10.0)),
        r_high=float(values.get("r_high", 100.0)),
        beta0=float(values.get("beta0", 1.0)),
        p_min=float(values.get("p_min", 2.001)),
        p_max=float(values.get("p_max", 10.0)),
        gamma_ratio=float(values.get("gamma_ratio", 1.0e5)),
    )


def _bhac_parameters(job: dict[str, object]) -> dict[str, object]:
    if "plot_types" in job:
        plot_types = tuple(str(value) for value in job["plot_types"])
    elif bool(job.get("two_planes", False)):
        plot_types = ("xz_xy",)
    else:
        plot_types = tuple(str(value) for value in job.get(
            "planes", ["xz"]))
    plot_types = tuple(dict.fromkeys(plot_types))
    invalid = [
        value for value in plot_types
        if value not in {"xz", "xy", "xz_xy"}
    ]
    if invalid:
        raise ValueError(f"Unknown BHAC plot type: {invalid[0]}")
    if not plot_types:
        raise ValueError("At least one BHAC plot type is required.")
    return {
        "input": Path(str(job["input"])).resolve(),
        "grid": Path(str(job["grid"])).resolve(),
        "output": Path(str(job["output"])).resolve(),
        "frames": tuple(int(value) for value in job.get("frames", [])),
        "quantities": tuple(str(value) for value in job.get(
            "quantities", ["rho"])),
        "plot_types": plot_types,
        "limit": float(job.get("limit", 50.0)),
        "slice_width": float(job.get("slice_width", 0.1)),
        "draw_magnetic_field": bool(job.get("draw_magnetic_field", False)),
        "draw_jet_boundary": bool(job.get("draw_jet_boundary", True)),
        "sigma_level": float(job.get("sigma_level", 20.0)),
        "be_level": float(job.get("be_level", 1.02)),
        "formats": tuple(str(value) for value in job.get("formats", ["png"])),
        "profile_quantity": str(job.get("profile_quantity", "rho")),
        "profile_types": tuple(str(value) for value in job.get(
            "profile_types", ["radial", "theta"])),
        "profile_r": tuple(float(value) for value in job.get(
            "profile_r", [1.5, 50.0])),
        "profile_shell": tuple(float(value) for value in job.get(
            "profile_shell", [1.5, 10.0])),
        "profile_bins": int(job.get("profile_bins", 100)),
        "profile_smooth": int(job.get("profile_smooth", 5)),
        "profile_log": bool(job.get("profile_log", True)),
        "timeseries_radius": float(job.get("timeseries_radius", 2.5)),
        "timeseries_half_width": float(job.get(
            "timeseries_half_width", 0.25)),
        "cancel_file": _cancel_file(job),
        "model": _model_parameters(job),
    }


def run_bhac_plot(job: dict[str, object]) -> None:
    from tools.bhac_plot import plot_frames

    emit("stage", name="bhac_plot")
    parameters = _bhac_parameters(job)
    paths = plot_frames(parameters)
    _finish(Path(parameters["output"]), paths)


def run_bhac_profile(job: dict[str, object]) -> None:
    from tools.bhac_plot import plot_profiles

    emit("stage", name="bhac_profile")
    parameters = _bhac_parameters(job)
    paths = plot_profiles(parameters)
    _finish(Path(parameters["output"]), paths)


def run_bhac_video(job: dict[str, object]) -> None:
    from tools.bhac_plot import make_quantity_movie

    emit("stage", name="bhac_video")
    parameters = _bhac_parameters(job)
    path = make_quantity_movie(
        parameters,
        str(job.get("quantity", "rho")),
        str(job.get("plane", "xz")),
    )
    _finish(path.parent, [path])


def run_bhac_timeseries(job: dict[str, object]) -> None:
    from tools.bhac.timeseries import make_timeseries

    emit("stage", name="bhac_timeseries")
    parameters = _bhac_parameters(job)
    paths = make_timeseries(parameters)
    _finish(Path(parameters["output"]) / "timeseries", paths)


def run_interpolation(job: dict[str, object], action: str) -> None:
    from tools import interp_err

    emit("stage", name=action)
    parameters = {
        "primitive_input": Path(str(job.get(
            "input", job.get("primitive_input", ".")))).resolve(),
        "grid": Path(str(job.get("grid", "."))).resolve(),
        "primitive_output": Path(str(job.get(
            "output", job.get("primitive_output", ".")))).resolve(),
        "observation_input": Path(str(job.get(
            "input", job.get("observation_input", ".")))).resolve(),
        "observation_output": Path(str(job.get(
            "output", job.get("observation_output", ".")))).resolve(),
        "dt": tuple(float(value) for value in job.get(
            "dt", [0.2, 0.5, 1.0, 2.0, 4.0])),
        "shells": tuple(
            tuple(float(edge) for edge in shell)
            for shell in job.get("shells", [[1.5, 5.0], [5.0, 10.0]])
        ),
        "blocks": job.get("blocks"),
        "load_workers": int(job.get("load_workers", 1)),
        "workers": int(job.get("workers", 1)),
        "formats": tuple(str(value) for value in job.get("formats", ["png"])),
        "radial_log": bool(job.get("radial_log", False)),
        "nt0": job.get("frame_start"),
        "nt1": job.get("frame_end"),
    }
    actions: dict[str, Callable[[dict[str, object]], None]] = {
        "interp_primitive": interp_err.calculate_primitive,
        "plot_primitive_error": interp_err.plot_primitive,
        "interp_observation": interp_err.calculate_observation,
        "plot_observation_error": interp_err.plot_observation,
    }
    actions[action](parameters)
    output_key = (
        "primitive_output" if "primitive" in action
        else "observation_output"
    )
    _finish(Path(parameters[output_key]))


def run_benchmark_plot(job: dict[str, object]) -> None:
    from tools.benchmark import plot_benchmark

    result = Path(str(job["result"])).resolve()
    output = Path(str(job.get("output", result / "plot"))).resolve()
    modes_value = job.get("modes")
    modes = (
        None if modes_value is None
        else tuple(str(value) for value in modes_value)
    )
    emit("stage", name="benchmark_plot")
    paths = plot_benchmark(
        input_dir=result,
        output_dir=output,
        modes=modes,
        formats=tuple(str(value) for value in job.get("formats", ["png"])),
        time_log=bool(job.get("time_log", False)),
        rate_log=bool(job.get("rate_log", False)),
        memory_unit=str(job.get("memory_unit", "GiB")),
    )
    _finish(output, paths)


def run_evpa_video(job: dict[str, object]) -> None:
    from tools.lib.media import make_video

    result = Path(str(job["result"])).resolve()
    output = result / "plot"
    images = sorted((output / "evpa").glob("*.png"))
    canvas_value = job.get("canvas_size", [1920, 1080])
    canvas = tuple(int(value) for value in canvas_value)
    if len(canvas) != 2:
        raise ValueError("canvas_size must contain width and height.")
    emit("stage", name="evpa_video")
    path = make_video(
        images=images,
        output=output / "evpa.mp4",
        fps=float(job.get("fps", 30.0)),
        canvas_size=(canvas[0], canvas[1]),
        cancel_file=_cancel_file(job),
    )
    _finish(output, [path])


def run_error_scan(job: dict[str, object]) -> None:
    from tools.lib.data import result_from_config
    from tools.lib.slow_error import calc_slow_errors, plot_slow_errors

    slow_paths = [Path(str(value)).resolve() for value in job["slow_results"]]
    values_list = list(job["values"])
    if len(slow_paths) < 2 or len(values_list) != len(slow_paths):
        raise ValueError(
            "error_scan requires at least two results and one value per result.")
    reference = str(job.get("reference", slow_paths[-1].name))
    fast = result_from_config(Path(str(job["fast_result"])).resolve())
    output = Path(str(job["output"])).resolve()
    runs = {path.name: path for path in slow_paths}
    alignments = {name: path / "plot" / "time_alignment.csv"
                  for name, path in runs.items()}
    labels = {name: name for name in runs}
    values = {path.name: value for path, value in zip(slow_paths, values_list)}
    emit("stage", name="error_scan")
    calc_slow_errors(
        runs=runs,
        alignments=alignments,
        labels=labels,
        values=values,
        output=output,
        reference=reference,
        nt0=fast.nt0,
        t0=fast.t0,
        dt=fast.dt,
        time_start=float(job["time_start"]),
        time_end=float(job["time_end"]),
        workers=int(job.get("workers", 1)),
    )
    paths = plot_slow_errors(
        output=output,
        xlabel=str(job.get("xlabel", "控制变量")),
        formats=tuple(str(value) for value in job.get("formats", ["png"])),
    )
    _finish(output, paths)


def _actions() -> dict[str, Callable[[dict[str, object]], None]]:
    return {
        "postprocess": run_postprocess,
        "evpa": run_evpa,
        "observables": run_observables,
        "align": run_align,
        "compare": run_compare,
        "result_diagnostics": run_result_diagnostics,
        "evpa_compare": run_evpa_compare,
        "bhac_plot": run_bhac_plot,
        "bhac_profile": run_bhac_profile,
        "bhac_video": run_bhac_video,
        "bhac_timeseries": run_bhac_timeseries,
        "benchmark_plot": run_benchmark_plot,
        "evpa_video": run_evpa_video,
        "error_scan": run_error_scan,
    }


def run_action(kind: str, job: dict[str, object]) -> None:
    _throw_if_cancelled(job)
    action = _actions().get(kind)
    if action is not None:
        action(job)
        return
    if kind in {
        "interp_primitive", "plot_primitive_error",
        "interp_observation", "plot_observation_error",
    }:
        run_interpolation(job, kind)
        return
    raise ValueError(f"未知内部 Python Worker：{kind}")


def _manifest_value(
    tasks: list[dict[str, object]],
    *,
    status: str,
    current: int,
    error: str = "",
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": status,
        "updated": datetime.now().isoformat(timespec="seconds"),
        "current": current,
        "error": error,
        "tasks": tasks,
    }


def run_task_batch(job: dict[str, object]) -> None:
    """Execute selected plotting tasks in dependency order and update the manifest."""
    raw_tasks = job.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise ValueError("请至少勾选一个需要运行的任务。")
    tasks: list[dict[str, object]] = []
    batch_cancel = _cancel_file(job)
    for item in raw_tasks:
        if not isinstance(item, dict) or not isinstance(item.get("job"), dict):
            raise TypeError("批作业中的每个任务都必须包含 kind 和 job。")
        item_job = dict(item["job"])
        if batch_cancel is not None:
            paths = item_job.setdefault("paths", {})
            if isinstance(paths, dict):
                paths.setdefault("cancel_file", str(batch_cancel))
        tasks.append({
            "kind": str(item.get("kind", "")),
            "label": str(item.get("label", item.get("kind", ""))),
            "status": "pending",
            "job": item_job,
        })
    manifest = Path(str(job["manifest"])).resolve()
    manifest.parent.mkdir(parents=True, exist_ok=True)
    write_json(manifest, _manifest_value(
        tasks, status="running", current=0))
    total = len(tasks)
    for index, item in enumerate(tasks, 1):
        _throw_if_cancelled(job)
        item["status"] = "running"
        write_json(manifest, _manifest_value(
            tasks, status="running", current=index))
        emit("progress", current=index - 1, total=total)
        emit("stage", name=str(item["label"]))
        try:
            run_action(str(item["kind"]), item["job"])
        except Exception as error:
            item["status"] = "failed"
            item["error"] = str(error)
            write_json(manifest, _manifest_value(
                tasks,
                status="failed",
                current=index,
                error=str(error),
            ))
            raise
        item["status"] = "complete"
        emit("progress", current=index, total=total)
    write_json(manifest, _manifest_value(
        tasks, status="complete", current=total))
    _finish(manifest.parent, manifest)


def run_internal(kind: str, path: Path) -> int:
    try:
        job = read_json(path)
        if kind == "task_batch":
            run_task_batch(job)
        else:
            run_action(kind, job)
        return 0
    except Exception as error:
        emit("error", message=str(error))
        print(f"Python Worker failed: {error}", file=sys.stderr)
        return 1
