#pragma once

#include <optional>
#include <filesystem>
#include <string>

#include "src/physics/fluid/GridLocations.h"
#include "src/physics/fluid/FrameSequence.h"
#include "src/support/RunDirectory.h"
#include "src/grrt/RayGeometry.h"
#include "src/grrt/Signatures.h"
#include "AnalysisStore.h"
#include "regions/Region.h"

namespace slow_light::analysis {

struct SlowSelection {
    regions::RegionSelection regions;
    std::string window;
    double left = 0.0;
    double right = 0.0;
};

std::optional<AnalysisResult> find_compatible_analysis(
    const fluid::FrameSequence& sequence,
    const grrt::Signatures& signatures);

AnalysisResult run_analysis(
    const fluid::FrameSequence& sequence,
    const ray::RayGeometry& rays,
    const fluid::GridLocations& sampling,
    const grrt::Signatures& signatures);

SlowSelection prepare_selection(
    const fluid::FrameSequence& sequence,
    const ray::RayGeometry& rays,
    const regions::RegionSelection& selection,
    const std::filesystem::path& output_directory);

void write_selection_map(
    const ray::RayGeometry& rays,
    const regions::RegionSelection& selection,
    const std::filesystem::path& output_directory);

} // namespace slow_light::analysis
