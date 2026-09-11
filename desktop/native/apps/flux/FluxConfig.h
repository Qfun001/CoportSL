#pragma once

#include <array>
#include <cmath>
#include <filesystem>
#include <numbers>
#include <vector>

// User configuration for the Flux project. The parameters here are only used for fast light average luminous flux estimation, and the Stokes image file will not be written.
namespace Config {

inline std::filesystem::path DATA = "D:/CoportSL-data/output";
inline std::filesystem::path GRID = "D:/CoportSL-data/grid_mks.in";

inline int NT0 = 1000;
inline int NT1 = 2400;
inline int DNT = 10;
inline int NPIX = 256;
inline double FOV = std::numbers::pi / 64.0;
inline std::vector<double> NU = {230e9};

inline double TARGET_FLUX_JY = 0.66;
inline double DISTANCE_PC = 16.9e6;

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
constexpr int METRIC = MKSBHAC; // Must be consistent with input GRMHD data.
inline double SPIN = 0.9375;
inline double HS = 0.0;

constexpr int BHAC = 1;
constexpr int FLUID_BACKEND = BHAC; // The fluid backend used by the current data, manually specified by the user.

constexpr int THERMAL = 0;
constexpr int POWER_LAW = 1;
constexpr int BEAM = 2;
constexpr int LOSS_CONE = 3;
inline int ELECTRON = POWER_LAW;

inline double MBH = 6.5e9;
inline double MDOT = 2.46e-4;
inline double MDOT_SIM = 50.0;

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

inline double R_SOURCE = 200.0;

} // namespace Config
