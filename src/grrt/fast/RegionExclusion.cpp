#include "RegionExclusion.h"

#include <stdexcept>
#include <utility>

#include "src/grrt/SampleTransfer.h"
#include "src/grrt/StokesProjection.h"
#include "src/physics/fluid/FluidBackend.h"
#include "src/physics/transfer/AnalyticalSolution.h"

namespace fast_light {

void compute_region_exclusion(
    const ray::RayGeometry& rays,
    const fluid::GridLocations& sampling,
    double nu,
    const slow_light::regions::RegionPartition& partition,
    std::span<const slow_light::regions::RegionSelection> selections,
    RegionExclusionResult& result) {

    fluid::validate_grid_locations(
        sampling, rays.samples.size(), "RegionError");
    slow_light::regions::validate_partition(
        partition, rays.samples.size(), "RegionError");
    const std::vector<slow_light::regions::SampleMask> masks =
        slow_light::regions::select_region_sets(partition, selections);

    const int pixel_count = rays.npix * rays.npix;
    result.full.assign(
        static_cast<size_t>(pixel_count), {0.0, 0.0, 0.0, 0.0});
    result.selections.clear();
    for (const auto& selection : selections) {
        RegionApproximation approximation;
        approximation.name = selection.name;
        approximation.emission.assign(
            static_cast<size_t>(pixel_count), {0.0, 0.0, 0.0, 0.0});
        approximation.all_coefficients.assign(
            static_cast<size_t>(pixel_count), {0.0, 0.0, 0.0, 0.0});
        result.selections.push_back(std::move(approximation));
    }

#pragma omp parallel for schedule(dynamic, 1)
    for (int pixel = 0; pixel < pixel_count; pixel++) {
        std::array<double, 4> full = {};
        std::vector<std::array<double, 4>> emission(selections.size());
        std::vector<std::array<double, 4>> all(selections.size());
        fluid::State state;
        const uint64_t begin = rays.ray_offset[static_cast<size_t>(pixel)];
        const uint64_t end = rays.ray_offset[static_cast<size_t>(pixel + 1)];
        for (uint64_t i = begin; i < end; i++) {
            const size_t sample_index = static_cast<size_t>(i);
            const ray::RayPoint& sample = rays.samples[sample_index];
            const grrt::TransferSample transfer =
                grrt::make_transfer_sample(sample);
            if (!fluid::Backend::sample_active(
                transfer.x,
                sampling.locations[sample_index],
                state,
                transfer.gdown,
                transfer.gup)) {
                continue;
            }
            const TransferCoefficients coefficients =
                grrt::evaluate_transfer(transfer, state, nu);
            auto propagation = coefficients;
            propagation.J_chi = {0.0, 0.0, 0.0, 0.0};
            const double dl = transfer.dl;
            full = AnalyticalSolution(
                coefficients.J_chi, coefficients.M_chi, full, dl);
            for (size_t selection = 0; selection < masks.size(); selection++) {
                if (masks[selection][sample_index]) {
                    emission[selection] = AnalyticalSolution(
                        coefficients.J_chi,
                        coefficients.M_chi,
                        emission[selection],
                        dl);
                    all[selection] = AnalyticalSolution(
                        coefficients.J_chi,
                        coefficients.M_chi,
                        all[selection],
                        dl);
                }
                else {
                    emission[selection] = AnalyticalSolution(
                        propagation.J_chi,
                        propagation.M_chi,
                        emission[selection],
                        dl);
                }
            }
        }
        result.full[static_cast<size_t>(pixel)] =
            screen::project_stokes(rays, pixel, full);
        for (size_t selection = 0; selection < masks.size(); selection++) {
            result.selections[selection].emission[static_cast<size_t>(pixel)] =
                screen::project_stokes(rays, pixel, emission[selection]);
            result.selections[selection]
                .all_coefficients[static_cast<size_t>(pixel)] =
                screen::project_stokes(rays, pixel, all[selection]);
        }
    }
}

} // namespace fast_light
