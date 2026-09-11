#pragma once

#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <numbers>
#include <string>
#include <string_view>
#include <vector>

#include "src/grrt/slow/regions/RegionDefinition.h"
#include "src/grrt/slow/regions/RegionSelector.h"

// User configuration for GRRT; production imaging and automated slow-light pre-analysis share these parameters.
namespace Config {

inline std::filesystem::path DATA = "D:/CoportSL-data/output"; // Runtime can be overridden by JSON jobs.
inline std::filesystem::path GRID = "D:/CoportSL-data/grid_mks.in";
inline std::filesystem::path OUTPUT = "D:/CoportSL-data/result";

enum class Task { Analysis, Fast, Slow, RegionError };
#ifndef COPORTSL_TASK
inline Task TASK = Task::Analysis;
#else
inline Task TASK = static_cast<Task>(COPORTSL_TASK);
#endif

inline int NPIX = 512; // Number of pixels along one side of the square image.
inline int FRAME_START = -1; // -1 means Fast/Slow automatically uses all legal output frames.
inline int FRAME_END = -1; // -1 means use the last found frame.
inline double FOV = std::numbers::pi / 64.0; // Camera field-of-view angle, in rad.
inline double NU = 230e9; // Observation frequency, unit Hz; one run only corresponds to one frequency.

inline double OBS_T = 0.0; // Observer coordinate time.
inline double OBS_R = 500.0; // Observer radius, in rg.
inline double OBS_TH = 163.0 * std::numbers::pi / 180.0; // Polar angle from the rotation axis, in rad.
inline double OBS_PH = 0.0001; // Observer azimuthal coordinate, in rad.
inline std::array<double, 4> OBS = {
    OBS_T,
    std::log(OBS_R),
    OBS_TH,
    OBS_PH
};

constexpr int CAR = 0; // Cartesian coordinate identifier.
constexpr int BL = 1; // Boyer-Lindquist coordinate identifier.
constexpr int MBL = 2; // Modified Boyer-Lindquist coordinate identifier.
constexpr int KS = 3; // Kerr-Schild coordinate identifier.
constexpr int MKS = 4; // Modified Kerr-Schild coordinate identifier.
constexpr int MKSHARM = 5; // HARM modified Kerr-Schild coordinate identifier.
constexpr int MKSBHAC = 6; // BHAC modified Kerr-Schild coordinate identifier.
constexpr int MKSN = 7; // Alternate modified Kerr-Schild coordinate identifier.
constexpr int CKS = 8; // Cartesian Kerr-Schild coordinate identifier.
constexpr int METRIC = MKSBHAC; // Active coordinate and metric choice; must match the input dataset.
inline double SPIN = 0.9375; // Dimensionless Kerr spin a/M.
inline double HS = 0.0; // Polar deformation parameter used by MKSBHAC.

constexpr int BHAC = 1; // BHAC GRMHD plasma model identifier.
constexpr int FLUID_BACKEND = BHAC; // The fluid backend used by the current data, manually specified by the user.

constexpr int THERMAL = 0; // Pure thermal electron distribution identifier.
constexpr int POWER_LAW = 1; // Thermal plus Power-law electron distribution identifier.
constexpr int BEAM = 2; // Thermal plus Beam-like electron distribution identifier.
constexpr int LOSS_CONE = 3; // Thermal plus Loss-cone electron distribution identifier.
#ifndef COPORTSL_ELECTRON
inline int ELECTRON = POWER_LAW; // Active electron distribution model.
#else
inline int ELECTRON = COPORTSL_ELECTRON; // Build-time override for batch runs.
#endif

inline double MBH = 6.5e9; // Black-hole mass, in solar masses.
inline double MDOT = 2.46e-4; // Physical source accretion rate, in solar masses per year.
inline double MDOT_SIM = 50.0; // GRMHD accretion normalization in MBH/T_unit; must match the dataset.

inline double R_LOW = 10.0;
inline double R_HIGH = 100.0;
inline double BETA0 = 1.0;
inline double SIGMA_MAX = 20.0;
inline double THETAE_EMIT = 0.10;
inline double NE_EMIT = 1.0e2;
inline double POL_LIMIT = 0.95;

inline double P_MIN = 2.001;
inline double P_MAX = 10.0;
inline double GAMMA_RATIO = 1.0e5;
inline double BEAM_ANGLE = 0.0;
inline double BEAM_WIDTH = 0.1;

inline double RAY_ATOL = 1e-7;
inline double RAY_RTOL = 1e-8;
inline double RAY_HMIN = 1e-10;
inline double RAY_LMAX = 1e5;
inline double RAY_H0 = 10.0;
inline double RAY_CELL = 0.85;
inline double RAY_HORIZON = 1.1;

inline double R_SOURCE = 200.0; // Outer radius of the fast-light emitting region, in rg.

} // namespace Config

