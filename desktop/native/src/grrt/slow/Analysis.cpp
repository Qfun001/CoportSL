#include "apps/RunConfig.h"

#if COPORTSL_APP != COPORTSL_FLUX

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "src/grrt/fast/RegionStats.h"
#include "src/physics/Model.h"
#include "src/physics/fluid/FluidBackend.h"
#include "src/config/Runtime.h"
#include "src/physics/fluid/GridLocations.h"
#include "src/support/RunDirectory.h"
#include "src/grrt/slow/Analysis.h"
#include "src/grrt/slow/AnalysisOutput.h"
#include "src/grrt/slow/TimeOffsetStats.h"
#include "src/grrt/slow/TimeOrigin.h"

namespace slow_light::analysis {
namespace {

std::vector<fluid::FrameInfo> analysis_input_frames(
    const fluid::FrameSequence& sequence) {
    return fluid::sample_frames(sequence, Analysis::SAMPLE_DT);
}

std::string selected_window_name() {
#if COPORTSL_APP == COPORTSL_BENCHMARK
    return BenchmarkConfig::WINDOW;
#else
    switch (SlowLight::WINDOW) {
    case SlowLight::Window::P90: return "p90";
    case SlowLight::Window::P95: return "p95";
    case SlowLight::Window::P99: return "p99";
    case SlowLight::Window::P99_9: return "p99.9";
    case SlowLight::Window::Full: return "full";
    }
    throw std::logic_error("Unknown slow-light window.");
#endif
}

struct CoefficientAnalysis {
    regions::RegionPartition partition;
    regions::RegionSelectionResult result;
    std::vector<output::ContributionFrame> frames;
};

CoefficientAnalysis run_coefficient_variability(
    const fluid::FrameSequence& sequence,
    const ray::RayGeometry& rays,
    const fluid::GridLocations& sampling) {

    auto partition = regions::build_partition(
        rays.samples, SlowLight::REGION);

    std::vector<regions::ContributionSnapshot> snapshots;
    std::vector<output::ContributionFrame> frames;
    for (const fluid::FrameInfo& frame : analysis_input_frames(sequence)) {
        runtime_config::throw_if_cancelled();
        fluid::Backend::load_active_frame(frame.path);
        auto stats = fast_light::regional_coefficient_stats(
            rays, sampling, Config::NU, partition);
        regions::CoefficientValues totals = {};
        for (const auto& item : stats) {
            totals[0] += item.jI_abs;
            totals[1] += item.jP_abs;
            totals[2] += item.aI_abs;
            totals[3] += item.aP_abs;
            totals[4] += item.rhoV_abs;
            totals[5] += item.rhoC_abs;
        }

        regions::ContributionSnapshot snapshot;
        snapshot.frame = frame.index;
        snapshot.time = frame.time;
        snapshot.nu = Config::NU;
        snapshot.regions.resize(stats.size());
        for (size_t coefficient = 0; coefficient < totals.size(); coefficient++) {
            snapshot.active[coefficient] = totals[coefficient] > 0.0;
        }
        for (size_t region = 0; region < stats.size(); region++) {
            const auto& item = stats[region];
            const regions::CoefficientValues absolute = {
                item.jI_abs, item.jP_abs, item.aI_abs,
                item.aP_abs, item.rhoV_abs, item.rhoC_abs
            };
            for (double value : absolute) {
                if (!(value >= 0.0) || !std::isfinite(value)) {
                    throw std::runtime_error(
                        "Non-finite regional transfer coefficient.");
                }
            }
            for (size_t coefficient = 0;
                coefficient < totals.size(); coefficient++) {
                snapshot.regions[region][coefficient] =
                    totals[coefficient] == 0.0 ? 0.0 :
                    absolute[coefficient] / totals[coefficient];
            }
        }
        snapshots.push_back(std::move(snapshot));
        frames.push_back({frame.index, std::move(stats)});
        std::cout << "Coefficient variability complete: frame="
            << frame.index << "\n";
    }

    auto result = regions::select_by_contribution(
        partition, snapshots, Analysis::REGION_TOLERANCES);

    std::cout << "Suggested region selection: partition=" << partition.name
        << " definition_hash=" << partition.definition_hash << " keys=";
    for (size_t index = 0; index < result.selection.keys.size(); index++) {
        if (index != 0) std::cout << ",";
        std::cout << result.selection.keys[index];
    }
    std::cout << "\n";
    return {
        std::move(partition),
        std::move(result),
        std::move(frames)
    };
}

std::vector<double> time_offsets(
    const ray::RayGeometry& rays,
    const regions::SampleMask& origin_mask,
    const regions::SampleMask& slow_mask) {

    const double origin =
        time_origin::reference_offset(rays, origin_mask);

    std::vector<double> values;
    for (size_t index = 0; index < rays.samples.size(); index++) {
        if (!slow_mask[index]) continue;
        values.push_back(
            time_origin::relative_offset(rays.samples[index], origin));
    }
    if (values.empty()) {
        throw std::runtime_error("Slow-light region contains no ray samples.");
    }
    return values;
}

std::vector<CoverageWindow> candidate_windows(
    const std::vector<double>& offsets) {

    const std::vector<CoverageWindowRequest> candidates = {
        {"p90", 0.90},
        {"p95", 0.95},
        {"p99", 0.99},
        {"p99.9", 0.999},
        {"full", 1.0}
    };
    return shortest_coverage_windows(candidates, offsets);
}

struct PreparedSelection {
    SlowSelection selection;
    std::vector<double> offsets;
    std::vector<CoverageWindow> windows;
    regions::SampleMask mask;
};

PreparedSelection prepare_selection_data(
    const ray::RayGeometry& rays,
    const regions::RegionPartition& partition,
    const regions::RegionSelection& selection) {

    const auto origin_mask = time_origin::build_mask(rays.samples);
    auto slow_mask = regions::select_regions(partition, selection);
    auto offsets = time_offsets(rays, origin_mask, slow_mask);
    auto windows = candidate_windows(offsets);
    const std::string name = selected_window_name();
    const auto selected = std::find_if(
        windows.begin(), windows.end(),
        [&name](const CoverageWindow& window) {
            return window.name == name;
        });
    if (selected == windows.end()) {
        throw std::logic_error("Configured slow-light window was not generated.");
    }
    return {
        {selection, selected->name, selected->left, selected->right},
        std::move(offsets),
        std::move(windows),
        std::move(slow_mask)
    };
}

void write_selection_diagnostics(
    double frame_dt,
    const ray::RayGeometry& rays,
    const regions::RegionPartition& partition,
    const regions::RegionSelection& selection,
    const std::filesystem::path& directory,
    bool write_suggestion) {

    std::filesystem::create_directories(directory);
    const PreparedSelection prepared =
        prepare_selection_data(rays, partition, selection);
    output::write_time_histogram(
        prepared.offsets, frame_dt, directory / "offset_histogram.csv");
    output::write_time_span_map(
        rays, prepared.mask, directory / "time_span.csv");
    if (write_suggestion) {
        output::write_windows(prepared.windows, directory / "windows.csv");
        output::write_region_keys(selection, directory / "regions.txt");
    }
}

SlowSelection run_time_offset_analysis(
    const std::filesystem::path& output_directory,
    const fluid::FrameSequence& sequence,
    const ray::RayGeometry& rays,
    const regions::RegionPartition& partition,
    const regions::RegionSelection& suggestion) {

    for (const auto& info : partition.regions) {
        const regions::RegionSelection selection{
            info.key, {info.key}
        };
        write_selection_diagnostics(
            sequence.dt,
            rays,
            partition,
            selection,
            output_directory / "regions" / info.key,
            false);
    }
    write_selection_diagnostics(
        sequence.dt,
        rays,
        partition,
        suggestion,
        output_directory / "suggest",
        true);
    return prepare_selection_data(rays, partition, suggestion).selection;
}

} // namespace

std::optional<AnalysisResult> find_compatible_analysis(
    const fluid::FrameSequence& sequence,
    const grrt::Signatures& signatures) {

    return find_compatible_stored_analysis(
        Config::OUTPUT / "analysis",
        sequence,
        signatures,
        SlowLight::REGION);
}

AnalysisResult run_analysis(
    const fluid::FrameSequence& sequence,
    const ray::RayGeometry& rays,
    const fluid::GridLocations& sampling,
    const grrt::Signatures& signatures) {

    run_io::RunDirectory run;
    try {
        run = run_io::allocate_run_directory(Config::OUTPUT / "analysis");
        run_io::write_run_paths(run, Config::DATA, Config::GRID, Config::OUTPUT);
        std::cout << "Slow-light prerequisite analysis\n"
            << "  run_id=" << run.name << "\n"
            << "  model_signature=" << signatures.model << "\n"
            << "  analysis_signature=" << signatures.analysis << "\n"
            << "  electron_model="
            << ModelConstants::electron_model_name() << "\n"
            << "  output_dir=" << run.path << "\n";

        output::write_config(run.path, sequence, signatures);
        const CoefficientAnalysis coefficients =
            run_coefficient_variability(sequence, rays, sampling);
        output::write_contributions(
            run.path,
            coefficients.partition,
            coefficients.frames);
        const SlowSelection selection = run_time_offset_analysis(
            run.path,
            sequence,
            rays,
            coefficients.partition,
            coefficients.result.selection);
        run_io::write_run_status(run, "complete");
        std::cout << "Slow-light prerequisite analysis complete: "
            << run.path << "\n";
        return AnalysisResult{
            run,
            selection.regions,
            signatures.model,
            signatures.analysis,
            false
        };
    }
    catch (...) {
        if (!run.path.empty()) {
            try {
                run_io::write_run_status(run, "failed");
            }
            catch (...) {
            }
        }
        throw;
    }
}

SlowSelection prepare_selection(
    const fluid::FrameSequence& sequence,
    const ray::RayGeometry& rays,
    const regions::RegionSelection& selection,
    const std::filesystem::path& output_directory) {

    const auto partition = regions::build_partition(
        rays.samples, SlowLight::REGION);
    const PreparedSelection prepared =
        prepare_selection_data(rays, partition, selection);
    if (!output_directory.empty()) {
        std::filesystem::create_directories(output_directory);
        output::write_time_span_map(
            rays, prepared.mask, output_directory / "time_span.csv");
    }
    return prepared.selection;
}

void write_selection_map(
    const ray::RayGeometry& rays,
    const regions::RegionSelection& selection,
    const std::filesystem::path& output_directory) {

    const auto partition = regions::build_partition(
        rays.samples, SlowLight::REGION);
    const auto mask = regions::select_regions(partition, selection);
    std::filesystem::create_directories(output_directory);
    output::write_time_span_map(rays, mask, output_directory / "time_span.csv");
}

} // namespace slow_light::analysis

#endif
