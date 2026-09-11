#include "RegionStats.h"

#include <array>
#include <cmath>
#include <stdexcept>

#include "src/grrt/SampleTransfer.h"
#include "src/physics/fluid/FluidBackend.h"
#include "src/physics/transfer/TransferSupport.h"

namespace fast_light {

std::vector<RegionCoefficients> regional_coefficient_stats(
    const ray::RayGeometry& cache,
    const fluid::GridLocations& sampling,
    double nu,
    const slow_light::regions::RegionPartition& partition) {

    slow_light::regions::validate_partition(
        partition, cache.samples.size(), "Coefficient statistics");
    fluid::validate_grid_locations(
        sampling, cache.samples.size(), "Coefficient statistics");

    std::vector<RegionCoefficients> total(partition.region_count());
    const int nray = cache.npix * cache.npix;

#pragma omp parallel
    {
        std::vector<RegionCoefficients> local(partition.region_count());
        fluid::State fluid = {};
#pragma omp for schedule(dynamic, 1)
        for (int pixel = 0; pixel < nray; pixel++) {
            const uint64_t begin = cache.ray_offset[static_cast<size_t>(pixel)];
            const uint64_t end = cache.ray_offset[static_cast<size_t>(pixel + 1)];
            for (uint64_t i = begin; i < end; i++) {
                const size_t index = static_cast<size_t>(i);
                const ray::RayPoint& sample = cache.samples[index];
                const grrt::TransferSample transfer =
                    grrt::make_transfer_sample(sample);
                if (!fluid::Backend::sample_active(
                    transfer.x,
                    sampling.locations[index],
                    fluid,
                    transfer.gdown,
                    transfer.gup)) continue;

                const TransferCoefficients c =
                    grrt::evaluate_transfer(transfer, fluid, nu);
                const CoefficientSupport support = coefficient_support(c);
                RegionCoefficients& out = local[partition.sample_regions[index]];
                const double dl = transfer.dl;
                out.jI_abs += support.jI * dl;
                out.jP_abs += support.jP * dl;
                out.aI_abs += support.aI * dl;
                out.aP_abs += support.aP * dl;
                out.rhoV_abs += support.rhoV * dl;
                out.rhoV_signed += c.M_chi[1][2] * dl;
                out.rhoC_abs += support.rhoC * dl;
                out.samples++;
            }
        }
#pragma omp critical
        {
            for (size_t region = 0; region < total.size(); region++) {
                total[region].jI_abs += local[region].jI_abs;
                total[region].jP_abs += local[region].jP_abs;
                total[region].aI_abs += local[region].aI_abs;
                total[region].aP_abs += local[region].aP_abs;
                total[region].rhoV_abs += local[region].rhoV_abs;
                total[region].rhoC_abs += local[region].rhoC_abs;
                total[region].rhoV_signed += local[region].rhoV_signed;
                total[region].samples += local[region].samples;
            }
        }
    }
    return total;
}

} // namespace fast_light
