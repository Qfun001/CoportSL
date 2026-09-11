# CoportSL: Polarized Slow-Light Radiative Transfer

English | [简体中文](README-zh.md)

CoportSL extends the original polarized GRRT code [CoportS](https://github.com/JieweiHuang/CoportS) with a slow-light imaging framework for computing polarized fast-light and hybrid slow-light images of black hole accretion flows.

## Download and run on Windows

Most Windows users do not need to build CoportSL. Open the [GitHub Releases page](https://github.com/Qfun001/CoportSL/releases), choose a release, download `CoportSL.exe` from **Assets**, and double-click it. The executable is a portable single-file application for 64-bit Windows 10/11 and does not require a separate Python or Visual Studio installation. GitHub's automatically generated source-code archives contain source files only; download the `.exe` asset to run the GUI.

See the [CoportSL Desktop User Guide](USER_GUIDE.md) for input preparation, first launch, language selection, the recommended workflow, result locations, and troubleshooting. The interface starts in English and can switch immediately to Simplified Chinese from **Settings > Language**.

The executable is currently unsigned, so Windows SmartScreen may identify it as coming from an unknown publisher. Continue only after downloading it from the official Releases page and verifying the SHA-256 checksum published with that release.

## Contents

- [Download and run on Windows](#download-and-run-on-windows)
- [Overview](#overview)
- [Input data](#input-data)
- [Requirements for source builds](#requirements-for-source-builds)
- [Building from source](#building-from-source)
- [Windows desktop source build](#windows-desktop-source-build)
- Workflow
  - [1. Calibrate the accretion rate with Flux](#1-calibrate-the-accretion-rate-with-flux)
  - [2. Fast-light imaging](#2-fast-light-imaging)
  - [3. Slow-light pre-analysis](#3-slow-light-pre-analysis)
  - [4. Slow-light imaging](#4-slow-light-imaging)
  - [5. Time alignment and plotting](#5-time-alignment-and-plotting)
  - [6. Benchmarking](#6-benchmarking)
- [Auxiliary analysis tools](#auxiliary-analysis-tools)
- [Result directory layout](#result-directory-layout)
- [Source layout](#source-layout)
- [Validation and limitations](#validation-and-limitations)
- [Citation, software, and data availability](#citation-software-and-data-availability)
- [License and provenance](#license-and-provenance)

## Overview

A typical end-to-end workflow is:

```text
Calibrate the accretion rate with Flux
  -> Fast-light imaging
  -> Slow-light pre-analysis to select the slow-light region and valid time window
  -> Slow-light imaging
  -> Fast-/slow-light time alignment
  -> Plotting and error analysis
  -> Benchmarking
```

`apps/`, `src/`, and `tools/` contain the application entry points, shared scientific implementation, and Python analysis tools, respectively. `desktop/` contains the Windows graphical interface and its packaging configuration.

The imaging code caches geodesics, spatial interpolation stencils, and parallel-transported polarization basis vectors, then reuses them across GRMHD frames and observing frequencies. Hybrid slow light performs temporal interpolation only inside data-driven selected regions; all other regions use the single GRMHD frame at the reference time.

Result identity is determined by input content, physical and numerical parameters, region definitions, and the time origin. It does not contain a manually assigned version number. An implementation optimization or accuracy improvement therefore does not invalidate existing results solely because the software version changed; reruns should be based on the actual parameter differences and error evidence.

## Requirements for source builds

Build environments:

- Windows 10/11: Visual Studio 2022 with the **Desktop development with C++** workload, MSVC `v143`, C++20, and OpenMP.
- Linux / WSL2: CMake 3.22 or later, a C++20 compiler with OpenMP support (GCC or Clang), and Ninja or Make.
- Python: version 3.10 or later for the command-line scientific tools and Windows desktop application.

Install the loosely pinned command-line plotting and post-processing dependencies:

```powershell
python -m pip install -r requirements.txt
```

Using or packaging the Windows desktop application also requires:

```powershell
python -m pip install -r requirements-desktop.txt
```

## Input data

GRMHD data are not included. Before running CoportSL, prepare:

1. A BHAC data directory containing files named `dataNNNN.dat`, such as `data1200.dat` and `data1201.dat`.
2. The matching static grid file `grid_mks.in`.
3. An output directory for Stokes CSV files, analysis results, and figures.

Every `dataNNNN.dat` file must use the same fixed SMR grid and primitive-variable layout. At startup, the active fluid backend discovers the entire input directory and requires complete files, strictly increasing header times, and a uniform cadence. The first frame, last frame, and cadence are discovered automatically. Before imaging, slow light selects only reference frames whose complete time windows are supported by the input data. Insufficient data on either side raise an error before computation begins; values are not clamped to an input boundary.

Set real absolute paths in [apps/grrt/GRRTConfig.h](apps/grrt/GRRTConfig.h):

```cpp
inline const std::filesystem::path DATA = "D:/CoportSL-data/output";
inline const std::filesystem::path GRID = "D:/CoportSL-data/grid_mks.in";
inline const std::filesystem::path OUTPUT = "D:/CoportSL-data/result";
constexpr int FLUID_BACKEND = BHAC;
```

These defaults are examples and must be replaced before use. The Python BHAC reader reads complete frames in AMR leaf-block order; one loading thread is usually sufficient for a mechanical disk.

## Building from source

### Windows

Open `CoportSL.slnx` with Visual Studio. The solution contains the routine research program `CoportSL` and exposes only x64 configurations, preventing memory-intensive jobs from accidentally using a 32-bit executable.

Select the routine program by changing the single default target line in [apps/RunConfig.h](apps/RunConfig.h):

```cpp
#define COPORTSL_APP COPORTSL_GRRT
// Alternatively use COPORTSL_FLUX or COPORTSL_BENCHMARK.
```

Set `CoportSL` as the startup project, then build and run it directly. Changing the target recompiles the source files that depend on this configuration. To build from the command line and confirm the selected target:

```powershell
msbuild .\CoportSL.vcxproj /p:Configuration=Release /p:Platform=x64
.\build\bin\x64\Release\CoportSL.exe --show-app
```

### Linux / WSL

Use the root `CMakeLists.txt`. Building without a target produces all three executables; individual targets can also be selected:

```bash
cmake -S . -B build/cmake-linux -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build/cmake-linux --parallel

cmake --build build/cmake-linux --target GRRT --parallel
cmake --build build/cmake-linux --target Flux --parallel
cmake --build build/cmake-linux --target Benchmark --parallel
```

Executables are written to `build/cmake-linux/bin/`. Windows drives are normally mounted under `/mnt/` in WSL, so replace Windows paths in the configuration headers with the corresponding Linux mount paths before running. The paths do not need to exist when only compiling.

### Input inspection

GRRT provides a read-only input inspection command. It creates no result directory and performs neither ray tracing nor radiative transfer. Use it to confirm the discovered frame range, frame count, cadence, and two-level signatures:

```powershell
.\build\bin\x64\Release\CoportSL.exe --inspect-input
```

## Windows desktop source build

This section is for contributors who want to run or package the graphical application from source. End users should download `CoportSL.exe` from [GitHub Releases](https://github.com/Qfun001/CoportSL/releases) and follow the [desktop user guide](USER_GUIDE.md).

`desktop/` provides the Windows graphical interface and invokes the GRRT, Flux, and Benchmark workers through JSON jobs. The interface supports Flux calibration, slow-light pre-analysis, fast- and slow-light imaging, region-error calculations, post-processing, GRMHD tools, and performance benchmarks.

Build the workers and launch the application from source:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-desktop.txt
powershell -ExecutionPolicy Bypass -File .\desktop\packaging\build-workers.ps1
.\.venv\Scripts\python.exe -m desktop
```

Build the single-file distribution:

```powershell
powershell -ExecutionPolicy Bypass -File .\desktop\packaging\build.ps1
```

The completed release candidate is written to `dist\CoportSL.exe`. Before publishing a version, launch this file, verify its SHA-256 checksum, and attach it to the matching GitHub Release as the `CoportSL.exe` asset.

Generated `build/`, `dist/`, and `CoportSL-data/` directories contain local build or runtime data and are excluded from Git.

## 1. Calibrate the accretion rate with Flux

Before production imaging, select `COPORTSL_FLUX` in `RunConfig.h`. Use a representative fast-light interval to estimate the mean flux density, then adjust `MDOT` in [apps/flux/FluxConfig.h](apps/flux/FluxConfig.h).

Frequently used parameters:

- `MDOT`: trial physical accretion rate in solar masses per year.
- `TARGET_FLUX_JY`: target mean flux density; the default is `0.66 Jy`.
- `NT0`, `NT1`, and `DNT`: frame range and sampling stride used for the mean.
- `ELECTRON`, `OBS_TH`, `NU`, `NPIX`, and `FOV`: model and observing parameters that affect the mean flux.
- `DISTANCE_PC`: source-to-observer distance in parsecs.

Run:

```powershell
.\build\bin\x64\Release\CoportSL.exe
```

The reported `suggested_mdot_linear` and `suggested_mdot_sqrt` values are initial suggestions for the next scan. Absorption and Faraday terms also change with normalization, so flux density is generally not exactly proportional to `MDOT`. Rerun `Flux` after changing the value.

## 2. Fast-light imaging

After selecting `COPORTSL_GRRT` in `RunConfig.h`, choose one of the four GRRT tasks with the single enumeration in [apps/grrt/GRRTConfig.h](apps/grrt/GRRTConfig.h):

```cpp
constexpr Task TASK = Task::Fast;
```

Frequently used production-imaging parameters:

- `ELECTRON`: electron distribution model.
- `NPIX` and `FOV`: image resolution and field of view.
- `NU`: observing frequency in Hz; run each frequency separately.
- `OBS_R`, `OBS_TH`, and `OBS_PH`: observer position.
- `MBH`, `SPIN`, `MDOT`, and `MDOT_SIM`: black hole and accretion-rate parameters.
- `R_LOW`, `R_HIGH`, and `BETA0`: parameters of the R–β electron-temperature model.

Fast light processes every input snapshot discovered by the backend. Before tracing rays, the program searches for the latest complete result matching `TASK=fast`, `model_signature`, and the complete I/Q/U/V file list. A match is printed and reused immediately; when automatic post-processing is enabled, missing plots can be generated in that directory. `DATA`, `GRID`, and `OUTPUT` control only the current I/O locations and do not enter the result signature.

Run:

```powershell
.\build\bin\x64\Release\CoportSL.exe
```

Fast-light results are written under `OUTPUT/fast/outputNNNN/`:

```text
OUTPUT/
└── fast/
    └── output0001/
        ├── status.txt
        ├── config.txt
        ├── I1000.csv
        ├── Q1000.csv
        ├── U1000.csv
        ├── V1000.csv
        └── ...
```

`fast`, `analysis`, `slow`, `region_error`, `benchmark`, and the two `interp_err` categories use independent numbering. Only canonical `outputNNNN` directories are recognized. A request is reused when its identity matches and all requested CSV files are complete. For incomplete Fast or Slow results, the complete requested frame range is overwritten; other tasks create the next numbered directory. `status.txt` records an audit trail of the path and `running`, `complete`, or `failed` states, but does not determine completeness.

Production `config.txt` files store only portable numerical semantics. The automatically discovered timeline always records the first and last source frame numbers as `Input::NT0` and `Input::NT1`, the first frame time as `Input::T0`, and the minimum adjacent interval as `Input::DT`. For uniformly sampled input,

$$
t(n)=\mathrm{Input::T0}
 +(n-\mathrm{Input::NT0})\mathrm{Input::DT}.
$$

Irregular input additionally records `Input::CADENCE=irregular`, `Input::FRAME_COUNT`, and `Input::FRAME.<i>.INDEX/TIME` for every discovered position. Source frame numbers may contain gaps; interpolation follows the explicit times and never invents a missing file. Absolute data, grid, and output paths are omitted. `model_signature` is a 64-character hexadecimal SHA-256 string determined by the grid, first-snapshot content, complete timeline, and shared numerical parameters. Copying identical input to another disk or operating system preserves the signature. A directory number carries no model or parameter meaning.

## 3. Slow-light pre-analysis

The slow-light region and valid time window depend on the GRMHD data, electron model, frequency, and viewing direction. Values derived for another configuration cannot be reused directly. To run pre-analysis independently:

```cpp
namespace Config {
constexpr Task TASK = Task::Analysis;
}
namespace Analysis {
constexpr double SAMPLE_DT = 10.0; // Units: rg/c.
}
```

Analysis covers the complete timeline discovered by the backend and samples physical times according to `SAMPLE_DT`; the final frame is included when the regular stride does not land on it. Uniform input requires `SAMPLE_DT / Input::DT` to be a positive integer within floating-point tolerance. For irregular input, the first frame no earlier than each target time is selected and duplicate selections are skipped. `REGION_TOLERANCES` gives the permitted contribution outside the slow-light region for each of six transfer-coefficient classes.

Region selection uses the six nonnegative support amplitudes $j_I$, $j_P$, $\alpha_I$, $\alpha_P$, $\rho_V$, and $\rho_C$, where

$$
j_P=\sqrt{j_Q^2+j_U^2+j_V^2},\qquad
\alpha_P=\sqrt{\alpha_Q^2+\alpha_U^2+\alpha_V^2},\qquad
\rho_C=\sqrt{\rho_Q^2+\rho_U^2}.
$$

For every frame and coefficient class, contributions are first normalized across regions and then averaged over valid analysis frames. For each class, Suggest accumulates regions in descending order of mean contribution until the tolerance is met, then takes the union across all six classes. Region-offset histograms use integer `frame_offset` values weighted by affine step length. `p90`, `p95`, `p99`, and `p99.9` are the shortest contiguous signed-delay intervals covering the corresponding fraction of the total affine-step weight; `full` uses both endpoints of all offsets.

`analysis_signature` extends `model_signature` with the analysis method, sampling interval, tolerances, region definitions, and time origin. The program reuses only the newest complete analysis batch with a matching signature and all required files. Absolute paths and modification times are excluded from the signature.

Analysis results are written in numbered batches under `OUTPUT/analysis/outputNNNN/`:

```text
OUTPUT/
└── analysis/
    └── output0001/
        ├── status.txt
        ├── config.txt
        ├── regions/
        │   ├── index.csv
        │   ├── <region_key>/
        │   │   ├── contribution.csv
        │   │   ├── offset_histogram.csv
        │   │   ├── time_span.csv
        │   └── ...
        └── suggest/
            ├── regions.txt
            ├── time_span.csv
            └── windows.csv
```

`regions/index.csv` stores stable keys, physical labels, and sample counts. Each region's `contribution.csv` stores the six absolute contributions by frame, `offset_histogram.csv` stores integer offsets and weights, and `time_span.csv` stores per-pixel time spans. `suggest/regions.txt` contains the suggested region keys, while `suggest/windows.csv` contains the exact endpoints of all five windows.

## 4. Slow-light imaging

A slow-light task first reuses the latest complete analysis matching `analysis_signature`. If none exists, analysis is generated in the same process before imaging continues. Suggest uses the analysis recommendation; Manual selects one combination from the shared named sets:

```cpp
namespace Config {
constexpr Task TASK = Task::Slow;
}
namespace SlowLight {
constexpr RegionMode REGION_MODE = RegionMode::Suggest;
constexpr Window WINDOW = Window::P99;
inline const std::vector<RegionSelection> REGION_SETS = {
    {"r20", {"region_000"}},
    {"r50", {"region_000", "region_001", "region_002"}},
};
constexpr std::string_view MANUAL_SET = "r50";
}
```

`REGION_SETS` is shared by manual slow light and manual RegionError. Names must be unique and keys must belong to the active `SlowLight::REGION`; sets may overlap and need not be nested. The final window endpoints and safe output range are calculated at runtime from the selected regions and input timeline.

Run:

```powershell
.\build\bin\x64\Release\CoportSL.exe
```

Slow-light results are written under `OUTPUT/slow/outputNNNN/`:

```text
OUTPUT/
└── slow/
    └── output0001/
        ├── status.txt
        ├── config.txt
        ├── time_span.csv
        ├── I<frame>.csv
        ├── Q<frame>.csv
        ├── U<frame>.csv
        ├── V<frame>.csv
        └── ...
```

The slow-light configuration refers to the analysis with a relative `analysis_path` and records `analysis_signature`, the selection mode, stable region keys, window name, and exact `LEFT/RIGHT` endpoints. References remain valid after copying the complete `result` directory. Samples inside the slow-light region but outside the time window use the nearest endpoint; samples outside the region use the reference frame. Output is produced only for reference frames whose complete windows are supported by the input timeline.

Region-truncation error is a separate task and does not modify pre-analysis:

```cpp
namespace Config {
constexpr Task TASK = Task::RegionError;
}
namespace RegionError {
constexpr int FRAME_STEP = 25;
}
```

Starting from the first frame of the complete input timeline, the program selects every `FRAME_STEP`-th frame. A final frame that does not align with the stride is omitted; actual frame numbers are recorded in `config.txt`. One task scans all named sets in `SlowLight::REGION_SETS` order. For each set, it separately disables emission outside the region and all transfer coefficients outside the region, comparing both with the full fast-light image at the same frame. Each set writes `region_error/outputNNNN/<set>/error.csv` with fields `frame,mode,I_error,Q_error,U_error,V_error`. The root `config.txt` preserves set order and keys through `RegionError::SETS` and `RegionError::SET.<set>`. All four components are normalized by the reference total Stokes I. Post-processing computes the arithmetic mean and sample standard deviation across representative frames; per-pixel spatial residuals are not stored.

Zero-emission regions use the homogeneous transfer branch and skip source-term integration. Before inverse cosine is evaluated, polarization-basis projection clamps the floating-point cosine to `[-1,1]`, preventing rounding at the parallel limit from producing non-finite Q/U. RegionError still checks every Stokes pixel in reference and truncated images and reports the frame, set, mode, pixel, and component on failure.

## 5. Time alignment and plotting

`Postprocess::RUN` is the only C++ switch for automatic post-processing. When disabled, Python is not started and `plot/` is not created. When enabled, a numerical task first writes `status.txt=complete`, then invokes the fixed entry point:

```cpp
namespace Postprocess {
constexpr bool RUN = true;
}
```

The same entry point can be invoked manually for a completed result in the current format:

```powershell
python .\tools\postprocess.py D:\CoportSL-data\result\slow\output0001
```

Fixed products:

- Analysis: one `plot/contribution.pdf`.
- Fast: `plot/flux.csv/.pdf`, `lp.csv/.pdf`, and `beta2.csv/.pdf`.
- Slow: the three Fast product groups plus `time_window.pdf` and `time_span.pdf`. The highest-numbered complete fast-light result with the same `model_signature` is selected, and relative references are written to root `fast.txt` and `plot/time_alignment.csv`.
- RegionError: `plot/error.pdf` with sample-standard-deviation error bars and `plot/error_summary.csv`.

Automatically generated CSV files do not duplicate time, pixel count, or total intensity values derivable from `config.txt`. Fields are `frame,F_nu_Jy` for `flux.csv`, `frame,local_linear_fraction,net_linear_fraction` for `lp.csv`, and `frame,beta2_abs,beta2_angle_deg` for `beta2.csv`. Python reconstructs physical time from `Input::...` entries.

`fast.txt` records the relative fast-light path, time shift added to the slow-light timeline, correlation coefficient, search interval, minimum overlap fraction, actual overlap frame count, and `Input::DT`. If no complete matching fast-light result exists, post-processing of the slow-light result still succeeds and skips alignment. A Python failure writes `failed` only to `plot/status.txt`; it does not change a completed C++ numerical result to failed.

The automatic entry point does not create EVPA products, frame PNG files, or videos. Fast and Slow print manual commands after completion. The manual entry point creates PNG and PDF output by default:

```powershell
python .\tools\evpa_plot.py D:\CoportSL-data\result\slow\output0001
```

Publication-oriented comparisons across batches, temporal-interpolation errors, and GRMHD figures are configured explicitly in `tools/run.py`, `tools/interp_err.py`, and `tools/bhac_plot.py`. Each script centralizes its parameters in `configure_parameters()`.

## 6. Benchmarking

Benchmark configuration lives in [apps/benchmark/BenchmarkConfig.h](apps/benchmark/BenchmarkConfig.h). Routine use primarily changes:

- `CORE_MODES`: the single physical-core group tested by this run.
- `NPIX_LIST`: image-resolution values.
- `CORE_COUNTS`: physical-core counts, with one OpenMP thread per core.

Benchmark uses fixed Thermal, 230 GHz, $512^2$, and Shell settings to calculate the two-level signatures. A complete matching pre-analysis and all required files must already exist under `OUTPUT/analysis`. Timing starts only after the analysis Suggest regions and exact `p99` window are loaded. Analysis is not generated during performance measurement, so Benchmark follows pre-analysis, fast/slow imaging, and region-error calculations in the full workflow.

Each Benchmark run initializes the fixed grid once. Each value in `NPIX_LIST` constructs ray geometry, fluid-grid locations, and the slow-light mask once. The fast-light active frame or slow-light `FrameCache` for each repeat is also prepared once and reused read-only by every core count at that resolution. Radiative transfer is then executed and timed for each core configuration.

Every benchmark writes to a non-overwriting `OUTPUT/benchmark/outputNNNN/`. `config.txt` stores the signature, Suggest regions, and window; `status.txt` stores the actual relative analysis path; and `summary.csv` stores scan results. [tools/benchmark.py](tools/benchmark.py) resolves the analysis from `status.txt` and generates:

- `time.*`: imaging runtime.
- `rate.*`: ray throughput.
- `grmhd_memory.*`: structured memory use of the active grid and one GRMHD frame.
- `frame_cache.*`: slow-light frame-cache estimates for the automatic selection and every raw region at different time windows.

`summary.csv` has eleven columns containing propagation type, resolution, physical-core count, actual grid and sample counts, active-grid and single-frame memory, and the means and standard deviations of per-frame update and radiative-transfer times. CPU model and core type are stored only in `config.txt`; ray count, image memory, throughput, and total time are derived from retained columns.

## Auxiliary analysis tools

[tools/interp_err.py](tools/interp_err.py) evaluates two classes of temporal linear-interpolation error. It reads BHAC frames, converts primitive variables, compares interpolation errors at multiple time intervals, and measures the systematic attenuation of $\sqrt{b^2}$. Outputs include `b_interp.csv`, `error_dt.*`, and `error_r.*`.

The same script also uses the original fast-light cadence as a baseline and interpolates coarser-cadence results back to baseline times. At each target frame, I/Q/U/V image errors are normalized by the reference image's total Stokes I. It then computes the arithmetic mean and sample standard deviation across frames and writes `obs_interp_t.csv`, `obs_interp.csv`, and `error_img.*`. `obs_interp_t.csv` stores four scalar errors per target frame; `obs_interp.csv` stores each time interval's mean and temporal standard deviation. Error plots use the mean as the data point and temporal standard deviation as the error bar.

Configure paths and parameters centrally in `configure_parameters()`, then uncomment one line in `main()` to select primitive calculation, primitive plotting, I/Q/U/V image-error calculation, or image-error plotting. The default run only prints input and output paths.

[tools/bhac_plot.py](tools/bhac_plot.py) generates GRMHD plane maps and volume-weighted profiles directly from BHAC `dataNNNN.dat`, without an intermediate MATLAB `.mat` file. It reuses the sequential mechanical-disk reader in [tools/bhac/read_bhac.py](tools/bhac/read_bhac.py) and primitive conversion in [tools/bhac/c2p.py](tools/bhac/c2p.py). Electron temperature, magnetization, plasma beta, Bernoulli parameter, and nonthermal-electron parameters follow the current C++ BHAC backend. The legacy color maps, scales, horizon, boundaries, magnetic field lines, and large-format typography are retained, while plotted time is read directly from the frame header.

`configure_parameters()` uses absolute input and output paths; the example output is `D:/CoportSL-data/result/GRMHDplot`. The default run prints paths only. Uncomment `plot_frames(parameters)`, `plot_profiles(parameters)`, or `make_quantity_movie(parameters, ...)` in `main()` to execute the corresponding task. Each frame is read once and used to calculate all selected physical quantities, avoiding repeated seeks on mechanical disks. AMR one-dimensional statistics use proper-cell-volume weights. Videos and mosaics are generated by the shared [tools/lib/media.py](tools/lib/media.py).

## Result directory layout

```text
result/
├── fast/
│   └── output0001/
│       └── plot/
├── slow/
│   └── output0001/
│       └── plot/
├── analysis/
│   └── output0001/
│       └── plot/
├── benchmark/
│   └── output0001/
│       └── plot/
├── interp_err/
│   ├── b_interp/output0001/
│   │   └── plot/
│   └── obs_interp/output0001/
│       └── plot/
├── GRMHDplot/
│   ├── xz/
│   ├── xy/
│   ├── xz_xy/
│   ├── profile/
│   └── movie/
└── comparison/
    ├── radius_scan/
    └── window_scan/
```

Run directories do not encode physical parameters. The electron model, viewing angle, frequency, region definition, and window are defined by that directory's `config.txt`. Derived Python CSV files, figures, and videos are written to the same run's `plot/` subdirectory. Controlled-variable scans across multiple runs are written to `result/comparison/<name>/`. Record both the run number and configuration file when comparing or publishing results.

## Source layout

```text
apps/                         Unified entry point, target selection, and app configuration
├── Main.cpp
├── RunConfig.h
├── grrt/
├── flux/
└── benchmark/
src/
├── physics/
│   ├── Constants.h            Fundamental constants and unit conversion
│   ├── Model.h                Model selection and derived configuration
│   ├── fluid/                Fluid backends, grid location, and frame cache
│   ├── spacetime/            Metrics, connection, and geodesic equations
│   └── transfer/             Electron distributions and polarized transfer
├── grrt/
│   ├── RayGeometry.*          Ray geometry
│   ├── StokesProjection.*     Stokes screen projection
│   ├── fast/                 Fast-light transfer and region statistics
│   └── slow/                 Slow-light regions, time windows, and pre-analysis
└── support/
    ├── RunDirectory.*         Run directory and output management
    └── numerics/             DP5 integration and linear algebra
tools/                        Python plotting and post-processing
desktop/                      Windows GUI, worker overlay, and packaging configuration
build/                        Build output excluded from Git
```

## Validation and limitations

- GitHub Actions builds command-line targets on Windows and Linux and checks the Python source.
- The fixed SMR grid is initialized once; scans reload only fluid variables for each frame.
- Fast light, pre-analysis, and slow light share `ray::RayGeometry` and `fluid::GridLocations`. Once slow light generates an analysis result, it does not retrace geodesics or relocate the grid.
- `fluid::FrameCache` manages the general time window. The BHAC backend stores primitive-frame payloads as `float` and performs spatial and temporal interpolation as `double`.
- BHAC data on a fixed SMR grid are currently the only runtime backend. No sample GRMHD data are included.
- BHAC grid, frame-header, and primitive-payload reads check exact lengths, positioning, and close status. Truncated, incomplete, or unreadable input stops at the first failure. Local pre-release validation covers signatures, result compatibility, CSV completeness, run locks, complete-range recomputation, frame ranges, and RegionError sampling; test files are not distributed with the public source.

## Citation, software, and data availability

- The current software version is `v0.6.5`. Cite CoportSL using the metadata in [CITATION.cff](CITATION.cff). Version `v0.6.5` is archived at [doi:10.5281/zenodo.22708025](https://doi.org/10.5281/zenodo.22708025); the archive for all versions is available at [doi:10.5281/zenodo.22708024](https://doi.org/10.5281/zenodo.22708024).
- The repository does not contain the original GRMHD snapshots used for the paper. See [Input data](#input-data) for the data format and input requirements.
- For reasonable requests concerning the GRMHD data used in the paper, contact Fan Zhou at `202631101012@mail.bnu.edu.cn` to discuss access.

## License and provenance

This project inherits the GNU Affero General Public License v3.0 from the original CoportS project; see [LICENSE.txt](LICENSE.txt). Shared or modified versions must retain the original author information, source provenance, and the same license requirements.
