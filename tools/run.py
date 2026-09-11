"""Set post-processing parameters centrally and call the required functions directly in `main()`."""

from __future__ import annotations

from pathlib import Path

if __package__:
    from .lib.paths import Case, ProjectPaths, case_name
    from .lib.region_contrib import plot_region_contribution
    from .lib.workflow import (
        align_cases,
        case_tuple,
        calc_case_errors,
        calc_cases,
        make_evpa_videos,
        plot_cases_beta2,
        plot_cases_flux,
        plot_cases_lp,
        plot_evpa_cases,
        plot_pair_beta2,
        plot_pair_evpa,
        plot_pair_flux,
        plot_pair_lp,
        plot_case_errors,
    )
else:
    from lib.paths import Case, ProjectPaths, case_name
    from lib.region_contrib import plot_region_contribution
    from lib.workflow import (
        align_cases,
        case_tuple,
        calc_case_errors,
        calc_cases,
        make_evpa_videos,
        plot_cases_beta2,
        plot_cases_flux,
        plot_cases_lp,
        plot_evpa_cases,
        plot_pair_beta2,
        plot_pair_evpa,
        plot_pair_flux,
        plot_pair_lp,
        plot_case_errors,
    )


# Path configuration. Modify the fields below to switch common input and output directories.
#
# Final input path:
#   Fast light: <root>/result/fast/<run>/
#   Slow light: <root>/result/slow/<run>/
#   Pre-analysis: <root>/result/analysis/<run>/
#
# The final post-processing paths are located in the plot/ subdirectory of the corresponding result directory.
# Comparison results across multiple batches are written to <root>/result/comparison/<name>/.
root = Path(r"D:/CoportSL-data")
paths = ProjectPaths(root=root)


cases = (
    # After running, it is updated according to the actual number of each directory; the number is incremented independently under fast and slow.
    Case("fast", "output0003", "Power-law fast"),
    Case("slow", "output0010", "Power-law slow r50 p99"),
)

thermal: tuple[Case, ...] = ()
powerlaw = cases[1:2]
groups = {
    "powerlaw": powerlaw,
}

# Common parameters.
formats = ("png", "pdf")  # Image format to save; to composite EVPA video, png must be included.
workers = 16  # Number of parallel processes; set to 1 for serial execution
fig_opts = dict(formats=formats)

# Time alignment parameters.
align_opts = dict(
    max_lag=300.0,  # Maximum search offset, unit rg/c
    min_overlap_fraction=0.75,
)

# EVPA parameters.
evpa_times = (10800.0, 11210.0, 11330.0, 11460.0)  # EVPA comparison moment
evpa_opts = dict(
    intensity_vmin=0.0,  # The lower limit of background light intensity color; must be greater than 0 when using logarithmic color scale.
    intensity_vmax=1.0e-3,
    intensity_log=False,
    stride=32,  # EVPA short line sampling interval, unit pixel
    line_length=12.0,  # EVPA short line length, unit pixel
    min_i_fraction=0.02,
    flip_u=True,
    scale_bar_uas=20.0,  # Angular scale ruler in uas; not drawn when set to None
)
evpa_frame_opts = dict(
    **evpa_opts,
    step=1,  # Frame sampling interval
    formats=formats,
    reuse=False,  # Set to False when adjusting color scale parameters to avoid reusing existing images.
    workers=workers,
)

# beta2 parameters. None represents the entire image, and the remaining values ​​represent the ring radius in uas.
obs_opts = dict(radii_muas=(None, 20.0), workers=workers)
beta2_opts = dict(radii_muas=(None, 20.0), **fig_opts)

# Slow light error scan parameters. Each case needs to generate its own time_alignment.csv first.
err_opts = dict(
    time_start=10800.0,
    time_end=11600.0,
    workers=workers,
)
err_fig_opts = dict(formats=formats)


def target_name(target: Case | tuple[Case, ...]) -> str:
    """Generates the display name of the currently executed object."""
    if isinstance(target, Case):
        return case_name(target)
    for name, group in groups.items():
        if target == group:
            return name
    return "custom"


def case_ref(item: Case) -> str:
    """Generate case short labels with serial numbers."""
    return f"[{cases.index(item)}] {case_name(item)}"


def group_refs(items: tuple[Case, ...]) -> str:
    """Generate compact display text for case groups."""
    if len(items) == 1:
        return case_ref(items[0])
    return ", ".join(case_ref(item) for item in items)


