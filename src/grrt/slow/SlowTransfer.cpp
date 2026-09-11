#include <algorithm>
#include <atomic>
#include <cmath>
#include <limits>
#include <stdexcept>

#include "src/grrt/SampleTransfer.h"
#include "src/grrt/StokesProjection.h"
#include "src/physics/transfer/AnalyticalSolution.h"
#include "SlowTransfer.h"
#include "TimeOrigin.h"

namespace slow_light {

TimeOffsetRange time_offset_range(
    const ray::RayGeometry& rays,
    const regions::SampleMask& time_origin_mask,
    const regions::SampleMask& slow_mask) {

    regions::validate_mask(
        time_origin_mask, rays.samples.size(), "Time origin");
    regions::validate_mask(slow_mask, rays.samples.size(), "Slow-light region");
    TimeOffsetRange range;
    range.origin_offset =
        time_origin::reference_offset(rays, time_origin_mask);
    range.min_offset = std::numeric_limits<double>::infinity();
    range.max_offset = -std::numeric_limits<double>::infinity();
    for (size_t i = 0; i < rays.samples.size(); i++) {
        if (!slow_mask[i]) continue;
        const ray::RayPoint& sample = rays.samples[i];
        const double offset =
            time_origin::relative_offset(sample, range.origin_offset);
        range.min_offset = std::min(range.min_offset, offset);
        range.max_offset = std::max(range.max_offset, offset);
    }
    return range;
}

TransferStats compute_image(
    const ray::RayGeometry& rays,
    const fluid::GridLocations& sampling,
    const fluid::FrameCache& frames,
    double nu,
    const regions::SampleMask& time_origin_mask,
    const regions::SampleMask& slow_mask,
    double time_min,
    double time_max,
    std::vector<std::array<double, 4>>& image) {

    if (!std::isfinite(time_min) || !std::isfinite(time_max) ||
        time_min > time_max) {
        throw std::invalid_argument(
            "Slow-light time window endpoints must be finite and ordered.");
    }
    fluid::validate_grid_locations(sampling, rays.samples.size(), "Slow-light transfer");
    const int nray = rays.npix * rays.npix;
    image.assign(static_cast<size_t>(nray), { 0.0, 0.0, 0.0, 0.0 });
    const TimeOffsetRange range = time_offset_range(
        rays, time_origin_mask, slow_mask);
    std::atomic<uint64_t> inner = 0;
    std::atomic<uint64_t> clamped = 0;
    std::atomic<uint64_t> future = 0;
    std::atomic<uint64_t> outer = 0;

#pragma omp parallel for schedule(dynamic, 16)
    for (int pixel = 0; pixel < nray; pixel++) {
        std::array<double, 4> stokes = { 0.0, 0.0, 0.0, 0.0 };
        uint64_t begin = rays.ray_offset[static_cast<size_t>(pixel)];
        uint64_t end = rays.ray_offset[static_cast<size_t>(pixel + 1)];
        fluid::State fluid = {};
        for (uint64_t i = begin; i < end; i++) {
            const ray::RayPoint& sample = rays.samples[static_cast<size_t>(i)];
            const grrt::TransferSample transfer =
                grrt::make_transfer_sample(sample);
            const size_t sample_index = static_cast<size_t>(i);
            const bool fixed = !slow_mask[sample_index];
            double offset = 0.0;
            if (fixed) {
                outer.fetch_add(1, std::memory_order_relaxed);
            }
            else {
                offset =
                    time_origin::relative_offset(sample, range.origin_offset);
                inner.fetch_add(1, std::memory_order_relaxed);
                if (offset > 0.0) future.fetch_add(1, std::memory_order_relaxed);
                if (offset < time_min || offset > time_max) {
                    clamped.fetch_add(1, std::memory_order_relaxed);
                }
                offset = std::clamp(offset, time_min, time_max);
            }
            double time = frames.base_time() + offset;
            if (!frames.sample(
                time,
                fixed,
                transfer.x,
                sampling.locations[sample_index],
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
        image[static_cast<size_t>(pixel)] = screen::project_stokes(rays, pixel, stokes);
    }

    TransferStats stats;
    stats.inner_samples = inner.load();
    stats.clamped_samples = clamped.load();
    stats.future_samples = future.load();
    stats.outer_samples = outer.load();
    stats.time_offset_begin = range.origin_offset;
    stats.time_offset_min = range.min_offset;
    stats.time_offset_max = range.max_offset;
    return stats;
}

} // namespace slow_light
