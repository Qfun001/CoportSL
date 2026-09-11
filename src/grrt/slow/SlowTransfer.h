#pragma once

#include <array>
#include <cstdint>
#include <vector>

#include "src/physics/fluid/FrameCache.h"
#include "src/physics/fluid/GridLocations.h"
#include "src/grrt/RayGeometry.h"
#include "regions/Region.h"

namespace slow_light {

struct TransferStats {
    uint64_t inner_samples = 0;
    uint64_t clamped_samples = 0;
    uint64_t future_samples = 0;
    uint64_t outer_samples = 0;
    double time_offset_begin = 0.0;
    double time_offset_min = 0.0;
    double time_offset_max = 0.0;
};

struct TimeOffsetRange {
    double origin_offset = 0.0;
    double min_offset = 0.0;
    double max_offset = 0.0;
};

TimeOffsetRange time_offset_range(
    const ray::RayGeometry& rays,
    const regions::SampleMask& time_origin_mask,
    const regions::SampleMask& slow_mask);

TransferStats compute_image(
    const ray::RayGeometry& rays,
    const fluid::GridLocations& sampling,
    const fluid::FrameCache& frames,
    double nu,
    const regions::SampleMask& time_origin_mask,
    const regions::SampleMask& slow_mask,
    double time_min,
    double time_max,
    std::vector<std::array<double, 4>>& image);

} // namespace slow_light
