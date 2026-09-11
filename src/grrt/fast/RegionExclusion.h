#pragma once

#include <array>
#include <span>
#include <string>
#include <vector>

#include "src/grrt/RayGeometry.h"
#include "src/grrt/slow/regions/Region.h"
#include "src/physics/fluid/GridLocations.h"

namespace fast_light {

struct RegionApproximation {
    std::string name;
    std::vector<std::array<double, 4>> emission;
    std::vector<std::array<double, 4>> all_coefficients;
};

struct RegionExclusionResult {
    std::vector<std::array<double, 4>> full;
    std::vector<RegionApproximation> selections;
};

void compute_region_exclusion(
    const ray::RayGeometry& rays,
    const fluid::GridLocations& sampling,
    double nu,
    const slow_light::regions::RegionPartition& partition,
    std::span<const slow_light::regions::RegionSelection> selections,
    RegionExclusionResult& result);

} // namespace fast_light
