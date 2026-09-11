#pragma once

#include <cmath>
#include <numbers>

#include "apps/RunConfig.h"

namespace Constants {

inline constexpr double ELECTRON_CHARGE = 4.8032044e-10; // esu
inline constexpr double ELECTRON_MASS = 9.1093837e-28; // g
inline constexpr double SPEED_OF_LIGHT = 2.99792458e10; // cm/s
inline constexpr double PLANCK_CONSTANT = 6.62607015e-27; // erg s
inline constexpr double BOLTZMANN_CONSTANT = 1.380649e-16; // erg/K
inline constexpr double MEC2 =
    ELECTRON_MASS * SPEED_OF_LIGHT * SPEED_OF_LIGHT; // erg

inline constexpr double PROTON_MASS = 1.6726219e-24;
inline constexpr double MPCL2 = 0.0015033;
inline constexpr double GGRAV = 6.674e-8;
inline constexpr double MSUN = 1.989e33;
inline constexpr double KPCTOCM = 3.086e21;
inline constexpr double MPoME = MPCL2 / MEC2;

inline double MBH;
inline double rg;
inline double tg;
inline double V3g;
inline double V4g;
inline double L_unit;
inline double T_unit;
inline double dotM;
inline double dotMBH;
inline double ratio;
inline double RHO_unit;
inline double U_unit;
inline double Ne_unit;
inline double B_unit;

inline void refresh_units() {
    MBH = Config::MBH * MSUN;
    rg = GGRAV * MBH / SPEED_OF_LIGHT / SPEED_OF_LIGHT;
    tg = rg / SPEED_OF_LIGHT;
    V3g = rg * rg * rg;
    V4g = V3g * tg;
    L_unit = GGRAV * MBH / (SPEED_OF_LIGHT * SPEED_OF_LIGHT);
    T_unit = L_unit / SPEED_OF_LIGHT;
    dotM = Config::MDOT_SIM * (MBH / T_unit);
    dotMBH = Config::MDOT * MSUN / (365.0 * 24.0 * 3600.0);
    ratio = dotMBH / dotM;
    RHO_unit = MBH / ((T_unit * T_unit) * L_unit) * ratio;
    U_unit = RHO_unit;
    Ne_unit = RHO_unit /
        ((PROTON_MASS + ELECTRON_MASS) * SPEED_OF_LIGHT * SPEED_OF_LIGHT);
    B_unit = std::sqrt(4.0 * std::numbers::pi * RHO_unit);
}

inline const bool units_initialized = [] {
    refresh_units();
    return true;
}();

} // namespace Constants
