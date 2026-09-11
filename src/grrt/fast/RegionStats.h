#pragma once

#include <cstdint>
#include <vector>

#include "src/physics/fluid/GridLocations.h"
#include "src/grrt/RayGeometry.h"
#include "src/grrt/slow/regions/Region.h"

namespace fast_light {

struct RegionCoefficients {
    double jI_abs = 0.0;
    double jP_abs = 0.0;
    double aI_abs = 0.0;
    double aP_abs = 0.0;
    double rhoV_abs = 0.0;
    double rhoC_abs = 0.0;
    double rhoV_signed = 0.0;
    uint64_t samples = 0;
};

std::vector<RegionCoefficients> regional_coefficient_stats(
    const ray::RayGeometry& cache,
    const fluid::GridLocations& sampling,
    double nu,
    const slow_light::regions::RegionPartition& partition);

} // namespace fast_light