def print_paths(
    *,
    fast: Case,
    target: Case | tuple[Case, ...],
    items: tuple[Case, ...],
    analysis: str,
) -> None:
    """Prints the main input and output paths actually directed by the current configuration."""
    print("Available")
    for item in cases:
        print(f"  {case_ref(item)}")

    print("Selected")
    print(f"  fast:     {case_ref(fast)}")
    print(f"  analysis: {analysis}")
    print(f"  target: {target_name(target)}")
    print(f"  cases:    {group_refs(items)}")

    print("Paths")
    print(f"  analysis input:  {paths.analysis_input_path(analysis)}")
    print(f"  analysis output: {paths.analysis_output_path(analysis)}")
    print(f"  fast input:      {paths.fast_result_path(fast)}")
    print(f"  fast output:     {paths.fast_plot_path(fast)}")
    if all(item.light == "slow" for item in items):
        for item in items:
            print(f"  slow input:      {paths.slow_result_path(item)}")
            print(f"  slow output:     {paths.slow_plot_path(item)}")


def main() -> None:
    # Each function only performs the function described by its name. Uncomment in the corresponding group according to the current task.
    # Fast light analysis is run by explicitly specifying the fast reference.
    fast = cases[0]

    # Slow-light pre-analysis is run by analysis with an explicitly specified number.
    analysis = "output0002"

    # The target of slow light related functions is determined by target.
    target = powerlaw
    items = case_tuple(target)

    print_paths(fast=fast, target=target, items=items, analysis=analysis)

    # # Read I/Q/U once per frame and generate flux.csv, lp.csv, and beta2.csv.
    # calc_cases(items=fast, paths=paths, **obs_opts)

    # # Plot flux over time from an existing CSV.
    # plot_cases_flux(items=fast, paths=paths, **fig_opts)

    # # Plot linear polarization over time from an existing CSV.
    # plot_cases_lp(items=fast, paths=paths, **fig_opts)

    # # Plot beta2 amplitude and phase from existing CSV.
    # plot_cases_beta2(items=fast, paths=paths, **beta2_opts)

    # # Draw EVPA graph frame by frame.
    plot_evpa_cases(items=fast, paths=paths, **evpa_frame_opts)

    # # Synthesize existing EVPA image sequences into MP4 videos.
    # make_evpa_videos(items=fast, paths=paths)

    '''2. Slow-light pre-analysis
    Inspect regions and time windows produced by automatic GRRT pre-analysis.'''

    # # Draw a single 6 x N discrete heat map from the reduced area contribution file.
    # plot_region_contribution(
    #     input=paths.analysis_input_path(analysis),
    #     output=paths.analysis_output_path(analysis),
    #     **fig_opts)

    '''3. Production slow-light result analysis
    When the target is a single slow-light Case, a single group is processed, and when it is thermal/powerlaw, the entire group is processed in a loop.'''

    # # Calculate the three types of observations for all slow light cases in the target, and then estimate the time translation based on the fast and slow light fluxes.
    # calc_cases(items=target, paths=paths, **obs_opts)
    # align_cases(items=target, reference=fast, paths=paths, **align_opts)

    # # Compare the changes in fast and slow light flux over time.
    # plot_pair_flux(items=target, reference=fast, paths=paths, **fig_opts)

    # # Compare the polarization of fast light and slow light.
    # plot_pair_lp(items=target, reference=fast, paths=paths, **fig_opts)

    # # Compare fast light and slow light beta2 amplitude and phase.
    # plot_pair_beta2(items=target, reference=fast, paths=paths, **beta2_opts)

    # # Compare fast light and slow light EVPA plots side by side at a specified physical moment.
    # plot_pair_evpa(items=target, reference=fast, paths=paths, times=evpa_times, **evpa_opts)

    '''4. Slow-light error scan validation
    Compare production slow-light results and reference cases across a control variable.'''

    # # The key of values is the slow light run number, and the value is the control variable that needs to be plotted on the horizontal axis.
    # values = {item.run: value for item, value in zip(items, (20.0, 30.0, 50.0, 80.0))}
    # error_output = paths.comparison_path("radius_scan")
    # calc_case_errors(
    #     items=target, reference=items[-1], fast=fast, values=values,
    #     paths=paths, output=error_output, **err_opts)
    # plot_case_errors(
    #     output=error_output,
    #     xlabel=r"$r_{\mathrm{slow}}\ [r_{\mathrm{g}}]$",
    #     **err_fig_opts)

    pass


if __name__ == "__main__":
    main()
