"""Common post-processing pipeline around `Case`."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from .align import align_flux
from .calc_obs import calc_observables
from .evpa import plot_evpa
from .evpa_cmp import plot_evpa_comparison
from .media import make_video
from .paths import Case, ProjectPaths, case_name, require_light
from .plot_obs import plot_beta2, plot_flux, plot_lp
from .slow_error import calc_slow_errors, plot_slow_errors

CaseItems = Case | Iterable[Case]


def case_tuple(items: CaseItems) -> tuple[Case, ...]:
    """Unify single or multiple cases into tuples."""
    if isinstance(items, Case):
        return (items,)
    return tuple(items)


def result_for(case: Case, paths: ProjectPaths):
    """Read the result metadata corresponding to the case."""
    if case.light == "fast":
        return paths.fast_result(case)
    return paths.slow_result(case)


def plot_path(case: Case, paths: ProjectPaths) -> Path:
    """Return the plot directory for a case."""
    if case.light == "fast":
        return paths.fast_plot_path(case)
    return paths.slow_plot_path(case)


def default_output(items: tuple[Case, ...], paths: ProjectPaths) -> Path:
    """Write a single case group to its plot directory; require an explicit output directory for multiple groups."""
    if len(items) == 1:
        return plot_path(items[0], paths)
    raise ValueError("Multiple cases require an explicit output path.")


def calc_cases(
    *,
    items: CaseItems,
    paths: ProjectPaths,
    radii_muas: tuple[float | None, ...] = (None,),
    workers: int = 1,
) -> None:
    """Compute observables for one or more production results."""
    for item in case_tuple(items):
        calc_observables(
            result=result_for(item, paths),
            output=plot_path(item, paths),
            radii_muas=radii_muas,
            workers=workers,
        )


def align_cases(
    *,
    items: CaseItems,
    paths: ProjectPaths,
    reference: Case,
    max_lag: float,
    min_overlap_fraction: float = 0.75,
) -> None:
    """Generate `time_alignment.csv` for one or more slow-light cases."""
    require_light(reference, "fast")
    fast = paths.fast_result(reference)
    for item in case_tuple(items):
        require_light(item, "slow")
        align_flux(
            reference=paths.fast_plot_path(reference),
            target=paths.slow_plot_path(item),
            output=paths.slow_plot_path(item),
            dt=fast.dt,
            max_lag=max_lag,
            min_overlap_fraction=min_overlap_fraction,
        )


def case_inputs(items: tuple[Case, ...], paths: ProjectPaths) -> Path | dict[str, Path]:
    """Return input directories for plotting one or more case groups."""
    if len(items) == 1:
        return plot_path(items[0], paths)
    return {case_name(item): plot_path(item, paths) for item in items}


def plot_cases_flux(
    *,
    items: CaseItems,
    paths: ProjectPaths,
    output: Path | None = None,
    formats: tuple[str, ...] = ("png",),
    time_start: float | None = None,
    time_end: float | None = None,
) -> list[Path]:
    """Plot the flux curve for one or more cases."""
    current = case_tuple(items)
    return plot_flux(
        inputs=case_inputs(current, paths),
        output=default_output(current, paths) if output is None else output,
        formats=formats,
        time_start=time_start,
        time_end=time_end,
    )


def plot_cases_lp(
    *,
    items: CaseItems,
    paths: ProjectPaths,
    output: Path | None = None,
    formats: tuple[str, ...] = ("png",),
    time_start: float | None = None,
    time_end: float | None = None,
) -> list[Path]:
    """Plot linear polarization curves for one or more cases."""
    current = case_tuple(items)
    return plot_lp(
        inputs=case_inputs(current, paths),
        output=default_output(current, paths) if output is None else output,
        formats=formats,
        time_start=time_start,
        time_end=time_end,
    )


def plot_cases_beta2(
    *,
    items: CaseItems,
    paths: ProjectPaths,
    output: Path | None = None,
    radii_muas: tuple[float | None, ...] = (None,),
    formats: tuple[str, ...] = ("png",),
    time_start: float | None = None,
    time_end: float | None = None,
) -> list[Path]:
    """Plot beta2 curves for one or more cases."""
    current = case_tuple(items)
    return plot_beta2(
        inputs=case_inputs(current, paths),
        output=default_output(current, paths) if output is None else output,
        radii_muas=radii_muas,
        formats=formats,
        time_start=time_start,
        time_end=time_end,
    )


def pair_inputs(item: Case, reference: Case, paths: ProjectPaths) -> dict[str, Path]:
    """Return plot input directories for the fast-light reference and current slow-light cases."""
    require_light(reference, "fast")
    require_light(item, "slow")
    fast = paths.fast_result(reference)
    slow = paths.slow_result(item)
    return {
        fast.label: paths.fast_plot_path(reference),
        slow.label: paths.slow_plot_path(item),
    }


def plot_pair_flux(
    *,
    items: CaseItems,
    paths: ProjectPaths,
    reference: Case,
    formats: tuple[str, ...] = ("png",),
    time_start: float | None = None,
    time_end: float | None = None,
) -> list[Path]:
    """Plot the flux of one or more slow-light cases versus a fast-light baseline."""
    outputs = []
    for item in case_tuple(items):
        outputs.extend(plot_flux(
            inputs=pair_inputs(item, reference, paths),
            output=paths.slow_plot_path(item),
            formats=formats,
            time_start=time_start,
            time_end=time_end,
        ))
    return outputs


def plot_pair_lp(
    *,
    items: CaseItems,
    paths: ProjectPaths,
    reference: Case,
    formats: tuple[str, ...] = ("png",),
    time_start: float | None = None,
    time_end: float | None = None,
) -> list[Path]:
    """Plot linear polarization of one or more slow-light cases against a fast-light baseline."""
    outputs = []
    for item in case_tuple(items):
        outputs.extend(plot_lp(
            inputs=pair_inputs(item, reference, paths),
            output=paths.slow_plot_path(item),
            formats=formats,
            time_start=time_start,
            time_end=time_end,
        ))
    return outputs


def plot_pair_beta2(
    *,
    items: CaseItems,
    paths: ProjectPaths,
    reference: Case,
    radii_muas: tuple[float | None, ...] = (None,),
    formats: tuple[str, ...] = ("png",),
    time_start: float | None = None,
    time_end: float | None = None,
) -> list[Path]:
    """Plot beta2 of one or more slow-light cases versus the fast-light baseline."""
    outputs = []
    for item in case_tuple(items):
        outputs.extend(plot_beta2(
            inputs=pair_inputs(item, reference, paths),
            output=paths.slow_plot_path(item),
            radii_muas=radii_muas,
            formats=formats,
            time_start=time_start,
            time_end=time_end,
        ))
    return outputs


def plot_pair_evpa(
    *,
    items: CaseItems,
    paths: ProjectPaths,
    reference: Case,
    times: tuple[float, ...],
    intensity_vmin: float = 0.0,
    intensity_vmax: float = 1.0e-3,
    intensity_log: bool = False,
    stride: int = 32,
    line_length: float = 12.0,
    min_i_fraction: float = 0.02,
    flip_u: bool = True,
    flip_rows: bool = True,
    scale_bar_uas: float | None = 20.0,
) -> list[Path]:
    """Plot the EVPA of one or more slow-light cases versus the fast-light baseline."""
    outputs = []
    for item in case_tuple(items):
        require_light(reference, "fast")
        require_light(item, "slow")
        outputs.append(plot_evpa_comparison(
            reference=paths.fast_result(reference),
            target=paths.slow_result(item),
            output=paths.slow_plot_path(item),
            times=times,
            intensity_vmin=intensity_vmin,
            intensity_vmax=intensity_vmax,
            intensity_log=intensity_log,
            stride=stride,
            line_length=line_length,
            min_i_fraction=min_i_fraction,
            flip_u=flip_u,
            flip_rows=flip_rows,
            scale_bar_uas=scale_bar_uas,
        ))
    return outputs


def plot_evpa_cases(
    *,
    items: CaseItems,
    paths: ProjectPaths,
    **kwargs,
) -> None:
    """Plot the EVPA of one or more cases frame by frame."""
    for item in case_tuple(items):
        plot_evpa(result=result_for(item, paths), output=plot_path(item, paths), **kwargs)


def make_evpa_videos(
    *,
    items: CaseItems,
    paths: ProjectPaths,
    fps: float = 30.0,
) -> None:
    """Synthesize EVPA image sequences from one or more cases into a video."""
    for item in case_tuple(items):
        output = plot_path(item, paths)
        path = make_video(
            images=sorted((output / "evpa").glob("*.png")),
            output=output / "evpa.mp4",
            fps=fps,
        )
        print(f"video: {path}")


def calc_case_errors(
    *,
    items: CaseItems,
    reference: Case,
    fast: Case,
    values: dict[str, float | str],
    paths: ProjectPaths,
    output: Path,
    time_start: float,
    time_end: float,
    workers: int = 1,
) -> list[dict[str, float | int | str]]:
    """Computes a set of slow-light control variable errors by explicit run number."""
    current = case_tuple(items)
    for item in current:
        require_light(item, "slow")
        if item.run not in values:
            raise KeyError(f"Missing scan value for {item.run}.")
    require_light(reference, "slow")
    require_light(fast, "fast")
    baseline = paths.fast_result(fast)
    return calc_slow_errors(
        runs={item.run: paths.slow_result_path(item) for item in current},
        alignments={item.run: paths.slow_alignment_path(item) for item in current},
        labels={item.run: case_name(item) for item in current},
        values=values,
        output=output,
        reference=reference.run,
        nt0=baseline.nt0,
        t0=baseline.t0,
        dt=baseline.dt,
        time_start=time_start,
        time_end=time_end,
        workers=workers,
    )


def plot_case_errors(
    *,
    output: Path,
    xlabel: str,
    formats: tuple[str, ...] = ("png",),
) -> list[Path]:
    """Plot an existing general control variable error sweep."""
    return plot_slow_errors(output=output, xlabel=xlabel, formats=formats)