// Automatic slow-light pre-analysis parameters. Analysis shares NPIX, NU, FOV, and OBS with production imaging,
// Therefore, the same ray cache can be reused in the same process.
namespace Analysis {

inline double SAMPLE_DT = 10.0; // Pre-analysis physical sampling interval, unit rg/c.
inline slow_light::regions::CoefficientTolerances REGION_TOLERANCES = {
    1.0e-3, // jI // 2.0e-3
    1.0e-3, // jP // 2.0e-3
    1.0e-3, // aI // 1.0e-3
    1.0e-3, // aP // 1.0e-3
    1.0e-1, // rhoV // 2.6e-1
    2.0e-3  // rhoC // 2.5e-2
};

} // namespace Analysis

// Slow-light workflow control. Analysis mode generates or reuses pre-analysis and exits; imaging mode continues with image calculation.
namespace SlowLight {

// Current spatial partitions; see regions/definitions/ for detailed geometry and radial boundaries.
inline auto PARTITION = slow_light::regions::Partition::Shell;
inline slow_light::regions::RegionDefinition REGION =
    slow_light::regions::definition(PARTITION);

enum class RegionMode {
    Suggest,
    Manual
};

enum class Window { P90, P95, P99, P99_9, Full };

inline RegionMode REGION_MODE = RegionMode::Suggest;
inline Window WINDOW = Window::P99;

// Shell available keys: region_000 to region_005.
// Currently r20/r30/r50/r80/r100/r200 show the common radial combinations for Shell.
// JetShell available keys: north_000 to north_005, south_000 to south_005,
// non_jet_000 to non_jet_005. The desktop and runtime follow the established production slow-light definitions
// Nested set of Omega1 to Omega7, where Omega4 is the Suggest and Omega7 is the full range.
// After switching PARTITION, the collection should be configured according to the current scientific research problem; the exact boundary shall be subject to the specific definition file.
inline std::vector<slow_light::regions::RegionSelection> REGION_SETS = {
    {"r20", {"region_000"}},
    {"r30", {"region_000", "region_001"}},
    {"r50", {"region_000", "region_001", "region_002"}},
    {"r80", {"region_000", "region_001", "region_002", "region_003"}},
    {"r100", {
        "region_000", "region_001", "region_002", "region_003",
        "region_004"}},
    {"r200", {
        "region_000", "region_001", "region_002", "region_003",
        "region_004", "region_005"}}
};
inline std::string MANUAL_SET = "r50";

} // namespace SlowLight

// Region-truncation error task; scan every named set in SlowLight::REGION_SETS.
namespace RegionError {

inline int FRAME_STEP = 25; // Positive integer frame sampling interval starting from the first frame of the input.

} // namespace RegionError

// Fixed whether to call Python postprocessing when numerical results are complete; plot/ is not created when turned off.
namespace Postprocess {

inline bool RUN = false;

} // namespace Postprocess
