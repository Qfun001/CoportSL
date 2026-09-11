#include "src/grrt/SampleTransfer.h"

#include "src/physics/spacetime/Metric.h"

namespace grrt {

TransferSample make_transfer_sample(const ray::RayPoint& sample) {
    TransferSample result;
    result.x = ray::position(sample);
    result.k = ray::wave_vector(sample);
    result.f = ray::polar_vector(sample);
    result.gdown = MetricDown(result.x);
    result.gup = MetricUp(result.x);
    result.dl = static_cast<double>(sample.dl);
    return result;
}

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
