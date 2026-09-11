#pragma once

#include <array>
#include <vector>

#include "src/physics/fluid/GridLocations.h"
#include "src/grrt/RayGeometry.h"

namespace fast_light {

// Solve for polarized radiation transfer along cached rays, returning I/Q/U/V for each pixel.
void compute_image(
    const ray::RayGeometry& rays,
    const fluid::GridLocations& sampling,
    double nu,
    std::vector<std::array<double, 4>>& image);

} // namespace fast_light
