#include "Scaling.h"

#include <cmath>

#include "src/physics/Constants.h"
#include "src/physics/Model.h"

namespace fluid {

void set_radiative_scalars(
    State& state,
    double rho,
    double internal_energy,
    double adiabatic_index,
    double magnetic_norm) {

    // Preserving the two-level numerical lower bound in the BHAC baseline avoids changes in old results due to extraction of common functions.
    const double b2 = std::abs(magnetic_norm) + 1e-6;
    state.n_e = rho * Constants::Ne_unit + 1e-6;
    state.B = std::sqrt(b2) * Constants::B_unit;
    state.beta = internal_energy * (adiabatic_index - 1.0) /
        (0.5 * (b2 + 1e-6));
    state.sigma = b2 / rho;
    state.sigma_min = 1.0;

    const double beta_ratio2 = std::pow(state.beta / Config::BETA0, 2.0);
    const double temperature_ratio =
        ModelConstants::R_HIGH * beta_ratio2 / (1.0 + beta_ratio2) +
        ModelConstants::R_LOW / (1.0 + beta_ratio2);
    state.theta_e = internal_energy * (adiabatic_index - 1.0) / rho *
        Constants::MPoME / (temperature_ratio + 1.0);
}

} // namespace fluid
