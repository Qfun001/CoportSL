"""Read BHAC frames directly and generate GRMHD diagnostic plots."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import numpy as np

if __package__:
    from .bhac.plot import plot_plane, plot_two_planes
    from .bhac.profiles import (
        plot_profile,
        radial_profile,
        smooth_profile,
        theta_profile,
        write_profile,
    )
    from .bhac.quantities import (
        ModelParameters,
        load_fluid_frame,
        path_for_frame,
        prepare_run,
    )
    from .bhac.timeseries import make_timeseries
    from .lib.cancel import throw_if_cancelled
    from .lib.media import make_video
else:
    from bhac.plot import plot_plane, plot_two_planes
    from bhac.profiles import (
        plot_profile,
        radial_profile,
        smooth_profile,
        theta_profile,
        write_profile,
    )
    from bhac.quantities import (
        ModelParameters,
        load_fluid_frame,
        path_for_frame,
        prepare_run,
    )
    from bhac.timeseries import make_timeseries
    from lib.cancel import throw_if_cancelled
    from lib.media import make_video


def configure_parameters() -> dict[str, object]:
    """Centrally set BHAC input, physics model, and plot parameters."""
    root = Path(r"D:/CoportSL-data")
    return {
        "input": root / "output",  # Absolute directory containing dataNNNN.dat.
        "grid": root / "grid_mks.in",  # BHAC static mesh file.
        "output": root / "result" / "GRMHDplot",
        "frames": (1000,),
        "quantities": ("rho",),
        # Independent selection of XZ, XY and XZ+XY bi-plane puzzles.
        "plot_types": ("xz", "xy", "xz_xy"),
        "limit": 50.0,  # Image plane half-width, unit rg.
        "slice_width": 0.1,  # The angular half-thickness of a plane slice, in rad.
        "draw_magnetic_field": False,
        "draw_jet_boundary": True,
        "sigma_level": 20.0,
        "be_level": 1.02,
        "formats": ("png",),
        "profile_quantity": "rho",
        "profile_types": ("radial", "theta"),
        "profile_r": (1.5, 50.0),
        "profile_shell": (1.5, 10.0),
        "profile_bins": 100,
        "profile_smooth": 5,
        "profile_log": True,
        "timeseries_radius": 2.5,  # The center radius of the thin shell, unit rg.
        "timeseries_half_width": 0.25,  # Half width of thin shell, unit rg.
        "model": ModelParameters(
            mbh=6.5e9,
            mdot=2.46e-4,
            mdot_sim=50.0,
            r_low=10.0,
            r_high=100.0,
            beta0=1.0,
            p_min=2.001,
            p_max=10.0,
            gamma_ratio=1.0e5,
        ),
    }


def selected_plot_types(parameters: dict[str, object]) -> tuple[str, ...]:
    """Reads explicit plot types and is compatible with legacy `planes/two_planes` parameters."""
    if "plot_types" in parameters:
        values = tuple(str(value) for value in parameters["plot_types"])
    elif bool(parameters.get("two_planes", False)):
        values = ("xz_xy",)
    else:
        values = tuple(str(value) for value in parameters.get(
            "planes", ("xz",)))
    values = tuple(dict.fromkeys(values))
    invalid = [value for value in values if value not in {"xz", "xy", "xz_xy"}]
    if invalid:
        raise ValueError(f"Unknown BHAC plot type: {invalid[0]}")
    if not values:
        raise ValueError("At least one BHAC plot type is required.")
    return values


def field_output_dir(
    output: Path | str,
    *fields: str,
) -> Path:
    """Build non-overlapping GRMHD product directories by figure type and physical quantity."""
    values = [str(value).strip() for value in fields]
    if not values or any(
            not value or not value.replace("_", "").isalnum()
            for value in values):
        raise ValueError("GRMHD output fields must be alphanumeric names.")
    return Path(output).joinpath(*values)


def plot_frames(parameters: dict[str, object]) -> list[Path]:
    """Read the data frame by frame and generate all selected floor plans."""
    run = prepare_run(Path(parameters["input"]), Path(parameters["grid"]))
    output = Path(parameters["output"])
    model = parameters["model"]
    if not isinstance(model, ModelParameters):
        raise TypeError("model must be ModelParameters")
    quantities = tuple(str(value) for value in parameters["quantities"])
    plot_types = selected_plot_types(parameters)
    targets = {
        (plot_type, quantity): field_output_dir(
            output, plot_type, quantity)
        for quantity in quantities
        for plot_type in plot_types
    }
    for (plot_type, quantity), target in targets.items():
        write_config(
            parameters,
            output=target,
            task="distribution",
            quantity=quantity,
            plot_type=plot_type,
        )
    paths = []
    for nt in tuple(parameters["frames"]):
        throw_if_cancelled(parameters.get("cancel_file"))
        frame = load_fluid_frame(run, path_for_frame(run, int(nt)), model)
        throw_if_cancelled(parameters.get("cancel_file"))
        print_frame_diagnostics(frame, quantities)
        for quantity in quantities:
            for plot_type in plot_types:
                throw_if_cancelled(parameters.get("cancel_file"))
                options = {
                    "limit": float(parameters["limit"]),
                    "formats": tuple(parameters["formats"]),
                    "draw_magnetic_field": bool(
                        parameters["draw_magnetic_field"]),
                    "draw_jet_boundary": bool(
                        parameters.get("draw_jet_boundary", True)),
                    "slice_width": float(parameters["slice_width"]),
                    "sigma_level": float(parameters["sigma_level"]),
                    "be_level": float(parameters["be_level"]),
                    "target_dir": targets[(plot_type, quantity)],
                }
                if plot_type == "xz_xy":
                    paths.extend(plot_two_planes(
                        frame, output, quantity, **options))
                else:
                    paths.extend(plot_plane(
                        frame, output, quantity, plot_type, **options))
    for path in paths:
        print(f"plot:   {path}")
    return paths


def plot_profiles(parameters: dict[str, object]) -> list[Path]:
    """Generates user-selected volume-weighted radial or polar statistics for selected frames."""
    run = prepare_run(Path(parameters["input"]), Path(parameters["grid"]))
    output = Path(parameters["output"])
    model = parameters["model"]
    if not isinstance(model, ModelParameters):
        raise TypeError("model must be ModelParameters")
    quantity = str(parameters["profile_quantity"])
    profile_types = tuple(str(value) for value in parameters.get(
        "profile_types", ("radial", "theta")))
    invalid = [
        value for value in profile_types
        if value not in {"radial", "theta"}
    ]
    if invalid or not profile_types:
        raise ValueError("profile_types must select radial and/or theta.")
    targets = {
        profile_type: field_output_dir(
            output, "profile", profile_type, quantity)
        for profile_type in profile_types
    }
    for profile_type, target in targets.items():
        write_config(
            parameters,
            output=target,
            task="profile",
            quantity=quantity,
            plot_type=profile_type,
        )
    paths = []
    for nt in tuple(parameters["frames"]):
        throw_if_cancelled(parameters.get("cancel_file"))
        frame = load_fluid_frame(run, path_for_frame(run, int(nt)), model)
        throw_if_cancelled(parameters.get("cancel_file"))
        window = int(parameters["profile_smooth"])
        if "radial" in profile_types:
            r0, r1 = tuple(parameters["profile_r"])
            radial = radial_profile(
                frame, quantity, r_min=float(r0), r_max=float(r1),
                bins=int(parameters["profile_bins"]))
            if window > 1:
                radial = smooth_profile(radial, window)
            radial_base = targets["radial"] / f"{quantity}_{frame.nt:04d}"
            paths.append(write_profile(
                radial, radial_base.with_suffix(".csv")))
            paths.extend(plot_profile(
                frame, radial, radial_base,
                formats=tuple(parameters["formats"]),
                logarithmic=bool(parameters["profile_log"])))
        if "theta" in profile_types:
            throw_if_cancelled(parameters.get("cancel_file"))
            s0, s1 = tuple(parameters["profile_shell"])
            theta = theta_profile(
                frame, quantity, r_min=float(s0), r_max=float(s1),
                bins=int(parameters["profile_bins"]))
            if window > 1:
                theta = smooth_profile(theta, window)
            theta_base = targets["theta"] / f"{quantity}_{frame.nt:04d}"
            paths.append(write_profile(
                theta, theta_base.with_suffix(".csv")))
            paths.extend(plot_profile(
                frame, theta, theta_base,
                formats=tuple(parameters["formats"]),
                logarithmic=bool(parameters["profile_log"])))
    for path in paths:
        print(f"profile: {path}")
    return paths


def make_quantity_movie(parameters: dict[str, object], quantity: str, plane: str = "xz") -> Path:
    """Encode an existing plane diagram of a certain physical quantity into MP4."""
    output = Path(parameters["output"])
    source = field_output_dir(output, plane, quantity)
    target = field_output_dir(output, "movie", plane, quantity)
    images = sorted(source.glob(f"{quantity}_*.png"))
    if not images:
        # The old version mixed all physical quantities in a flat directory, and still allowed videos to be made accordingly.
        images = sorted((output / plane).glob(f"{quantity}_*.png"))
    write_config(
        parameters,
        output=target,
        task="video",
        quantity=quantity,
        plot_type=plane,
    )
    path = make_video(
        images=images,
        output=target / f"{quantity}_{plane}.mp4",
        fps=10.0,
        max_size=(1920, 1080),
        cancel_file=parameters.get("cancel_file"),
    )
    print(f"movie: {path}")
    return path


def print_frame_diagnostics(frame, quantities: tuple[str, ...]) -> None:
    """Outputs the frame time, cell number, and limited value range of the plotted physical quantity."""
    print(f"frame:  {frame.path}  t={frame.time:g} rg/c  cells={frame.volume.size}")
    for quantity in quantities:
        values = frame.get(str(quantity))
        finite = values[np.isfinite(values)]
        if finite.size:
            print(f"  {quantity}: [{finite.min():.6e}, {finite.max():.6e}]")
        else:
            print(f"  {quantity}: no finite values")


def write_config(
    parameters: dict[str, object],
    *,
    output: Path | None = None,
    task: str = "distribution",
    quantity: str | None = None,
    plot_type: str | None = None,
) -> Path:
    """Record the main input parameters that affect the physical quantity or plot."""
    output = Path(parameters["output"]) if output is None else Path(output)
    if not output.is_absolute():
        raise ValueError("BHAC output path must be absolute.")
    output.mkdir(parents=True, exist_ok=True)
    model = parameters["model"]
    if not isinstance(model, ModelParameters):
        raise TypeError("model must be ModelParameters")
    path = output / "config.txt"
    lines = [
        f"task={task}",
        f"input={Path(parameters['input']).as_posix()}",
        f"grid={Path(parameters['grid']).as_posix()}",
        f"frames={','.join(str(value) for value in tuple(parameters['frames']))}",
        f"quantity={quantity or ''}",
        f"plot_type={plot_type or ''}",
        f"formats={','.join(str(value) for value in tuple(parameters['formats']))}",
        f"mbh={model.mbh:.17g}",
        f"mdot={model.mdot:.17g}",
        f"mdot_sim={model.mdot_sim:.17g}",
        f"r_low={model.r_low:.17g}",
        f"r_high={model.r_high:.17g}",
        f"beta0={model.beta0:.17g}",
        f"p_min={model.p_min:.17g}",
        f"p_max={model.p_max:.17g}",
        f"gamma_ratio={model.gamma_ratio:.17g}",
    ]
    if task == "distribution":
        lines.extend([
            f"limit={float(parameters['limit']):.17g}",
            f"slice_width={float(parameters['slice_width']):.17g}",
            "draw_jet_boundary="
            f"{str(bool(parameters.get('draw_jet_boundary', True))).lower()}",
            "draw_magnetic_field="
            f"{str(bool(parameters['draw_magnetic_field'])).lower()}",
            f"sigma_level={float(parameters['sigma_level']):.17g}",
            f"be_level={float(parameters['be_level']):.17g}",
        ])
    elif task == "profile":
        lines.extend([
            "profile_r=" + ",".join(
                f"{float(value):.17g}"
                for value in tuple(parameters["profile_r"])),
            "profile_shell=" + ",".join(
                f"{float(value):.17g}"
                for value in tuple(parameters["profile_shell"])),
            f"profile_bins={int(parameters['profile_bins'])}",
            f"profile_smooth={int(parameters['profile_smooth'])}",
            f"profile_log={str(bool(parameters['profile_log'])).lower()}",
        ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def print_paths(parameters: dict[str, object]) -> None:
    """By default only absolute input and output are printed to avoid accidentally performing expensive tasks."""
    print("BHAC GRMHD plots")
    print(f"  input:  {Path(parameters['input'])}")
    print(f"  grid:   {Path(parameters['grid'])}")
    print(f"  output: {Path(parameters['output'])}")


def main() -> None:
    parameters = configure_parameters()
    print_paths(parameters)

    # plot_frames(parameters)
    # plot_profiles(parameters)
    # make_timeseries(parameters)
    # make_quantity_movie(parameters, "rho", "xz")


if __name__ == "__main__":
    main()
