# CoportSL Desktop User Guide

English | [简体中文](USER_GUIDE-zh.md)

This guide is for people using the packaged Windows application. Developers who want to compile or modify CoportSL should follow the build instructions in the [project README](README.md#building-from-source).

## 1. Download and launch

1. Open the [CoportSL Releases page](https://github.com/Qfun001/CoportSL/releases).
2. Open the release you want and download `CoportSL.exe` from its **Assets** section. The source-code archives do not contain the built application.
3. Optionally compare the file's SHA-256 checksum with the value published in the release notes.
4. Move `CoportSL.exe` to a writable folder and double-click it. It is a portable, single-file application; Python and Visual Studio are not required.

The first launch can take several seconds while the single-file package extracts its runtime components. CoportSL is currently distributed without a commercial code-signing certificate, so Windows SmartScreen may show an **Unknown publisher** warning. Continue only when the file came from the official Releases page and its checksum matches the release notes; select **More info > Run anyway** if needed.

CoportSL prefers to store settings, job descriptions, status files, and logs in a `CoportSL-data` folder beside the executable. If that folder is not writable, it uses the current Windows user's application-data directory. The exact active path is shown on the **Settings** page. Scientific input and result directories are selected separately and are never embedded in the executable.

## 2. Prepare input data

The application does not include GRMHD simulation data. For the currently supported BHAC backend, prepare:

- one directory containing a fixed-SMR sequence named `dataNNNN.dat`, for example `data1200.dat` and `data1201.dat`;
- the matching static grid file `grid_mks.in`;
- a writable results directory with enough free space for Stokes CSV files, analysis records, figures, and videos.

All frames must use the same grid and primitive-variable layout. Header times must increase strictly and use a uniform cadence. Keep the original data and grid read-only when practical; CoportSL writes scientific outputs only under the selected results directory.

## 3. First-time setup

Open **Data and models** and select the BHAC data directory, grid file, and results root. The application discovers the available frame range and cadence automatically. Then review the source, camera, observer, ray-integration, electron-distribution, and slow-light analysis parameters.

Select **Check current settings** before a long run. A successful check confirms that the current fields can form a valid job and that the selected input files can be inspected. It does not guarantee that a scientifically expensive run will finish within the available memory or storage.

English is selected on a clean installation. To use Simplified Chinese, open **Settings**, choose **简体中文** under **Language**, and continue working; the window updates immediately and remembers the choice.

## 4. Interface map

| Page | Purpose |
| --- | --- |
| **Data and models** | Select input/output paths and define shared physical, camera, observer, ray, electron, region, and analysis parameters. |
| **Flux calibration** | Measure mean flux over selected frames and obtain trial accretion-rate suggestions. |
| **Imaging** | Run fast-light imaging, slow-light pre-analysis and imaging, or region-truncation error calculations. |
| **Post-processing** | Discover completed results and generate observables, EVPA products, comparisons, diagnostic plots, or videos. |
| **GRMHD tools** | Plot BHAC quantities and profiles, create time series or videos, and inspect interpolation behavior. |
| **Benchmark** | Measure scaling across image resolutions and CPU core selections. |
| **Run History** | Review job state and open the full log for previous runs. |
| **Settings** | Change language, theme, log capacity, and history retention; view the application-data path. |

The bar above the current page provides common actions. **Check current settings** validates the page, **Run current task** submits its job, and **Open results directory** opens the selected results root. On the Imaging page, **Slow light pre-analysis** is also available as a separate action.

## 5. Recommended workflow

### Step 1: calibrate flux

Open **Flux calibration**, select a representative inclusive frame range and sampling step, choose one or more frequencies, and enter the target flux density. Run the task and inspect the mean flux and suggested accretion rates. A suggestion is an initial value: update the accretion rate, run Flux again, and confirm the result because absorption and Faraday terms also change with normalization.

### Step 2: create a fast-light reference

Open **Imaging**, select **Fast Light**, and keep the automatic full frame range or enable a smaller manual range for a trial. Validate and run the job. A complete fast-light result provides the reference used by later alignment, comparison, and region-error tools.

### Step 3: run slow-light pre-analysis

Use **Slow light pre-analysis** on the Imaging page. The analysis evaluates coefficient support across the selected spatial partition and records suggested slow-light regions together with valid time windows. Changes to input content, shared model parameters, region definitions, or analysis tolerances change the analysis signature and may require a new analysis.

### Step 4: create slow-light images

Select **Slow Light**. **Suggest** mode uses the compatible analysis recommendation; **Manual** mode uses one of the named region sets defined on **Data and Models**. Choose a time window such as `p99`, validate, and run. If Suggest mode cannot find a compatible analysis, the job performs the pre-analysis before imaging.

### Step 5: inspect errors and create products

Use **Region Error** when you need to quantify truncation error for the named region sets. For ordinary figures and derived observables, open **Post-processing**, select a completed result, enable the required tasks and output formats, then run them. Fast-/slow-light comparisons require compatible complete results; the page reports any signature or parameter mismatch it finds.

### Step 6: use optional tools

**GRMHD tools** can create simulation-plane plots, profiles, accretion-rate or magnetic-flux time series, primitive-variable interpolation checks, and videos. **Benchmark** runs repeated performance measurements across selected resolutions and CPU groups. Both can consume substantial time, memory, storage, and CPU resources, so begin with a small frame range.

## 6. Jobs, logs, cancellation, and results

Only one scheduled job runs at a time. Its task drawer shows current status and recent output. Cancellation is cooperative and can take time while a worker finishes its current operation. Do not move, replace, or disconnect the input data, grid file, or results drive during a run.

Use **Run History** to refresh past jobs, open full logs, or open the job-record directory. Clearing history removes saved job descriptions, status records, and logs; it leaves original GRMHD data, scientific results, and figures untouched.

Scientific outputs are placed under the chosen results root in task-specific directories such as `analysis/`, `fast/`, `slow/`, `region_error/`, and `benchmark/`. Use **Post-processing > Refresh** after copying or completing results so the interface rescans their status and signatures.

## 7. Common problems

- **The application does not start:** download the executable again from the official release, verify its checksum, move it to a writable local folder, and retry. Security software may quarantine unsigned scientific applications.
- **No frames are found:** select the directory that directly contains `dataNNNN.dat`; confirm the names, read permissions, and complete file copies.
- **Grid or signature mismatch:** select the `grid_mks.in` that belongs to the chosen frame sequence. Do not combine grids and snapshots from different simulations.
- **A slow-light result has no valid frame range:** provide enough input frames on both sides of the requested observer times, or choose a narrower supported time window.
- **A post-processing comparison is unavailable:** complete compatible fast- and slow-light runs with matching input and model signatures, then refresh the result list.
- **A task fails or appears stalled:** open the task drawer or **Run History > View Log** and retain the full log when reporting an issue.

When reporting a reproducible problem, include the CoportSL version, Windows version, selected task, relevant parameter values, and the complete job log. Do not upload proprietary or restricted GRMHD data to a public issue.
