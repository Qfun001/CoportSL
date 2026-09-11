#pragma once

#include <array>
#include <filesystem>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

#include "src/grrt/Signatures.h"
#include "src/grrt/slow/Analysis.h"
#include "src/physics/fluid/FrameSequence.h"
#include "src/support/RunDirectory.h"

namespace grrt {

struct RegionErrorRecord {
    int frame = 0;
    std::string region_set;
    std::string mode;
    std::array<double, 4> error = {};
};

struct StokesRun {
    run_io::RunDirectory run;
    bool complete = false;
};

std::string_view task_name();

std::optional<StokesRun> find_fast_result(
    std::span<const fluid::FrameInfo> frames,
    std::string_view model_signature);

std::optional<StokesRun> find_slow_result(
    std::span<const fluid::FrameInfo> frames,
    const Signatures& signatures,
    const slow_light::analysis::SlowSelection& selection);

std::optional<StokesRun> find_region_error_result(
    std::span<const fluid::FrameInfo> frames,
    std::span<const slow_light::regions::RegionSelection> selections,
    std::string_view model_signature);

void write_result_config(
    const run_io::RunDirectory& run,
    const fluid::FrameSequence& sequence,
    const Signatures& signatures,
    const slow_light::analysis::SlowSelection* selection = nullptr,
    const slow_light::analysis::AnalysisResult* analysis = nullptr,
    std::span<const fluid::FrameInfo> output_frames = {},
    std::span<const fluid::FrameInfo> region_error_frames = {},
    std::span<const slow_light::regions::RegionSelection>
        region_error_selections = {});

void write_stokes(
    const std::filesystem::path& directory,
    int frame,
    const std::vector<std::array<double, 4>>& image);

void write_region_errors(
    const std::filesystem::path& directory,
    std::span<const RegionErrorRecord> records,
    std::span<const slow_light::regions::RegionSelection> selections);

} // namespace grrt
