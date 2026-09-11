#pragma once

#include <cmath>

#include "apps/RunConfig.h"

// Model name and configuration derivation used by the shared physics module.
inline namespace ModelConstants {

inline double& blackhole_spin = Config::SPIN;
inline double& hs = Config::HS;

inline double& R_source = Config::R_SOURCE;

inline double horizon_radius() {
    return 1.0 + std::sqrt(1.0 - blackhole_spin * blackhole_spin);
}

inline constexpr int CAR = Config::CAR;
inline constexpr int BL = Config::BL;
inline constexpr int MBL = Config::MBL;
inline constexpr int KS = Config::KS;
inline constexpr int MKS = Config::MKS;
inline constexpr int MKSHARM = Config::MKSHARM;
inline constexpr int MKSBHAC = Config::MKSBHAC;
inline constexpr int MKSN = Config::MKSN;
inline constexpr int CKS = Config::CKS;
inline constexpr int metric = Config::METRIC;
inline constexpr int logscale =
    (metric == MBL || metric == MKS || metric == MKSHARM ||
     metric == MKSBHAC || metric == MKSN) ? 1 : 0;

inline constexpr int ThermalModel = Config::THERMAL;
inline constexpr int PowerLawModel = Config::POWER_LAW;
inline constexpr int BeamModel = Config::BEAM;
inline constexpr int LossConeModel = Config::LOSS_CONE;
inline int& ElectronModel = Config::ELECTRON;

inline const char* electron_model_name() {
    if (ElectronModel == PowerLawModel) return "powerlaw";
    if (ElectronModel == BeamModel) return "beam";
    if (ElectronModel == LossConeModel) return "losscone";
    return "thermal";
}

inline double& R_LOW = Config::R_LOW;
inline double& R_HIGH = Config::R_HIGH;
inline double& SIGMA_MAX = Config::SIGMA_MAX;

} // namespace ModelConstants
