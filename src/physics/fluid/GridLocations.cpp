#include "GridLocations.h"

#include <stdexcept>

namespace fluid {

GridLocations locate_ray_samples(const ray::RayGeometry& rays) {
    GridLocations grid;
    grid.locations.resize(rays.samples.size());
    for (size_t pixel = 0; pixel + 1 < rays.ray_offset.size(); pixel++) {
        uint64_t hint = 0;
        const uint64_t begin = rays.ray_offset[pixel];
        const uint64_t end = rays.ray_offset[pixel + 1];
        for (uint64_t i = begin; i < end; i++) {
            const ray::RayPoint& sample = rays.samples[static_cast<size_t>(i)];
            const Position x = {
                0.0,
                static_cast<double>(sample.x[0]),
                static_cast<double>(sample.x[1]),
                static_cast<double>(sample.x[2])
            };
            if (!Backend::locate(
                x, hint, grid.locations[static_cast<size_t>(i)])) {
                throw std::runtime_error(
                    "A cached ray sample is outside the active fluid grid.");
            }
        }
    }
    return grid;
}

} // namespace fluid
