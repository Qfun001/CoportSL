"""Compare the I/Q/U/V image errors caused by slow light area and time window control variables."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from .data import find_frames, load_csv_map, read_rows, stokes_path, write_rows
from .image_error import image_error, temporal_mean_std
from .parallel import process_tasks
from .save_fig import save_figure

RunId = str


def has_stokes(directory: Path, nt: int) -> bool:
    """Checks whether all four Stokes components of the specified frame are present."""
    return all(stokes_path(directory, name, nt).exists() for name in ("I", "Q", "U", "V"))


def load_stokes(directory: Path, nt: int) -> dict[str, np.ndarray]:
    """Read a full Stokes image from a slow-light result."""
    return {
        name: load_csv_map(stokes_path(directory, name, nt))
        for name in ("I", "Q", "U", "V")
    }


def read_alignment(path: Path) -> dict[str, float | int]:
    """Read the integer frame displacement and corresponding time translation output by `align_flux`."""
    if not path.exists():
        raise FileNotFoundError(f"Missing time alignment file: {path}. Run align_flux for this case first.")
    rows = read_rows(path)
    if not rows:
        raise ValueError(f"No time-alignment rows found in {path}.")
    row = rows[0]
    return {
        "lag_steps": int(round(float(row["lag_steps"]))),
        "time_shift": float(row["target_time_shift_rg_over_c"]),
    }


def calibrated_time(nt: int, *, nt0: int, t0: float, dt: float, time_shift: float) -> float:
    """Convert raw frame numbers to calibrated physical time."""
    return t0 + (nt - nt0) * dt + time_shift


def frame_at_calibrated_time(
    time: float,
    *,
    nt0: int,
    t0: float,
    dt: float,
    time_shift: float,
) -> int:
    """Convert the calibrated physical time to the nearest original frame number."""
    return int(round(nt0 + (time - time_shift - t0) / dt))


def compare_slow_frame(
    *,
    calibrated_t: float,
    nt: int,
    reference_nt: int,
    run: RunId,
    label: str,
    scan_value: float | str,
    value: dict[str, np.ndarray],
    reference: dict[str, np.ndarray],
    reference_run: RunId,
    reference_label: str,
) -> dict[str, float | int | str]:
    """Calculate the common denominator I/Q/U/V error of a single frame candidate slow light relative to the reference slow light."""
    stokes_error = image_error(
        np.stack([value[name] for name in ("I", "Q", "U", "V")]),
        np.stack([reference[name] for name in ("I", "Q", "U", "V")]),
    )

    return {
        "time_rg_over_c": calibrated_t,
        "nt": nt,
        "reference_nt": reference_nt,
        "run": run,
        "label": label,
        "scan_value": scan_value,
        "reference_run": reference_run,
        "reference_label": reference_label,
        "I_l1": float(stokes_error[0]),
        "Q_l1": float(stokes_error[1]),
        "U_l1": float(stokes_error[2]),
        "V_l1": float(stokes_error[3]),
    }


def compare_slow_frame_set(
    task: tuple[
        float,
        int,
        Path,
        list[tuple[RunId, str, float | str, int, Path]],
        tuple[RunId, str, float | str],
    ],
) -> list[dict[str, float | int | str]]:
    """Compares all candidate cases on a calibrated time for a multi-process task call."""
    calibrated_t, reference_nt, reference_dir, candidates, reference_case = task
    reference_run, reference_label, reference_value = reference_case
    reference = load_stokes(reference_dir, reference_nt)
    rows = [
        compare_slow_frame(
            calibrated_t=calibrated_t,
            nt=reference_nt,
            reference_nt=reference_nt,
            run=reference_run,
            label=reference_label,
            scan_value=reference_value,
            value=reference,
            reference=reference,
            reference_run=reference_run,
            reference_label=reference_label,
        )
    ]
    for run, label, scan_value, nt, directory in candidates:
        rows.append(
            compare_slow_frame(
                calibrated_t=calibrated_t,
                nt=nt,
                reference_nt=reference_nt,
                run=run,
                label=label,
                scan_value=scan_value,
                value=load_stokes(directory, nt),
                reference=reference,
                reference_run=reference_run,
                reference_label=reference_label,
            )
        )
    return rows


def metrics() -> tuple[str, ...]:
    """Return the four image errors aggregated for a production slow-light control-variable scan."""
    return ("I_l1", "Q_l1", "U_l1", "V_l1")


def summarize_errors(rows: list[dict[str, float | int | str]]) -> list[dict[str, float | int | str]]:
    """The time average and sample standard deviation of each error amount are summarized by candidate slow-light cases."""
    summary = []
    runs = sorted({str(row["run"]) for row in rows})
    for run in runs:
        current = [row for row in rows if str(row["run"]) == run]
        if not current:
            continue
        for metric in metrics():
            values = np.array([float(row[metric]) for row in current])
            mean, std = temporal_mean_std(values)
            summary.append({
                "run": run,
                "label": str(current[0]["label"]),
                "scan_value": current[0]["scan_value"],
                "reference_run": str(current[0]["reference_run"]),
                "reference_label": str(current[0]["reference_label"]),
                "metric": metric,
                "n_frames": len(current),
                "time_start_rg_over_c": float(min(float(row["time_rg_over_c"]) for row in current)),
                "time_end_rg_over_c": float(max(float(row["time_rg_over_c"]) for row in current)),
                "mean": float(mean),
                "std": float(std),
            })
    return summary


def summary_value(
    rows: list[dict[str, float | int | str]],
    *,
    run: RunId,
    metric: str,
    field: str,
) -> float:
    """Get the statistics for a case from the summary table."""
    for row in rows:
        if str(row["run"]) == run and str(row["metric"]) == metric:
            return float(row[field])
    raise KeyError(f"Missing {field} for {run} / {metric}.")


def scan_axis(summary: list[dict[str, float | int | str]]) -> tuple[
    list[RunId],
    list[float | int],
    list[str],
    bool,
]:
    """Generates the horizontal axis of the error sweep plot."""
    rows = {str(row["run"]): row for row in summary}
    try:
        numeric = {run: float(row["scan_value"]) for run, row in rows.items()}
    except (TypeError, ValueError):
        runs = sorted(rows, key=lambda run: str(rows[run]["scan_value"]))
        return runs, list(range(len(runs))), [str(rows[run]["scan_value"]) for run in runs], True
    runs = sorted(rows, key=numeric.__getitem__)
    return runs, [numeric[run] for run in runs], [str(rows[run]["scan_value"]) for run in runs], False


def plot_metric_scan(
    output: Path,
    summary: list[dict[str, float | int | str]],
    *,
    xlabel: str,
    metric_items: tuple[tuple[str, str], ...],
    formats: tuple[str, ...] = ("png",),
) -> list[Path]:
    """Plot the time mean and standard deviation of the errors for the four Stokes images."""
    runs, x_values, x_labels, categorical = scan_axis(summary)
    figure, axes = plt.subplots(2, 2, figsize=(8.8, 6.2), constrained_layout=True)
    for axis, (metric, ylabel) in zip(axes.flat, metric_items):
        means = [
            summary_value(summary, run=run, metric=metric, field="mean")
            for run in runs
        ]
        stds = [
            summary_value(summary, run=run, metric=metric, field="std")
            for run in runs
        ]
        axis.errorbar(
            x_values,
            means,
            yerr=stds,
            marker="o",
            linewidth=1.4,
            capsize=3,
        )
        axis.set_ylabel(ylabel)
        axis.grid(alpha=0.25)
        axis.set_ylim(bottom=0.0)
        if categorical:
            axis.set_xticks(x_values, x_labels)
    for axis in axes[-1, :]:
        axis.set_xlabel(xlabel)
    paths = save_figure(figure, output, formats, dpi=180)
    plt.close(figure)
    return paths


def plot_error_scan(
    output: Path,
    summary: list[dict[str, float | int | str]],
    *,
    xlabel: str,
    formats: tuple[str, ...] = ("png",),
) -> list[Path]:
    """Plot the unique I/Q/U/V time-averaged error and its time standard deviation."""
    image_metrics = (
        ("I_l1", r"$\langle\epsilon_I^{L_1}\rangle$"),
        ("Q_l1", r"$\langle\epsilon_Q^{L_1}\rangle$"),
        ("U_l1", r"$\langle\epsilon_U^{L_1}\rangle$"),
        ("V_l1", r"$\langle\epsilon_V^{L_1}\rangle$"),
    )
    available = {str(row["metric"]) for row in summary}
    missing = [metric for metric, _ in image_metrics if metric not in available]
    if missing:
        raise ValueError(
            "errors.csv is missing current I/Q/U/V metrics: " +
            ", ".join(missing) + ".")
    return plot_metric_scan(
        output / "error_img",
        summary,
        xlabel=xlabel,
        metric_items=image_metrics,
        formats=formats,
    )


def load_alignments(alignments: dict[RunId, Path]) -> dict[RunId, dict[str, float | int]]:
    """Read the time calibration results of all participating comparison cases."""
    return {case: read_alignment(path) for case, path in alignments.items()}


def build_tasks(
    *,
    runs: dict[RunId, Path],
    alignments: dict[RunId, dict[str, float | int]],
    labels: dict[RunId, str],
    values: dict[RunId, float | str],
    reference: RunId,
    nt0: int,
    t0: float,
    dt: float,
    time_start: float,
    time_end: float,
) -> list[tuple[
    float,
    int,
    Path,
    list[tuple[RunId, str, float | str, int, Path]],
    tuple[RunId, str, float | str],
]]:
    """A frame-by-frame comparison task is constructed on the calibrated time grid of the reference case."""
    reference_dir = runs[reference]
    reference_shift = float(alignments[reference]["time_shift"])
    tasks = []
    for reference_nt in find_frames(reference_dir, None, None):
        time = calibrated_time(reference_nt, nt0=nt0, t0=t0, dt=dt, time_shift=reference_shift)
        if time < time_start or time > time_end:
            continue

        candidates = []
        for case, directory in sorted(runs.items()):
            if case == reference:
                continue
            shift = float(alignments[case]["time_shift"])
            nt = frame_at_calibrated_time(time, nt0=nt0, t0=t0, dt=dt, time_shift=shift)
            if has_stokes(directory, nt):
                candidates.append((case, labels[case], values[case], nt, directory))

        if candidates:
            tasks.append((
                time,
                reference_nt,
                reference_dir,
                candidates,
                (reference, labels[reference], values[reference]),
            ))

    if not tasks:
        raise ValueError("No aligned frames remain in the requested time range.")
    return tasks


def calc_slow_errors(
    *,
    runs: dict[RunId, Path],
    alignments: dict[RunId, Path],
    labels: dict[RunId, str],
    values: dict[RunId, float | str],
    output: Path,
    reference: RunId,
    nt0: int,
    t0: float,
    dt: float,
    time_start: float,
    time_end: float,
    workers: int = 1,
) -> list[dict[str, float | int | str]]:
    """Compares slow-light errors in control variable scans and outputs frame-by-frame errors and summary CSV."""
    if reference not in runs:
        raise KeyError(f"Reference run {reference} is not in runs.")
    for name, mapping in (("alignment", alignments), ("label", labels), ("scan value", values)):
        missing = sorted(run for run in runs if run not in mapping)
        if missing:
            raise KeyError(f"Missing {name} for: {', '.join(missing)}")

    output.mkdir(parents=True, exist_ok=True)
    alignment_rows = load_alignments(alignments)
    tasks = build_tasks(
        runs=runs,
        alignments=alignment_rows,
        labels=labels,
        values=values,
        reference=reference,
        nt0=nt0,
        t0=t0,
        dt=dt,
        time_start=time_start,
        time_end=time_end,
    )
    rows = [
        row
        for frame_rows in process_tasks(compare_slow_frame_set, tasks, workers)
        for row in frame_rows
    ]
    if not rows:
        raise ValueError("No comparable aligned Stokes frames were found.")

    summary = summarize_errors(rows)
    write_rows(output / "errors_t.csv", rows)
    write_rows(output / "errors.csv", summary)

    print(f"Wrote {output / 'errors_t.csv'}")
    print(f"Wrote {output / 'errors.csv'}")
    return summary


def plot_slow_errors(
    *,
    output: Path,
    xlabel: str,
    formats: tuple[str, ...] = ("png",),
) -> list[Path]:
    """Plot a slow-light error scan with time standard deviation from an existing `errors.csv`."""
    summary = read_rows(output / "errors.csv")
    paths = plot_error_scan(output, summary, xlabel=xlabel, formats=formats)
    for path in paths:
        print(f"Wrote {path}")
    return paths
