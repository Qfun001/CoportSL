#include "Coefficients.h"

#include <cmath>
#include <stdexcept>

namespace medium {

TransferCoefficients make_transfer_coefficients(
    const NamedCoefficients& values) {

    for (double value : values.j) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument("Emission coefficients must be finite.");
        }
    }
    for (double value : values.alpha) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument("Absorption coefficients must be finite.");
        }
    }
    for (double value : values.rho) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument("Faraday coefficients must be finite.");
        }
    }

    const auto& a = values.alpha;
    const double rho_q = values.rho[0];
    const double rho_u = values.rho[1];
    const double rho_v = values.rho[2];
    TransferCoefficients result;
    result.J_chi = values.j;
    result.M_chi = {{
        {a[0], a[1], a[2], a[3]},
        {a[1], a[0], rho_v, -rho_u},
        {a[2], -rho_v, a[0], rho_q},
        {a[3], rho_u, -rho_q, a[0]}
    }};
    return result;
}

bool finite(const TransferCoefficients& values) {
    for (double value : values.J_chi) {
        if (!std::isfinite(value)) return false;
    }
    for (const auto& row : values.M_chi) {
        for (double value : row) {
            if (!std::isfinite(value)) return false;
        }
    }
    return true;
}

} // namespace medium
