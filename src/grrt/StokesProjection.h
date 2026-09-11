#pragma once

#include <array>

#include "RayGeometry.h"

namespace screen {

std::array<double, 4> project_stokes(
    const ray::RayGeometry& rays,
    int pixel,
    const std::array<double, 4>& stokes);

} // namespace screen
