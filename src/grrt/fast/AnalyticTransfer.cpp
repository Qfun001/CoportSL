#include "AnalyticTransfer.h"

#include <atomic>
#include <stdexcept>

#include "src/grrt/SampleTransfer.h"
#include "src/grrt/StokesProjection.h"
#include "src/physics/medium/Coefficients.h"
#include "src/physics/transfer/AnalyticalSolution.h"

namespace fast_light {

void compute_analytic_image(
    const ray::RayGeometry& rays,
    const medium::Sampler& sampler,
    double observer_frequency,
    double emission_time,
    std::vector<std::array<double, 4>>& image) {

    const int pixel_count = rays.npix * rays.npix;
    if (rays.ray_offset.size() != static_cast<size_t>(pixel_count + 1)) {
        throw std::invalid_argument(
            "Analytic transfer ray offsets do not match the image size.");
    }
    image.assign(
        static_cast<size_t>(pixel_count), {0.0, 0.0, 0.0, 0.0});
    std::atomic<bool> invalid_coefficients = false;

#pragma omp parallel for schedule(dynamic, 16)
    for (int pixel = 0; pixel < pixel_count; pixel++) {
        std::array<double, 4> stokes = {};
        const uint64_t begin = rays.ray_offset[static_cast<size_t>(pixel)];
        const uint64_t end = rays.ray_offset[static_cast<size_t>(pixel + 1)];
        for (uint64_t offset = begin; offset < end; offset++) {
            const size_t index = static_cast<size_t>(offset);
            const grrt::TransferSample transfer =
                grrt::make_transfer_sample(rays.samples[index]);
            TransferCoefficients coefficients = {};
            const medium::Query query{
                transfer, index, observer_frequency, emission_time};
            if (!sampler.sample(query, coefficients)) continue;
            if (!medium::finite(coefficients)) {
                invalid_coefficients.store(true, std::memory_order_relaxed);
                continue;
            }
            stokes = AnalyticalSolution(
                coefficients.J_chi,
                coefficients.M_chi,
                stokes,
                transfer.dl);
        }
        image[static_cast<size_t>(pixel)] =
            screen::project_stokes(rays, pixel, stokes);
    }
    if (invalid_coefficients.load(std::memory_order_relaxed)) {
        throw std::runtime_error(
            "Analytic medium returned non-finite transfer coefficients.");
    }
}

} // namespace fast_light
