#include "SampleTransfer.h"

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

} // namespace grrt
