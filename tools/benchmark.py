"""Plot speed and memory summary graphs of C++ Benchmark output."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

if __package__:
    from .lib.data import read_key_values, read_rows, read_status_paths
    from .lib.save_fig import save_figure
else:
    from lib.data import read_key_values, read_rows, read_status_paths
    from lib.save_fig import save_figure


SUMMARY_NAME = "summary.csv"
CONFIG_NAME = "config.txt"

WINDOWS = ("p90", "p99", "p99.9")
MEMORY_TICK_SIZE = 16
MEMORY_LABEL_SIZE = 18
MEMORY_LEGEND_SIZE = 16


def configure_parameters() -> dict[str, object]:
    """Centrally set Benchmark input and plot output parameters."""
    root = Path(r"D:/CoportSL-data")
    output = root / "result" / "benchmark" / "output0001"
    return {
        "inp": output,  # Directory containing config.txt and summary.csv.
        "plot": output / "plot",  # Figures are written to the current Benchmark batch.
        "modes": ("performance_cores",),  # The core group to display; None means all.
        "fmt": ("png", "pdf"),  # Image output format.
        "time_log": False,  # Whether to use logarithmic coordinates on the vertical axis of the time graph.
        "rate_log": True,  # Whether the vertical axis of the throughput graph uses logarithmic coordinates.
        "mem_unit": "GiB",  # Memory unit, can be MiB or GiB.
    }


def as_float(row: dict[str, str], field: str) -> float:
    """Read floating point fields in CSV."""
    try:
        return float(row[field])
    except KeyError as exc:
        raise KeyError(f"Missing column {field} in benchmark summary.") from exc


def as_int(row: dict[str, str], field: str) -> int:
    """Read integer fields from CSV."""
    return int(round(as_float(row, field)))


def read_benchmark(input_dir: Path) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Read Benchmark configuration and summary tables."""
    config_path = input_dir / CONFIG_NAME
    summary_path = input_dir / SUMMARY_NAME
    if not config_path.is_file():
        raise FileNotFoundError(f"Missing benchmark config: {config_path}")
    if not summary_path.is_file():
        raise FileNotFoundError(f"Missing benchmark summary: {summary_path}")

    rows = read_rows(summary_path)
    if not rows:
        raise ValueError(f"No benchmark rows found in {summary_path}")
    return read_key_values(config_path), rows


def sorted_values(rows: list[dict[str, str]], field: str) -> list[int]:
    """Read all values of an integer field and sort them."""
    return sorted({as_int(row, field) for row in rows})


def parse_int_list(value: str | None) -> list[int]:
    """Read a comma-separated list of integers from config.txt."""
    if value is None or not value.strip():
        return []
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def lights(rows: list[dict[str, str]]) -> list[str]:
    """Return available propagation models in fast-light, slow-light order."""
    present = {row["light"] for row in rows}
    ordered = [light for light in ("fast", "slow") if light in present]
    ordered.extend(sorted(present - set(ordered)))
    return ordered


def rows_for(
    rows: list[dict[str, str]],
    *,
    light: str,
    npix: int,
) -> list[dict[str, str]]:
    """Get the physical core number scan results under the same propagation model and resolution."""
    selected = [
        row for row in rows
        if (
            row["light"] == light and
            as_int(row, "npix") == npix
        )
    ]
    return sorted(selected, key=lambda row: as_int(row, "cores"))


def light_label(light: str) -> str:
    """Generate propagation model labels in the legend."""
    labels = {
        "fast": "fast",
        "slow": "slow",
    }
    return labels.get(light, light)


def bytes_scale(unit: str) -> tuple[float, str]:
    """Returns the memory unit scaling factor and Matplotlib labels."""
    if unit == "MiB":
        return 1024.0**2, "MiB"
    if unit == "GiB":
        return 1024.0**3, "GiB"
    raise ValueError(f"Unsupported memory unit: {unit}")


