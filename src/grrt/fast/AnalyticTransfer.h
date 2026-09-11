#pragma once

#include <array>
#include <vector>

#include "src/grrt/RayGeometry.h"
#include "src/physics/medium/Medium.h"

namespace fast_light {

// Resolving media does not require fluid mesh positioning and directly requests transfer coefficients along cached rays.
void compute_analytic_image(
    const ray::RayGeometry& rays,
    const medium::Sampler& sampler,
    double observer_frequency,
    double emission_time,
    std::vector<std::array<double, 4>>& image);

} // namespace fast_light
