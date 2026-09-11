#pragma once

#include <array>
#include <cmath>
#include <filesystem>
#include <numbers>
#include <string_view>
#include <vector>

#include "src/grrt/slow/regions/RegionDefinition.h"
#include "src/grrt/slow/regions/RegionSelector.h"

// User profile for the Benchmark project.
// Users usually only need to modify the scan parameters in BenchmarkConfig below.
namespace Config {

// Standard Reference Model: These parameters affect the GRRT calculation of the speed being measured, but are not part of the performance scan dimension.
inline std::filesystem::path DATA = "D:/CoportSL-data/output";
inline std::filesystem::path GRID = "D:/CoportSL-data/grid_mks.in";
inline std::filesystem::path OUTPUT = "D:/CoportSL-data/result";

inline int NPIX = 512;
inline double FOV = std::numbers::pi / 64.0;
inline double NU = 230e9;
inline double OBS_T = 0.0;
inline double OBS_R = 500.0;
inline double OBS_TH = 163.0 * std::numbers::pi / 180.0;
inline double OBS_PH = 0.0001;
inline std::array<double, 4> OBS = {
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
inline double SPIN = 0.9375;
inline double HS = 0.0;

constexpr int BHAC = 1;
constexpr int FLUID_BACKEND = BHAC; // The fluid backend used by the current data, manually specified by the user.

constexpr int THERMAL = 0;
constexpr int POWER_LAW = 1;
constexpr int BEAM = 2;
constexpr int LOSS_CONE = 3;
inline int ELECTRON = THERMAL;

inline double MBH = 6.5e9;
inline double MDOT = 3.7e-4;
inline double MDOT_SIM = 50.0;

// Electron temperature, magnetization and emission threshold.
inline double R_LOW = 10.0;
inline double R_HIGH = 100.0;
inline double BETA0 = 1.0;
inline double SIGMA_MAX = 20.0;
inline double THETAE_EMIT = 0.10;
inline double NE_EMIT = 1.0e2;
inline double POL_LIMIT = 0.95;

// Standard nonthermal-electron parameters; included in signatures and calculations only for applicable electron models.
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

inline double R_SOURCE = 200.0;

} // namespace Config

namespace Analysis {

inline double SAMPLE_DT = 10.0;
inline slow_light::regions::CoefficientTolerances REGION_TOLERANCES = {
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
inline auto PARTITION = slow_light::regions::Partition::Shell;
inline slow_light::regions::RegionDefinition REGION =
    slow_light::regions::definition(PARTITION);
inline std::string WINDOW = "p99";

// Performance measurements use time ranges and output frame intervals, not GRRT input data boundaries.
inline int NT0 = 2400;
inline int NT1 = 2450;
inline int DNT = 1;

// Primary scan variables for publication performance benchmarks.
inline std::vector<int> NPIX_LIST = {64, 128, 256, 512};
// Only one OpenMP thread runs per physical core.
inline std::vector<int> CORE_COUNTS = {1, 2, 3, 4, 5, 6, 7, 8};

// Standard observation frequency. Modifying this value changes the model signature used for matching analysis.
inline double& NU = Config::NU;
inline int REPEATS = 1;
inline int WARMUP_FRAMES = 1;

inline bool RUN_FAST_LIGHT = true;
inline bool RUN_SLOW_LIGHT = true;

enum class CoreMode {
    AllLogical,
    PhysicalCores,
    PerformanceCores,
    EfficiencyCores
};

inline std::vector<CoreMode> CORE_MODES = {
    CoreMode::PerformanceCores,
    // CoreMode::EfficiencyCores
};

} // namespace BenchmarkConfig

// The signature module uses the same region namespace boundary as GRRT.
namespace SlowLight {

inline const slow_light::regions::RegionDefinition& REGION =
    BenchmarkConfig::REGION;

} // namespace SlowLight