def validate_mode(config: dict[str, str], modes: tuple[str, ...] | None) -> str:
    """Check run-level core types; summary.csv does not repeat this field line by line."""
    mode = config.get("BenchmarkConfig::CORE_MODE")
    if not mode:
        raise KeyError("Missing BenchmarkConfig::CORE_MODE in benchmark config.txt.")
    if modes is not None and mode not in modes:
        raise ValueError(
            f"Benchmark core mode {mode!r} is not among requested modes={modes!r}.")
    return mode


def print_summary(
    config: dict[str, str],
    rows: list[dict[str, str]],
    modes: tuple[str, ...] | None,
) -> None:
    """Print minimal diagnostic information to facilitate confirmation of which set of benchmarks was read."""
    npix_values = sorted_values(rows, "npix")
    core_values = sorted_values(rows, "cores")
    print(f"Benchmark rows: {len(rows)}")
    print(f"electron={config.get('Config::ELECTRON', 'unknown')}")
    print(f"frequency_hz={config.get('Config::NU', 'unknown')}")
    print(
        "slow="
        f"{config.get('SlowLight::REGION_KEYS', '?')} "
        f"[{config.get('SlowLight::LEFT', '?')}, {config.get('SlowLight::RIGHT', '?')}]"
    )
    mode = validate_mode(config, modes)
    print(f"core_mode={mode}")
    print(f"npix={npix_values}")
    print(f"cores={core_values}")

    configured_npix = parse_int_list(config.get("BenchmarkConfig::NPIX_LIST"))
    configured_cores = parse_int_list(config.get("BenchmarkConfig::CORE_COUNTS"))
    if configured_npix and configured_npix != npix_values:
        missing = sorted(set(configured_npix) - set(npix_values))
        if missing:
            print(f"Warning: summary.csv is missing npix values from config.txt: {missing}")
    if configured_cores and configured_cores != core_values:
        missing = sorted(set(configured_cores) - set(core_values))
        if missing:
            print(f"Warning: summary.csv is missing core counts from config.txt: {missing}")


def plot_time(
    *,
    rows: list[dict[str, str]],
    output_dir: Path,
    formats: tuple[str, ...],
    log_y: bool,
) -> list[Path]:
    """Plot fast- and slow-light imaging time against physical core count."""
    figure, axes = plt.subplots(1, 2, figsize=(9.2, 4.0), sharey=True, constrained_layout=True)
    npix_values = sorted_values(rows, "npix")
    markers = ("o", "s", "^", "D", "P", "X")
    colors = plt.get_cmap("tab10")(np.linspace(0.0, 1.0, max(1, len(npix_values))))

    for axis, light in zip(axes, ("fast", "slow")):
        for i, npix in enumerate(npix_values):
            selected = rows_for(rows, light=light, npix=npix)
            if not selected:
                continue
            cores = [as_int(row, "cores") for row in selected]
            values = [as_float(row, "transfer_mean_s") for row in selected]
            axis.plot(
                cores,
                values,
                marker=markers[i % len(markers)],
                color=colors[i],
                label=f"{npix}$^2$",
            )
        axis.set_title(light_label(light))
        axis.set_xlabel("physical cores")
        axis.set_xticks(sorted_values(rows, "cores"))
        if log_y:
            axis.set_yscale("log")
        axis.grid(alpha=0.25)
    axes[0].set_ylabel(r"$t\ [\mathrm{s}]$")
    axes[1].tick_params(labelleft=False)
    axes[0].legend(fontsize=8, ncols=2, title=r"$N_{\rm pix}$", title_fontsize=8)

    paths = save_figure(figure, output_dir / "time", formats, dpi=220)
    plt.close(figure)
    return paths


