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

inline constexpr double MBH = Config::MBH * MSUN;
inline constexpr double rg = GGRAV * MBH / SPEED_OF_LIGHT / SPEED_OF_LIGHT;
inline constexpr double tg = rg / SPEED_OF_LIGHT;
inline constexpr double V3g = rg * rg * rg;
inline constexpr double V4g = V3g * tg;

inline constexpr double L_unit = GGRAV * MBH / (SPEED_OF_LIGHT * SPEED_OF_LIGHT);
inline constexpr double T_unit = L_unit / SPEED_OF_LIGHT;
inline constexpr double dotM =
    Config::MDOT_SIM * (MBH / T_unit);
inline constexpr double dotMBH =
    Config::MDOT * MSUN / (365.0 * 24.0 * 3600.0);
inline constexpr double ratio = dotMBH / dotM;

inline constexpr double RHO_unit =
    MBH / ((T_unit * T_unit) * L_unit) * ratio;
inline constexpr double U_unit = RHO_unit;
inline constexpr double Ne_unit =
    RHO_unit /
    ((PROTON_MASS + ELECTRON_MASS) * SPEED_OF_LIGHT * SPEED_OF_LIGHT);
inline const double B_unit = std::sqrt(4.0 * std::numbers::pi * RHO_unit);

} // namespace Constants
