#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <vector>

#include "Region.h"

namespace slow_light::regions {

enum class SupportCoefficient : size_t {
    jI,
    jP,
    aI,
    aP,
    rhoV,
    rhoC,
    count
};

inline constexpr size_t SUPPORT_COEFFICIENT_COUNT =
    static_cast<size_t>(SupportCoefficient::count);

using CoefficientValues = std::array<double, SUPPORT_COEFFICIENT_COUNT>;
using CoefficientFlags = std::array<uint8_t, SUPPORT_COEFFICIENT_COUNT>;

struct CoefficientTolerances {
    double jI = 2.0e-3;
    double jP = 2.0e-3;
    double aI = 1.0e-3;
    double aP = 1.0e-3;
    double rhoV = 2.6e-1;
    double rhoC = 2.5e-2;

    CoefficientValues values() const noexcept;
};

struct ContributionSnapshot {
    int frame = 0;
    double time = 0.0;
    size_t nu_index = 0;
    double nu = 0.0;
    std::vector<CoefficientValues> regions;
    CoefficientFlags active = {};
};

struct RegionPriority {
    RegionId region = 0;
    size_t rank = 0;
    double score = 0.0;
    double contribution = 0.0;
    size_t nu_index = 0;
    double nu = 0.0;
    SupportCoefficient coefficient = SupportCoefficient::count;
};

struct RegionSelectionResult {
    RegionSelection selection;
    CoefficientValues minimum_mean_coverage = {};
    std::array<uint64_t, SUPPORT_COEFFICIENT_COUNT> active_snapshots = {};
    std::vector<std::string> selected_by;
    std::vector<RegionPriority> priority;
};

const char* coefficient_name(SupportCoefficient coefficient) noexcept;

RegionSelectionResult select_by_contribution(
    const RegionPartition& partition,
    const std::vector<ContributionSnapshot>& snapshots,
    const CoefficientTolerances& tolerances,
    double normalization_tolerance = 1.0e-10);

} // namespace slow_light::regions
