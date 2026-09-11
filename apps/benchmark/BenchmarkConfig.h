#pragma once

#include <array>
#include <cmath>
#include <filesystem>
#include <numbers>
#include <string_view>

#include "src/grrt/slow/regions/RegionDefinition.h"
#include "src/grrt/slow/regions/RegionSelector.h"

// User profile for the Benchmark project.
// Users usually only need to modify the scan parameters in BenchmarkConfig below.
namespace Config {

// Fixed Baseline Model: These parameters affect the GRRT calculation of the measured speed, but Benchmark does not scan them.
inline const std::filesystem::path DATA = "D:/CoportSL-data/output"; // Absolute snapshot directory of the active fluid backend.
inline const std::filesystem::path GRID = "D:/CoportSL-data/grid_mks.in"; // Static BHAC grid file.
inline const std::filesystem::path OUTPUT = "D:/CoportSL-data/result"; // Benchmark output root directory.

constexpr int NPIX = 512; // Reference resolution used to match production pre-analysis.
constexpr double FOV = std::numbers::pi / 64.0; // Camera field of view, unit rad.
constexpr double NU = 230e9; // The observation frequency shared by pre-analysis and Benchmark, in Hz.
constexpr double OBS_T = 0.0;
constexpr double OBS_R = 500.0; // Viewer radius, unit rg.
constexpr double OBS_TH = 163.0 * std::numbers::pi / 180.0; // Observer polar angle, unit rad.
constexpr double OBS_PH = 0.0001;
inline const std::array<double, 4> OBS = {
    OBS_T,
    std::log(OBS_R),
    OBS_TH,
    OBS_PH
};

constexpr int CAR = 0;
constexpr int BL = 1;
constexpr int MBL = 2;
constexpr int KS = 3;
constexpr int MKS = 4;
constexpr int MKSHARM = 5;
constexpr int MKSBHAC = 6;
constexpr int MKSN = 7;
constexpr int CKS = 8;
constexpr int METRIC = MKSBHAC;
constexpr double SPIN = 0.9375;
inline double HS = 0.0; // Covered by hslope in the active BHAC mesh.

constexpr int BHAC = 1;
constexpr int FLUID_BACKEND = BHAC; // The fluid backend used by the current data, manually specified by the user.

constexpr int THERMAL = 0;
constexpr int POWER_LAW = 1;
constexpr int BEAM = 2;
constexpr int LOSS_CONE = 3;
constexpr int ELECTRON = THERMAL; // Performance benchmarks fix the hot electron model to avoid physical parameter scans being mixed into speed tests.

constexpr double MBH = 6.5e9; // Black hole mass, unit mass of the sun.
constexpr double MDOT = 3.7e-4; // Physical accretion rate, unit solar mass per year.
constexpr double MDOT_SIM = 50.0; // Simulated accretion rate normalized in MBH/T_unit.

// Electron temperature, magnetization and emission threshold.
constexpr double R_LOW = 10.0;
constexpr double R_HIGH = 100.0;
constexpr double BETA0 = 1.0;
constexpr double SIGMA_MAX = 20.0;
constexpr double THETAE_EMIT = 0.10;
constexpr double NE_EMIT = 1.0e2;
constexpr double POL_LIMIT = 0.95;

// Compatibility parameters for shared nonthermal-electron modules. Benchmark fixes Thermal and does not scan these values.
constexpr double P_MIN = 2.001;
constexpr double P_MAX = 10.0;
constexpr double GAMMA_RATIO = 1.0e5;
constexpr double BEAM_ANGLE = 0.0;
constexpr double BEAM_WIDTH = 0.1;

constexpr double RAY_ATOL = 1e-7;
constexpr double RAY_RTOL = 1e-8;
constexpr double RAY_HMIN = 1e-10;
constexpr double RAY_LMAX = 1e5;
constexpr double RAY_H0 = 10.0;
constexpr double RAY_CELL = 0.85;
constexpr double RAY_HORIZON = 1.1;

constexpr double R_SOURCE = 200.0;

} // namespace Config

namespace Analysis {

inline const std::filesystem::path OUTPUT = Config::OUTPUT / "analysis";
constexpr double SAMPLE_DT = 10.0;
inline constexpr slow_light::regions::CoefficientTolerances REGION_TOLERANCES = {
    1.0e-3,
    1.0e-3,
    1.0e-3,
    1.0e-3,
    1.0e-1,
    2.0e-3
};

} // namespace Analysis

namespace BenchmarkConfig {

// Benchmark uses the Suggest region and specified window that match the previous analysis.
constexpr auto PARTITION = slow_light::regions::Partition::Shell;
inline const slow_light::regions::RegionDefinition& REGION =
    slow_light::regions::definition(PARTITION);
inline constexpr std::string_view WINDOW = "p99";
inline const std::filesystem::path OUTPUT = Config::OUTPUT / "benchmark";

// Performance measurements use time ranges and output frame intervals, not GRRT input data boundaries.
constexpr int NT0 = 2400;
constexpr int NT1 = 2450;
constexpr int DNT = 1;

// Primary scan variables for publication performance benchmarks.
constexpr std::array NPIX_LIST = {64, 128, 256, 512};
// Only one OpenMP thread runs per physical core.
constexpr std::array CORE_COUNTS = {1, 2, 3, 4, 5, 6, 7, 8};

// Fixed observation frequency. Modifying this value changes the model signature used for matching analysis.
constexpr double NU = Config::NU;
constexpr int REPEATS = 1;
constexpr int WARMUP_FRAMES = 1;

constexpr bool RUN_FAST_LIGHT = true;
constexpr bool RUN_SLOW_LIGHT = true;

enum class CoreMode {
    AllLogical,
    PhysicalCores,
    PerformanceCores,
    EfficiencyCores
};

constexpr std::array CORE_MODES = {
    CoreMode::PerformanceCores,
    // CoreMode::EfficiencyCores
};

static_assert(NT0 <= NT1 && DNT > 0);
static_assert(!NPIX_LIST.empty() && !CORE_COUNTS.empty());
static_assert(CORE_MODES.size() == 1);
static_assert(CORE_MODES.front() != CoreMode::AllLogical);
static_assert(REPEATS > 0);
static_assert([] {
    for (int npix : NPIX_LIST) {
        if (npix <= 0) return false;
    }
    for (int cores : CORE_COUNTS) {
        if (cores <= 0) return false;
    }
    return true;
}());

} // namespace BenchmarkConfig

// The signature module uses the same region namespace boundary as GRRT.
namespace SlowLight {

inline const slow_light::regions::RegionDefinition& REGION =
    BenchmarkConfig::REGION;

} // namespace SlowLight