def plot_rate(
    *,
    rows: list[dict[str, str]],
    output_dir: Path,
    formats: tuple[str, ...],
    log_y: bool,
) -> list[Path]:
    """Plot fast- and slow-light ray throughput against physical core count."""
    figure, axes = plt.subplots(1, 2, figsize=(9.2, 4.0), sharey=True, constrained_layout=True)
    npix_values = sorted_values(rows, "npix")
    markers = ("o", "s", "^", "D", "P", "X")
    colors = plt.get_cmap("tab10")(np.linspace(0.0, 1.0, max(1, len(npix_values))))

    for axis, light in zip(axes, ("fast", "slow")):
        for i, npix in enumerate(npix_values):
            selected = rows_for(rows, light=light, npix=npix)
            if not selected:
                continue
            cores = [as_int(row, "cores") for row in selected]
            values = [rays_per_second(row) for row in selected]
            axis.plot(
                cores,
                values,
                marker=markers[i % len(markers)],
                color=colors[i],
                label=f"{npix}$^2$",
            )
        axis.set_title(light_label(light))
        axis.set_xlabel("physical cores")
        axis.set_xticks(sorted_values(rows, "cores"))
        if log_y:
            axis.set_yscale("log")
        axis.grid(alpha=0.25)
    axes[0].set_ylabel(r"$N_{\rm ray}/s$")
    axes[1].tick_params(labelleft=False)
    axes[0].legend(fontsize=8, ncols=2, title=r"$N_{\rm pix}$", title_fontsize=8)

    paths = save_figure(figure, output_dir / "rate", formats, dpi=220)
    plt.close(figure)
    return paths


