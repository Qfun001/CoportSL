#include "Slab.h"

#include <cmath>
#include <stdexcept>

namespace medium::analytic {

Slab::Slab(
    int axis,
    double minimum,
    double maximum,
    const NamedCoefficients& coefficients) :
    axis_(axis),
    minimum_(minimum),
    maximum_(maximum),
    coefficients_(make_transfer_coefficients(coefficients)) {

    if (axis < 1 || axis > 3) {
        throw std::invalid_argument("Analytic slab axis must be 1, 2, or 3.");
    }
    if (!std::isfinite(minimum) || !std::isfinite(maximum) ||
        minimum > maximum) {
        throw std::invalid_argument(
            "Analytic slab bounds must be finite and ordered.");
    }
}

bool Slab::sample(
    const Query& query,
    TransferCoefficients& result) const {

    const double coordinate =
        query.sample.x[static_cast<size_t>(axis_)];
    if (coordinate < minimum_ || coordinate > maximum_) return false;
    result = coefficients_;
    return true;
}

} // namespace medium::analytic
