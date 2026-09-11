#include "SampleTransfer.h"

namespace grrt {

TransferCoefficients evaluate_transfer(
    const TransferSample& sample,
    fluid::State& state,
    double nu) {

    const Radiation radiation = PlasmaRadiation(
        sample.x,
        sample.k,
        sample.f,
        nu,
        &state);
    return transfer_coefficients(radiation);
}

} // namespace grrt
