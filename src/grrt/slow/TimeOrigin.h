#pragma once

#include <cstddef>
#include <string_view>
#include <vector>

#include "src/grrt/RayGeometry.h"
#include "regions/Region.h"

namespace slow_light::time_origin {

// The earliest time delay of light entering the spherical area near the black hole is used as the unified time base.
inline constexpr double RADIUS = 20.0; // Unit rg.
inline constexpr std::string_view NAME = "inner_sphere_r20";

using Position = regions::Position;
using PositionAt = regions::PositionAt;

regions::SampleMask build_mask(
    size_t sample_count,
    const PositionAt& position_at);

double reference_offset(
    const ray::RayGeometry& rays,
    const regions::SampleMask& mask);

double relative_offset(
    const ray::RayPoint& sample,
    double reference) noexcept;

template <typename Sample>
regions::SampleMask build_mask(const std::vector<Sample>& samples) {
    return build_mask(
        samples.size(),
        [&samples](size_t index) {
            const Sample& sample = samples[index];
            return Position{0.0, sample.x[0], sample.x[1], sample.x[2]};
        });
}

} // namespace slow_light::time_origin
