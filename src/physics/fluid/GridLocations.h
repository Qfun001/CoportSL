#pragma once

#include <cstddef>
#include <sstream>
#include <stdexcept>
#include <vector>

#include "FluidBackend.h"
#include "src/grrt/RayGeometry.h"

namespace fluid {

// Save the positioning results of each light sampling point in the active fluid grid.
struct GridLocations {
    std::vector<Backend::Location> locations;
};

GridLocations locate_ray_samples(const ray::RayGeometry& rays);

inline void validate_grid_locations(
    const GridLocations& grid,
    size_t sample_count,
    const char* owner) {

    if (grid.locations.size() == sample_count) return;
    std::ostringstream message;
    message << owner << " grid location count " << grid.locations.size()
        << " does not match ray sample count " << sample_count << ".";
    throw std::invalid_argument(message.str());
}

} // namespace fluid
