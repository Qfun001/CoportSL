#pragma once

#include "State.h"

namespace fluid {

// Inputs are all in GRMHD code units, magnetic_norm is $b^\mu b_\mu$.
void set_radiative_scalars(
    State& state,
    double rho,
    double internal_energy,
    double adiabatic_index,
    double magnetic_norm);

} // namespace fluid
