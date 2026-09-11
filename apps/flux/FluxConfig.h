#pragma once

#include <array>
#include <cmath>
#include <filesystem>
#include <numbers>

// User configuration for the Flux project. The parameters here are only used for fast light average luminous flux estimation, and the Stokes image file will not be written.
namespace Config {

inline const std::filesystem::path DATA = "D:/CoportSL-data/output"; // Absolute snapshot directory of the active fluid backend.
inline const std::filesystem::path GRID = "D:/CoportSL-data/grid_mks.in"; // Static BHAC grid file.

constexpr int NT0 = 1000; // The starting frame used for averaging luminous flux, including this frame.
constexpr int NT1 = 2400; // End frame for average luminous flux, including this frame.
constexpr int DNT = 10; // Frame sampling step size.
constexpr int NPIX = 256; // Flux may use a lower resolution than production imaging to accelerate a scan.
constexpr double FOV = std::numbers::pi / 64.0; // Field of view, unit rad.
constexpr std::array NU = {230e9}; // Observation frequency, unit Hz.

constexpr double TARGET_FLUX_JY = 0.66; // Target average luminous flux density, unit Jy.
constexpr double DISTANCE_PC = 16.9e6; // Source-to-viewer distance, in pc.

constexpr double OBS_T = 0.0; // Viewer coordinate time.
constexpr double OBS_R = 500.0; // Viewer radius, unit rg.
constexpr double OBS_TH = 163.0 * std::numbers::pi / 180.0; // Observer polar angle, unit rad.
constexpr double OBS_PH = 0.0001; // Viewer azimuth, unit rad.
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
constexpr int METRIC = MKSBHAC; // Must be consistent with input GRMHD data.
constexpr double SPIN = 0.9375;
inline double HS = 0.0; // Covered by hslope in the active BHAC mesh.

constexpr int BHAC = 1;
constexpr int FLUID_BACKEND = BHAC; // The fluid backend used by the current data, manually specified by the user.

constexpr int THERMAL = 0;
constexpr int POWER_LAW = 1;
constexpr int BEAM = 2;
constexpr int LOSS_CONE = 3;
constexpr int ELECTRON = POWER_LAW; // Can be changed to POWER_LAW, BEAM, or LOSS_CONE.

constexpr double MBH = 6.5e9; // Black hole mass, unit mass of the sun.
constexpr double MDOT = 2.46e-4; // The physical accretion rate to be adjusted, per solar mass per year.
constexpr double MDOT_SIM = 50.0; // Simulated accretion rate normalized in MBH/T_unit.

constexpr double R_LOW = 10.0;
constexpr double R_HIGH = 100.0;
constexpr double BETA0 = 1.0;
constexpr double SIGMA_MAX = 20.0;
constexpr double THETAE_EMIT = 0.10;
constexpr double NE_EMIT = 1.0e2;
constexpr double POL_LIMIT = 0.95;

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

static_assert(NT0 <= NT1 && DNT > 0);
static_assert(NPIX > 0);
static_assert(TARGET_FLUX_JY > 0.0);

} // namespace Config
