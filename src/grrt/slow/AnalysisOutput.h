#pragma once

#include <filesystem>
#include <span>
#include <vector>

#include "src/grrt/RayGeometry.h"
#include "src/grrt/Signatures.h"
#include "src/grrt/fast/RegionStats.h"
#include "src/grrt/slow/TimeOffsetStats.h"
#include "src/grrt/slow/regions/Region.h"
#include "src/physics/fluid/FrameSequence.h"

namespace slow_light::analysis::output {

struct ContributionFrame {
    int frame = 0;
    std::vector<fast_light::RegionCoefficients> regions;
};

void write_config(
    const std::filesystem::path& directory,
    const fluid::FrameSequence& sequence,
    const grrt::Signatures& signatures);

void write_contributions(
    const std::filesystem::path& directory,
    const regions::RegionPartition& partition,
    std::span<const ContributionFrame> frames);

void write_time_histogram(
    const std::vector<double>& offsets,
    double dt,
    const std::filesystem::path& file);

void write_windows(
    const std::vector<CoverageWindow>& windows,
    const std::filesystem::path& file);

void write_time_span_map(
    const ray::RayGeometry& rays,
    const regions::SampleMask& slow_mask,
    const std::filesystem::path& file);

void write_region_keys(
    const regions::RegionSelection& selection,
    const std::filesystem::path& file);

} // namespace slow_light::analysis::output
