#pragma once

#include <filesystem>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "src/grrt/Signatures.h"
#include "src/grrt/slow/regions/Region.h"
#include "src/physics/fluid/FrameSequence.h"
#include "src/support/RunDirectory.h"

namespace slow_light::analysis {

struct AnalysisResult {
    run_io::RunDirectory run;
    regions::RegionSelection suggested_regions;
    std::string model_signature;
    std::string analysis_signature;
    bool reused = false;
};

struct StoredWindow {
    std::string name;
    double left = 0.0;
    double right = 0.0;
};

std::vector<std::filesystem::path> required_files(
    const regions::RegionDefinition& definition);

regions::RegionSelection read_suggestion(
    const run_io::RunDirectory& run,
    const regions::RegionDefinition& definition);

StoredWindow read_window(
    const run_io::RunDirectory& run,
    std::string_view name);

std::optional<AnalysisResult> find_stored_analysis(
    const std::filesystem::path& root,
    std::string_view model_signature,
    std::string_view analysis_signature,
    const regions::RegionDefinition& definition);

std::optional<AnalysisResult> find_compatible_stored_analysis(
    const std::filesystem::path& root,
    const fluid::FrameSequence& sequence,
    const grrt::Signatures& signatures,
    const regions::RegionDefinition& definition);

} // namespace slow_light::analysis
