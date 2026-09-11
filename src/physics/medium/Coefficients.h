#pragma once

#include <array>

#include "src/physics/transfer/PlasmaRadiation.h"

namespace medium {

// 11 coefficients in a parallel-shifted Stokes basis normalized by the affine parameters of the integrator.
struct NamedCoefficients {
    std::array<double, 4> j = {};
    std::array<double, 4> alpha = {};
    std::array<double, 3> rho = {}; // rho_Q, rho_U, and rho_V.
};

TransferCoefficients make_transfer_coefficients(
    const NamedCoefficients& values);

bool finite(const TransferCoefficients& values);

} // namespace medium
