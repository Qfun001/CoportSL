#include "RegionSelector.h"

#include <algorithm>
#include <cmath>
#include <limits>
#include <map>
#include <numeric>
#include <sstream>
#include <stdexcept>

namespace slow_light::regions {

CoefficientValues CoefficientTolerances::values() const noexcept {
    return { jI, jP, aI, aP, rhoV, rhoC };
}

const char* coefficient_name(SupportCoefficient coefficient) noexcept {
    switch (coefficient) {
    case SupportCoefficient::jI: return "jI";
    case SupportCoefficient::jP: return "jP";
    case SupportCoefficient::aI: return "aI";
    case SupportCoefficient::aP: return "aP";
    case SupportCoefficient::rhoV: return "rhoV";
    case SupportCoefficient::rhoC: return "rhoC";
    case SupportCoefficient::count: break;
    }
    return "unknown";
}

RegionSelectionResult select_by_contribution(
    const RegionPartition& partition,
    const std::vector<ContributionSnapshot>& snapshots,
    const CoefficientTolerances& tolerances,
    double normalization_tolerance) {

    validate_partition(partition, partition.sample_count(), "Region selector");
    if (snapshots.empty()) {
        throw std::invalid_argument("Region selector requires at least one snapshot.");
    }
    if (!(normalization_tolerance >= 0.0) ||
        !std::isfinite(normalization_tolerance)) {
        throw std::invalid_argument(
            "Region selector normalization tolerance must be finite and non-negative.");
    }

    const CoefficientValues epsilon = tolerances.values();
    for (size_t coefficient = 0; coefficient < epsilon.size(); coefficient++) {
        if (!(epsilon[coefficient] > 0.0 && epsilon[coefficient] < 1.0) ||
            !std::isfinite(epsilon[coefficient])) {
            throw std::invalid_argument(
                std::string("Invalid region tolerance for ") +
                coefficient_name(static_cast<SupportCoefficient>(coefficient)) + ".");
        }
    }

    struct FrequencyMean {
        double nu = 0.0;
        std::vector<CoefficientValues> sums;
        std::array<uint64_t, SUPPORT_COEFFICIENT_COUNT> counts = {};
    };

    std::map<size_t, FrequencyMean> means;
    RegionSelectionResult result;
    result.selection.name = "suggest";
    result.minimum_mean_coverage.fill(1.0);
    result.selected_by.resize(partition.region_count());
    result.priority.resize(partition.region_count());
    for (size_t region = 0; region < partition.region_count(); region++) {
        result.priority[region].region = static_cast<RegionId>(region);
        result.priority[region].score = -1.0;
    }
    for (const ContributionSnapshot& snapshot : snapshots) {
        if (!std::isfinite(snapshot.time)) {
            throw std::invalid_argument("Region selector snapshot time must be finite.");
        }
        if (!std::isfinite(snapshot.nu)) {
            throw std::invalid_argument(
                "Region selector snapshot frequency must be finite.");
        }
        if (snapshot.regions.size() != partition.region_count()) {
            throw std::invalid_argument(
                "Region selector frame=" + std::to_string(snapshot.frame) +
                " region_count=" + std::to_string(snapshot.regions.size()) +
                ", expected=" + std::to_string(partition.region_count()) + ".");
        }

        auto [mean_iterator, inserted] = means.try_emplace(snapshot.nu_index);
        FrequencyMean& mean = mean_iterator->second;
        if (inserted) {
            mean.nu = snapshot.nu;
            mean.sums.resize(partition.region_count());
        }
        else if (mean.nu != snapshot.nu) {
            throw std::invalid_argument(
                "Region selector received inconsistent frequencies for one nu_index.");
        }

        for (size_t coefficient = 0; coefficient < SUPPORT_COEFFICIENT_COUNT;
            coefficient++) {
            if (snapshot.active[coefficient] > 1) {
                throw std::invalid_argument(
                    "Region selector active flags must be boolean.");
            }
            double total = 0.0;
            for (size_t region = 0; region < snapshot.regions.size(); region++) {
                const CoefficientValues& values = snapshot.regions[region];
                const double value = values[coefficient];
                if (!(value >= 0.0) || !std::isfinite(value)) {
                    throw std::invalid_argument(
                        "Region selector received invalid contribution for frame=" +
                        std::to_string(snapshot.frame) + ".");
                }
                total += value;
            }
            if (snapshot.active[coefficient] == 0) continue;
            if (std::abs(total - 1.0) > normalization_tolerance) {
                throw std::invalid_argument(
                    "Region contributions for frame=" +
                    std::to_string(snapshot.frame) + " coefficient=" +
                    coefficient_name(static_cast<SupportCoefficient>(coefficient)) +
                    " sum=" + std::to_string(total) + ", expected=1.");
            }
            for (size_t region = 0; region < snapshot.regions.size(); region++) {
                mean.sums[region][coefficient] +=
                    snapshot.regions[region][coefficient];
            }
            mean.counts[coefficient]++;
            result.active_snapshots[coefficient]++;
        }
    }

    const bool any_active = std::any_of(
        result.active_snapshots.begin(), result.active_snapshots.end(),
        [](uint64_t count) { return count != 0; });
    if (!any_active) {
        throw std::runtime_error(
            "Region selector found no non-zero coefficient support.");
    }

    std::vector<uint8_t> selected(partition.region_count(), 0);
    for (auto& [nu_index, mean] : means) {
        for (size_t coefficient = 0; coefficient < SUPPORT_COEFFICIENT_COUNT;
            coefficient++) {
            if (mean.counts[coefficient] == 0) continue;
            const double denominator = static_cast<double>(mean.counts[coefficient]);
            for (size_t region = 0; region < partition.region_count(); region++) {
                mean.sums[region][coefficient] /= denominator;
                const double contribution = mean.sums[region][coefficient];
                const double score = contribution / epsilon[coefficient];
                RegionPriority& priority = result.priority[region];
                if (score > priority.score) {
                    priority.score = score;
                    priority.contribution = contribution;
                    priority.nu_index = nu_index;
                    priority.nu = mean.nu;
                    priority.coefficient =
                        static_cast<SupportCoefficient>(coefficient);
                }
            }

            std::vector<RegionId> order(partition.region_count());
            std::iota(order.begin(), order.end(), RegionId{ 0 });
            std::sort(order.begin(), order.end(),
                [&mean, &partition, coefficient](RegionId lhs, RegionId rhs) {
                    const double left = mean.sums[lhs][coefficient];
                    const double right = mean.sums[rhs][coefficient];
                    if (left != right) return left > right;
                    return partition.regions[lhs].key < partition.regions[rhs].key;
                });

            double coverage = 0.0;
            const double target = 1.0 - epsilon[coefficient];
            for (RegionId region : order) {
                if (coverage >= target) break;
                coverage += mean.sums[region][coefficient];
                if (selected[region] == 0) {
                    selected[region] = 1;
                    std::ostringstream reason;
                    reason << "nu_index=" << (nu_index + 1)
                        << ";coefficient="
                        << coefficient_name(
                            static_cast<SupportCoefficient>(coefficient))
                        << ";statistic=time_mean";
                    result.selected_by[region] = reason.str();
                }
            }
            if (coverage + normalization_tolerance < target) {
                throw std::runtime_error(
                    "Region selector could not reach the requested mean coverage for nu_index=" +
                    std::to_string(nu_index + 1) + " coefficient=" +
                    coefficient_name(
                        static_cast<SupportCoefficient>(coefficient)) + ".");
            }
        }
    }

    std::sort(
        result.priority.begin(), result.priority.end(),
        [&partition](const RegionPriority& lhs, const RegionPriority& rhs) {
            if (lhs.score != rhs.score) return lhs.score > rhs.score;
            return partition.regions[lhs.region].key <
                partition.regions[rhs.region].key;
        });
    for (size_t index = 0; index < result.priority.size(); index++) {
        result.priority[index].rank = index + 1;
    }

    for (size_t region = 0; region < selected.size(); region++) {
        if (selected[region] != 0) {
            result.selection.keys.push_back(partition.regions[region].key);
        }
    }

    for (const auto& [nu_index, mean] : means) {
        for (size_t coefficient = 0; coefficient < SUPPORT_COEFFICIENT_COUNT;
            coefficient++) {
            if (mean.counts[coefficient] == 0) continue;
            double coverage = 0.0;
            for (size_t region = 0; region < selected.size(); region++) {
                if (selected[region] != 0) {
                    coverage += mean.sums[region][coefficient];
                }
            }
            result.minimum_mean_coverage[coefficient] = std::min(
                result.minimum_mean_coverage[coefficient], coverage);
        }
    }
    for (size_t coefficient = 0; coefficient < SUPPORT_COEFFICIENT_COUNT;
        coefficient++) {
        if (result.active_snapshots[coefficient] == 0) continue;
        if (result.minimum_mean_coverage[coefficient] + normalization_tolerance <
            1.0 - epsilon[coefficient]) {
            throw std::runtime_error(
                std::string("Final region union violates the requested mean coverage for ") +
                coefficient_name(
                    static_cast<SupportCoefficient>(coefficient)) + ".");
        }
    }
    return result;
}

} // namespace slow_light::regions