def memory_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Press light and npix to deduplicate and keep the memory record of the minimum number of cores."""
    selected = {}
    for row in sorted(
        rows,
        key=lambda item: (
            item["light"],
            as_int(item, "npix"),
            as_int(item, "cores"),
        ),
    ):
        key = row["light"], as_int(row, "npix")
        selected.setdefault(key, row)
    return list(selected.values())


def bytes_per_frame(rows: list[dict[str, str]]) -> float:
    """Reads a single GRMHD frame memory measured directly by the backend."""
    values = [
        as_float(row, "frame_bytes")
        for row in rows
        if row["light"] == "slow" and as_float(row, "frame_bytes") > 0.0
    ]
    if not values:
        raise ValueError("Cannot estimate bytes per slow-light frame from summary.csv.")
    return float(np.median(values))


def rays_per_second(row: dict[str, str]) -> float:
    """Ray throughput is derived from image edge length and radiation transfer time."""
    npix = as_int(row, "npix")
    duration = as_float(row, "transfer_mean_s")
    if duration <= 0.0:
        raise ValueError("Benchmark transfer_mean_s must be positive.")
    return float(npix * npix) / duration


def plot_memory(
    *,
    rows: list[dict[str, str]],
    output_dir: Path,
    formats: tuple[str, ...],
    unit: str,
) -> list[Path]:
    """Plot structured memory use for the active grid and one GRMHD frame."""
    scale, label = bytes_scale(unit)
    selected = memory_rows(rows)
    npix_values = sorted_values(selected, "npix")
    x = np.arange(len(npix_values), dtype=float)
    width = 0.24
    by_key = {
        (row["light"], as_int(row, "npix")): row
        for row in selected
    }
    grid = np.array([
        as_float(by_key[("fast", npix)], "grid_bytes") / scale
        for npix in npix_values
    ])
    frame = np.array([
        as_float(by_key[("slow", npix)], "frame_bytes") / scale
        for npix in npix_values
    ])

    figure, axis = plt.subplots(figsize=(7.0, 4.2), constrained_layout=True)
    axis.bar(x - width / 2, grid, width=width, label="active grid", color="tab:blue")
    axis.bar(x + width / 2, frame, width=width, label="one GRMHD frame", color="tab:green")
    axis.set_xticks(x)
    axis.set_xticklabels([f"{npix}$^2$" for npix in npix_values])
    axis.set_xlabel(r"$N_{\rm pix}$", fontsize=MEMORY_LABEL_SIZE)
    axis.set_ylabel(rf"memory [{label}]", fontsize=MEMORY_LABEL_SIZE)
    axis.tick_params(axis="both", which="major", labelsize=MEMORY_TICK_SIZE)
    axis.grid(alpha=0.25, axis="y")
    axis.legend(fontsize=MEMORY_LEGEND_SIZE)

    paths = save_figure(figure, output_dir / "grmhd_memory", formats, dpi=220)
    plt.close(figure)
    return paths


def shortest_coverage_window(
    offsets: np.ndarray,
    probability: float,
) -> tuple[float, float]:
    """Find the shortest continuous interval covering ceil(qN) equally weighted samples on the sorted offset."""
    if offsets.ndim != 1 or offsets.size == 0:
        raise ValueError("Coverage window requires a one-dimensional offset array.")
    if not 0.0 < probability <= 1.0:
        raise ValueError("Coverage probability must satisfy 0 < probability <= 1.")
    if not np.all(np.isfinite(offsets)):
        raise ValueError("Coverage offsets must be finite.")
    x = np.sort(offsets)
    count = int(np.ceil(probability * x.size))
    best: tuple[float, float] | None = None
    for begin in range(0, x.size - count + 1):
        candidate = (float(x[begin]), float(x[begin + count - 1]))
        if best is None or (
            candidate[1] - candidate[0],
            candidate[0],
        ) < (
            best[1] - best[0],
            best[0],
        ):
            best = candidate
    if best is None:
        raise RuntimeError("No coverage window reaches the requested count.")
    return best


def estimated_frame_count(left: float, right: float, dt: float) -> float:
    """Estimates the number of slow-light buffered frames on the uniform timeline containing the previous interpolated frame."""
    if not np.isfinite(left) or not np.isfinite(right) or left > right:
        raise ValueError("Slow-light window endpoints must be finite and ordered.")
    if not np.isfinite(dt) or dt <= 0.0:
        raise ValueError("Input::DT must be finite and positive.")
    return float(max(1, int(np.ceil(right / dt) - np.ceil(left / dt) + 2)))


def resolve_analysis(
    input_dir: Path,
    benchmark_config: dict[str, str],
) -> Path:
    """Pre-analysis of parsing and verifying actual reuse from Benchmark status."""
    value = read_status_paths(input_dir).get("analysis")
    if not value:
        raise KeyError("Missing analysis path in benchmark status.txt.")
    path = Path(value)
    analysis = (path if path.is_absolute() else input_dir / path).resolve()
    config_path = analysis / CONFIG_NAME
    if not config_path.is_file():
        raise FileNotFoundError(f"Missing benchmark analysis config: {config_path}")
    analysis_config = read_key_values(config_path)
    for field in ("model_signature", "analysis_signature"):
        expected = benchmark_config.get(field)
        actual = analysis_config.get(field)
        if not expected or actual != expected:
            raise ValueError(
                f"Benchmark {field} does not match analysis config: "
                f"benchmark={expected!r}, analysis={actual!r}")
    return analysis


def read_window_rows(analysis_dir: Path) -> list[dict[str, float | str]]:
    """Read the Suggest exact window and estimate the candidate window from the single-region histogram."""
    analysis_config = read_key_values(analysis_dir / CONFIG_NAME)
    try:
        dt = float(analysis_config["Input::DT"])
    except KeyError as exc:
        raise KeyError("Missing Input::DT in analysis config.txt.") from exc
    labels = {
        row["key"]: row["label"]
        for row in read_rows(analysis_dir / "regions" / "index.csv")
    }
    rows: list[dict[str, float | str]] = []
    probabilities = {"p90": 0.90, "p99": 0.99, "p99.9": 0.999}
    for key, label in labels.items():
        histogram = read_rows(
            analysis_dir / "regions" / key / "offset_histogram.csv")
        if not histogram:
            continue
        if "count" not in histogram[0]:
            raise ValueError(
                f"Offset histogram for {key} uses the obsolete 'weight' header; "
                "re-run the Analysis with the current implementation.")
        offsets = np.array(
            [int(row["frame_offset"]) for row in histogram],
            dtype=np.int64,
        )
        counts = np.array(
            [int(row["count"]) for row in histogram],
            dtype=np.int64,
        )
        samples = np.repeat(offsets, counts).astype(np.float64)
        centers = (samples + 0.5) * dt
        for name, probability in probabilities.items():
            left, right = shortest_coverage_window(centers, probability)
            rows.append({
                "region": key,
                "label": label,
                "window": name,
                "frame_count": estimated_frame_count(left, right, dt),
            })

    for row in read_rows(analysis_dir / "suggest" / "windows.csv"):
        name = row["window"]
        if name not in WINDOWS:
            continue
        left = float(row["left"])
        right = float(row["right"])
        rows.append({
            "region": "suggest",
            "label": "suggest",
            "window": name,
            "frame_count": estimated_frame_count(left, right, dt),
        })
    if not rows:
        raise FileNotFoundError(f"No region window data found in {analysis_dir}")
    return rows


def plot_frame_cache(
    *,
    rows: list[dict[str, str]],
    analysis_dir: Path,
    output_dir: Path,
    formats: tuple[str, ...],
    unit: str,
    show_ylabel: bool = True,
) -> list[Path]:
    """Estimating and plotting framebuffer memory for different slow-light regions and time windows."""
    scale, label = bytes_scale(unit)
    frame_bytes = bytes_per_frame(rows)
    win_rows = read_window_rows(analysis_dir)
    regions = list(dict.fromkeys(str(row["region"]) for row in win_rows))
    labels = {
        str(row["region"]): str(row["label"])
        for row in win_rows
    }
    by_key = {
        (str(row["region"]), str(row["window"])): float(row["frame_count"])
        for row in win_rows
    }

    x = np.arange(len(regions), dtype=float)
    width = 0.24
    offsets = np.linspace(-width, width, len(WINDOWS))
    colors = {
        "p90": "tab:blue",
        "p99": "tab:green",
        "p99.9": "tab:orange",
    }

    figure, axis = plt.subplots(figsize=(7.0, 4.2), constrained_layout=True)
    for offset, window in zip(offsets, WINDOWS):
        values = np.array([
            by_key[(region, window)] * frame_bytes / scale
            for region in regions
        ])
        axis.bar(x + offset, values, width=width, label=window, color=colors[window])

    axis.set_xticks(x)
    axis.set_xticklabels([labels[region] for region in regions], rotation=20, ha="right")
    axis.set_xlabel("slow-light region", fontsize=MEMORY_LABEL_SIZE)
    if show_ylabel:
        axis.set_ylabel(rf"estimated frame cache [{label}]", fontsize=MEMORY_LABEL_SIZE)
    axis.tick_params(axis="both", which="major", labelsize=MEMORY_TICK_SIZE)
    axis.grid(alpha=0.25, axis="y")
    axis.legend(fontsize=MEMORY_LEGEND_SIZE, title="window", title_fontsize=MEMORY_LEGEND_SIZE)

    paths = save_figure(figure, output_dir / "frame_cache", formats, dpi=220)
    plt.close(figure)
    return paths


def plot_benchmark(
    *,
    input_dir: Path,
    output_dir: Path,
    modes: tuple[str, ...] | None,
    formats: tuple[str, ...],
    time_log: bool,
    rate_log: bool,
    memory_unit: str,
) -> list[Path]:
    """Read Benchmark output and generate post-processing plots."""
    config, rows = read_benchmark(input_dir)
    analysis_dir = resolve_analysis(input_dir, config)
    validate_mode(config, modes)
    print_summary(config, rows, modes)
    paths = []
    paths.extend(plot_time(rows=rows, output_dir=output_dir, formats=formats, log_y=time_log))
    paths.extend(plot_rate(rows=rows, output_dir=output_dir, formats=formats, log_y=rate_log))
    paths.extend(plot_memory(rows=rows, output_dir=output_dir, formats=formats, unit=memory_unit))
    paths.extend(plot_frame_cache(
        rows=rows,
        analysis_dir=analysis_dir,
        output_dir=output_dir,
        formats=formats,
        unit=memory_unit,
        show_ylabel=False,
    ))
    for path in paths:
        print(f"Wrote {path}")
    return paths


def main() -> None:
    params = configure_parameters()
    input_dir = params["inp"]
    output_dir = params["plot"]
    if not all(isinstance(path, Path) for path in (input_dir, output_dir)):
        raise TypeError("inp and plot must be pathlib.Path values.")

    plot_benchmark(
        input_dir=input_dir,
        output_dir=output_dir,
        modes=params["modes"],
        formats=tuple(params["fmt"]),
        time_log=bool(params["time_log"]),
        rate_log=bool(params["rate_log"]),
        memory_unit=str(params["mem_unit"]),
    )


if __name__ == "__main__":
    main()
