#include "FastTransfer.h"

#include <array>
#include <vector>

#include "src/grrt/SampleTransfer.h"
#include "src/grrt/StokesProjection.h"
#include "src/physics/fluid/FluidBackend.h"
#include "src/physics/transfer/AnalyticalSolution.h"

namespace fast_light {

namespace {

std::array<double, 4> trace(
    const ray::RayGeometry& cache,
    const fluid::GridLocations& sampling,
    int pixel_index,
    double nu) {

    fluid::validate_grid_locations(sampling, cache.samples.size(), "Fast-light trace");
    if (pixel_index < 0 || pixel_index + 1 >= static_cast<int>(cache.ray_offset.size())) {
        return { 0.0, 0.0, 0.0, 0.0 };
    }

    std::array<double, 4> stokes = { 0.0, 0.0, 0.0, 0.0 };
    uint64_t begin = cache.ray_offset[pixel_index];
    uint64_t end = cache.ray_offset[pixel_index + 1];

    fluid::State fluid;

    for (uint64_t i = begin; i < end; i++) {
        const ray::RayPoint& sample = cache.samples[static_cast<size_t>(i)];
        const grrt::TransferSample transfer =
            grrt::make_transfer_sample(sample);

        if (!fluid::Backend::sample_active(
            transfer.x,
            sampling.locations[static_cast<size_t>(i)],
            fluid,
            transfer.gdown,
            transfer.gup)) {
            continue;
        }

        const TransferCoefficients coefficients =
            grrt::evaluate_transfer(transfer, fluid, nu);
        stokes = AnalyticalSolution(
            coefficients.J_chi,
            coefficients.M_chi,
            stokes,
            transfer.dl);
    }

    return screen::project_stokes(cache, pixel_index, stokes);
}

} // namespace

void compute_image(
    const ray::RayGeometry& rays,
    const fluid::GridLocations& sampling,
    double nu,
    std::vector<std::array<double, 4>>& image) {

    fluid::validate_grid_locations(sampling, rays.samples.size(), "Fast-light transfer");
    int nray = rays.npix * rays.npix;
    image.assign(static_cast<size_t>(nray), { 0.0, 0.0, 0.0, 0.0 });

#pragma omp parallel for schedule(dynamic, 16)
    for (int pixel = 0; pixel < nray; pixel++) {
        image[static_cast<size_t>(pixel)] = trace(rays, sampling, pixel, nu);
    }
}

} // namespace fast_light
