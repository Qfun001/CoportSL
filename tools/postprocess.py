"""The only fixed postprocessing entry called after C++ GRRT completes."""

from __future__ import annotations

import os
from pathlib import Path
import sys

if __package__:
    from .lib.align import align_flux
    from .lib.calc_obs import calc_observables, reusable_observables
    from .lib.data import read_key_values, read_status_paths, result_from_config
    from .lib.paths import find_fast_result
    from .lib.plot_obs import plot_beta2, plot_flux, plot_lp
    from .lib.region_contrib import plot_region_contribution
    from .lib.region_error import plot_region_error
    from .lib.time_offset import plot_result_time_span, plot_selected_time_window
else:
    from lib.align import align_flux
    from lib.calc_obs import calc_observables, reusable_observables
    from lib.data import read_key_values, read_status_paths, result_from_config
    from lib.paths import find_fast_result
    from lib.plot_obs import plot_beta2, plot_flux, plot_lp
    from lib.region_contrib import plot_region_contribution
    from lib.region_error import plot_region_error
    from lib.time_offset import plot_result_time_span, plot_selected_time_window

TASK_DIRECTORIES = {
    "analysis": "analysis",
    "fast": "fast",
    "slow": "slow",
    "region_error": "region_error",
}


def require_task(result: Path, values: dict[str, str]) -> str:
    """Use parent directory and configuration fields to confirm tasks together to avoid mishandling other directories."""
    task = values.get("Config::TASK")
    if task not in TASK_DIRECTORIES:
        raise ValueError(f"Unknown Config::TASK in {result / 'config.txt'}: {task!r}")
    if result.parent.name != TASK_DIRECTORIES[task]:
        raise ValueError(
            f"Result parent {result.parent.name!r} does not match task {task!r}.")
    return task


def resolve_analysis(result: Path, values: dict[str, str]) -> Path:
    """Resolve slow-light analysis relative paths that can be migrated with the entire result directory."""
    text = read_status_paths(result).get("analysis")
    if not text:
        raise KeyError("Missing analysis path in slow result status.txt.")
    path = (result / Path(text)).resolve()
    if path.parent.name != "analysis":
        raise ValueError(f"analysis path does not resolve to result/analysis: {text}")
    analysis_values = read_key_values(path / "config.txt")
    if analysis_values.get("analysis_signature") != values.get("analysis_signature"):
        raise ValueError("Slow result and analysis path signatures do not match.")
    return path


def observable_plots(
    result: Path,
    output: Path,
    *,
    formats: tuple[str, ...] = ("pdf",),
    workers: int = 1,
) -> None:
    """Reuse or calculate three types of integral quantities and generate plots in the selected format."""
    metadata = result_from_config(result)
    paths = reusable_observables(
        result=metadata,
        output=output,
        radii_muas=(None,),
    )
    if paths is None:
        calc_observables(
            result=metadata,
            output=output,
            radii_muas=(None,),
            workers=workers,
        )
    else:
        print(f"Reusing observable CSV files in {output}.")
    plot_flux(inputs=output, output=output, formats=formats)
    plot_lp(inputs=output, output=output, formats=formats)
    plot_beta2(
        inputs=output,
        output=output,
        radii_muas=(None,),
        formats=formats,
    )


def match_fast(
    result: Path,
    values: dict[str, str],
    output: Path,
    *,
    workers: int = 1,
) -> Path | None:
    """Match complete fast rays, write relative references and complete fast and slow flux alignment."""
    fast = find_fast_result(result, values.get("model_signature"))
    if fast is None:
        print("No complete fast-light result matches model_signature.")
        target = result / "fast.txt"
        if target.exists():
            target.unlink()
        return None

    relative = os.path.relpath(fast, result).replace(os.sep, "/")
    fast_plot = fast / "plot"
    fast_metadata = result_from_config(fast, label="Fast light")
    if reusable_observables(
        result=fast_metadata,
        output=fast_plot,
        radii_muas=(None,),
    ) is None:
        calc_observables(
            result=fast_metadata,
            output=fast_plot,
            radii_muas=(None,),
            workers=workers,
        )
    left = float(values["SlowLight::LEFT"])
    right = float(values["SlowLight::RIGHT"])
    alignment = align_flux(
        reference=fast_plot,
        target=output,
        output=output,
        dt=float(values["Input::DT"]),
        search_left=left,
        search_right=right,
        min_overlap_fraction=0.75,
    )
    (result / "fast.txt").write_text(
        f"path={relative}\n"
        f"slow_time_shift_rg_over_c={alignment.time_shift:.17g}\n"
        f"correlation={alignment.correlation:.17g}\n"
        f"search_left_rg_over_c={alignment.search_left:.17g}\n"
        f"search_right_rg_over_c={alignment.search_right:.17g}\n"
        f"min_overlap_fraction={alignment.min_overlap_fraction:.17g}\n"
        f"overlap_frames={alignment.overlap_frames}\n"
        f"dt_rg_over_c={alignment.dt:.17g}\n"
    )
    print(f"Matched fast-light result: {relative}")
    return fast


def postprocess_result(
    result: Path,
    *,
    formats: tuple[str, ...] = ("pdf",),
    workers: int = 1,
) -> None:
    """Generate a fixed set of products corresponding to the task according to the unique current configuration semantics."""
    if not formats:
        raise ValueError("postprocess requires at least one figure format.")
    result = result.resolve()
    values = read_key_values(result / "config.txt")
    task = require_task(result, values)
    output = result / "plot"
    output.mkdir(parents=True, exist_ok=True)

    if task == "analysis":
        plot_region_contribution(
            input=result, output=output, formats=formats)
    elif task in {"fast", "slow"}:
        observable_plots(result, output, formats=formats, workers=workers)
        if task == "slow":
            analysis = resolve_analysis(result, values)
            plot_selected_time_window(
                result=result,
                analysis=analysis,
                output=output,
                formats=formats,
            )
            plot_result_time_span(
                result=result, output=output, formats=formats)
            match_fast(result, values, output, workers=workers)
    else:
        plot_region_error(result=result, output=output, formats=formats)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python tools/postprocess.py <result_dir>")
    result = Path(sys.argv[1])
    output = result / "plot"
    output.mkdir(parents=True, exist_ok=True)
    status = output / "status.txt"
    status.write_text("running\n")
    try:
        postprocess_result(result)
    except Exception:
        status.write_text("failed\n")
        raise
    status.write_text("complete\n")


if __name__ == "__main__":
    main()
