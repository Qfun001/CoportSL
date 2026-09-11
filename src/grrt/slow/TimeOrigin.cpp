#include "TimeOrigin.h"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

#include "src/physics/spacetime/Metric.h"

namespace slow_light::time_origin {

regions::SampleMask build_mask(
    size_t sample_count,
    const PositionAt& position_at) {

    if (!position_at) {
        throw std::invalid_argument("Time-origin position extractor is missing.");
    }

    regions::SampleMask mask;
    mask.name = NAME;
    mask.selected.resize(sample_count);
    for (size_t i = 0; i < sample_count; i++) {
        mask.selected[i] = static_cast<uint8_t>(
            get_radial_radius(position_at(i)) < RADIUS);
    }
    regions::validate_mask(mask, sample_count, "Time origin");
    return mask;
}

double reference_offset(
    const ray::RayGeometry& rays,
    const regions::SampleMask& mask) {

    regions::validate_mask(mask, rays.samples.size(), "Time origin");
    double result = std::numeric_limits<double>::infinity();
    for (size_t index = 0; index < rays.samples.size(); index++) {
        if (!mask[index]) continue;
        result = std::min(
            result,
            static_cast<double>(rays.samples[index].dt));
    }
    if (!std::isfinite(result)) {
        throw std::runtime_error("Time origin contains no ray samples.");
    }
    return result;
}

double relative_offset(
    const ray::RayPoint& sample,
    double reference) noexcept {

    return reference - static_cast<double>(sample.dt);
}

} // namespace slow_light::time_origin
