#include "apps/RunConfig.h"

#if COPORTSL_APP == COPORTSL_GRRT

#include <algorithm>
#include <array>
#include <chrono>
#include <exception>
#include <filesystem>
#include <iostream>
#include <optional>
#include <span>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "Postprocess.h"
#include "src/grrt/RayGeometry.h"
#include "src/grrt/ImageError.h"
#include "src/grrt/ResultOutput.h"
#include "src/grrt/Signatures.h"
#include "src/grrt/fast/FastTransfer.h"
#include "src/grrt/fast/RegionExclusion.h"
#include "src/grrt/slow/Analysis.h"
#include "src/grrt/slow/SlowTransfer.h"
#include "src/grrt/slow/TimeOrigin.h"
#include "src/physics/Model.h"
#include "src/physics/fluid/FluidBackend.h"
#include "src/physics/fluid/FrameCache.h"
#include "src/physics/fluid/FrameSequence.h"
#include "src/physics/fluid/GridLocations.h"
#include "src/support/RunDirectory.h"

namespace {

void print_config(
    const fluid::FrameSequence& sequence,
    const grrt::Signatures& signatures,
    const run_io::RunDirectory* run = nullptr,
    const slow_light::analysis::AnalysisResult* analysis = nullptr,
    std::span<const fluid::FrameInfo> output_frames = {}) {

    std::cout << "Configuration\n"
        << "  task=" << grrt::task_name() << "\n"
        << "  electron_model=" << ModelConstants::electron_model_name() << "\n"
        << "  fluid_backend=" << fluid::Backend::name() << "\n"
        << "  frames=" << sequence.first().index << ".."
        << sequence.last().index << "\n"
        << "  frame_count=" << sequence.frames.size() << "\n"
        << "  input_cadence="
        << (sequence.uniform ? "uniform" : "irregular") << "\n"
        << "  input_dt_min=" << sequence.dt << " rg/c\n"
        << "  input_signature=" << signatures.input << "\n"
        << "  model_signature=" << signatures.model << "\n"
        << "  image=" << Config::NPIX << "x" << Config::NPIX << "\n"
        << "  frequency=" << Config::NU / 1e9 << " GHz\n"
        << "  data_dir=" << Config::DATA << "\n"
        << "  grid_file=" << Config::GRID << "\n";
    if (run != nullptr) std::cout << "  output_dir=" << run->path << "\n";
    if (!output_frames.empty()) {
        std::cout << "  output_frames=" << output_frames.front().index
            << ".." << output_frames.back().index << "\n"
            << "  output_frame_count=" << output_frames.size() << "\n";
    }
    if (analysis != nullptr) {
        std::cout << "  analysis_run=" << analysis->run.path << "\n"
            << "  analysis_signature=" << analysis->analysis_signature << "\n"
            << "  analysis_reused=" << std::boolalpha << analysis->reused << "\n"
            << "  suggested_region=" << analysis->suggested_regions.name << "\n";
    }
}

struct Geometry {
    ray::RayGeometry rays;
    fluid::GridLocations sampling;
};

Geometry build_geometry(const fluid::FrameSequence& sequence) {
    Geometry result;
    result.rays = ray::build_ray_geometry(
        Config::NPIX, Config::FOV, Config::OBS, fluid::Backend::probe_grid);
    result.sampling = fluid::locate_ray_samples(result.rays);
    return result;
}

slow_light::regions::RegionSelection selected_region(
    SlowLight::RegionMode mode,
    std::string_view manual_set,
    const slow_light::analysis::AnalysisResult* analysis) {

    if (mode == SlowLight::RegionMode::Suggest) {
        if (analysis == nullptr) {
            throw std::logic_error(
                "Suggested region selection requires a compatible analysis.");
        }
        return analysis->suggested_regions;
    }
    const auto item = std::find_if(
        SlowLight::REGION_SETS.begin(),
        SlowLight::REGION_SETS.end(),
        [manual_set](const auto& candidate) {
            return candidate.name == manual_set;
        });
    if (item == SlowLight::REGION_SETS.end()) {
        throw std::invalid_argument(
            "The configured manual region does not name a region set.");
    }
    return *item;
}

void run_fast(
    const run_io::RunDirectory& run,
    const fluid::FrameSequence& sequence,
    std::span<const fluid::FrameInfo> frames,
    const Geometry& geometry,
    const grrt::Signatures& signatures,
    bool recompute = false) {

    if (!recompute) {
        grrt::write_result_config(
            run, sequence, signatures, nullptr, nullptr, frames);
    }
    for (const fluid::FrameInfo& frame : frames) {
        const auto start = std::chrono::high_resolution_clock::now();
        fluid::Backend::load_active_frame(frame.path);
        std::vector<std::array<double, 4>> image;
        fast_light::compute_image(
            geometry.rays, geometry.sampling, Config::NU, image);
        grrt::write_stokes(run.path, frame.index, image);
        const std::chrono::duration<double> duration =
            std::chrono::high_resolution_clock::now() - start;
        std::cout << "Fast-light imaging: frame=" << frame.index
            << " time=" << frame.time
            << " runtime=" << duration.count() << " s\n";
    }
}

void run_slow(
    const run_io::RunDirectory& run,
    const fluid::FrameSequence& sequence,
    std::span<const fluid::FrameInfo> base_frames,
    const Geometry& geometry,
    const slow_light::analysis::SlowSelection& selection,
    const slow_light::analysis::AnalysisResult& analysis,
    const grrt::Signatures& signatures,
    bool recompute = false) {

    if (base_frames.empty()) {
        throw std::runtime_error(
            "Selected slow-light window has no safe base frames.");
    }
    if (!recompute) {
        grrt::write_result_config(
            run, sequence, signatures, &selection, &analysis, base_frames);
    }
    const auto partition = slow_light::regions::build_partition(
        geometry.rays.samples, SlowLight::REGION);
    const auto origin_mask =
        slow_light::time_origin::build_mask(geometry.rays.samples);
    const auto slow_mask =
        slow_light::regions::select_regions(partition, selection.regions);
    fluid::FrameCache cache = fluid::FrameCache::load(
        sequence, base_frames.front(), selection.left, selection.right);

    for (const fluid::FrameInfo& frame : base_frames) {
        const auto start = std::chrono::high_resolution_clock::now();
        cache.advance(frame.time);
        std::vector<std::array<double, 4>> image;
        const slow_light::TransferStats stats = slow_light::compute_image(
            geometry.rays,
            geometry.sampling,
            cache,
            Config::NU,
            origin_mask,
            slow_mask,
            selection.left,
            selection.right,
            image);
        grrt::write_stokes(run.path, frame.index, image);
        const std::chrono::duration<double> duration =
            std::chrono::high_resolution_clock::now() - start;
        std::cout << "Slow-light imaging: frame=" << frame.index
            << " time=" << frame.time
            << " inner_samples=" << stats.inner_samples
            << " clamped_samples=" << stats.clamped_samples
            << " runtime=" << duration.count() << " s\n";
    }
}

run_io::RunLock lock_run(const run_io::RunDirectory& run) {
    std::optional<run_io::RunLock> lock = run_io::try_lock_run(run);
    if (!lock) {
        throw std::runtime_error(
            "Matching result is still being written by another process: " +
            run.path.string());
    }
    return std::move(*lock);
}

void begin_resumed_run(
    const run_io::RunDirectory& run,
    std::span<const fluid::FrameInfo> frames) {

    run_io::write_run_status(run, "running");
    std::cout << "Recomputing requested " << grrt::task_name()
        << " result: " << run.path
        << " nt0=" << frames.front().index
        << " nt1=" << frames.back().index
        << " total=" << frames.size() << "\n";
}

std::array<double, 4> region_image_error(
    std::span<const grrt::StokesPixel> image,
    std::span<const grrt::StokesPixel> reference,
    int frame,
    const std::string& set,
    const char* mode) {

    try {
        return grrt::image_error(image, reference);
    }
    catch (const std::exception& error) {
        throw std::runtime_error(
            "Region error frame " + std::to_string(frame) +
            ", set " + set + ", mode " + mode + ": " + error.what());
    }
}

void run_region_error(
    const run_io::RunDirectory& run,
    const fluid::FrameSequence& sequence,
    const Geometry& geometry,
    const grrt::Signatures& signatures,
    std::span<const slow_light::regions::RegionSelection> selections) {

    const std::vector<fluid::FrameInfo> frames =
        fluid::sample_frames_by_step(
            sequence, static_cast<size_t>(RegionError::FRAME_STEP));
    grrt::write_result_config(
        run, sequence, signatures, nullptr, nullptr, {}, frames, selections);
    const auto partition = slow_light::regions::build_partition(
        geometry.rays.samples, SlowLight::REGION);
    std::vector<grrt::RegionErrorRecord> records;
    for (const fluid::FrameInfo& frame : frames) {
        fluid::Backend::load_active_frame(frame.path);
        fast_light::RegionExclusionResult result;
        fast_light::compute_region_exclusion(
            geometry.rays,
            geometry.sampling,
            Config::NU,
            partition,
            selections,
            result);
        for (const auto& selection : result.selections) {
            const auto emission =
                region_image_error(
                    selection.emission,
                    result.full,
                    frame.index,
                    selection.name,
                    "emission");
            const auto all =
                region_image_error(
                    selection.all_coefficients,
                    result.full,
                    frame.index,
                    selection.name,
                    "all");
            for (const auto& [mode, error] : {
                std::pair{"emission", emission},
                std::pair{"all", all}}) {
                records.push_back({
                    frame.index,
                    selection.name,
                    mode,
                    error
                });
            }
        }
    }
    grrt::write_region_errors(run.path, records, selections);
}

// Remove .run.lock after releasing it; a removal error is logged as a warning and does not fail the run.
void remove_run_lock(const run_io::RunDirectory& run) {
    if (run.path.empty()) return;
    std::error_code error;
    std::filesystem::remove(run.path / ".run.lock", error);
    if (error) {
        std::cerr << "Warning: cannot remove run lock file: "
            << (run.path / ".run.lock").string() << "\n";
    }
}

} // namespace

namespace grrt_app {

int inspect_input() {
    try {
        const fluid::FrameSequence sequence =
            fluid::discover_frame_sequence(Config::DATA);
        fluid::Backend::initialize_grid(sequence.first().path, Config::GRID);
        const grrt::Signatures signatures =
            grrt::make_signatures(sequence);
        print_config(sequence, signatures);
        std::cout << "  analysis_signature=" << signatures.analysis << "\n";
        return 0;
    }
    catch (const std::exception& error) {
        std::cerr << "Fatal error: " << error.what() << "\n";
        return 1;
    }
}

int run() {
    run_io::RunDirectory run;
    std::optional<run_io::RunLock> run_lock;
    int64_t status_nt0 = -1;
    int64_t status_nt1 = -1;
    try {
        const fluid::FrameSequence sequence =
            fluid::discover_frame_sequence(Config::DATA);
        fluid::Backend::initialize_grid(sequence.first().path, Config::GRID);
        const grrt::Signatures signatures =
            grrt::make_signatures(sequence);

        if constexpr (Config::TASK == Config::Task::Analysis) {
            if (const auto existing =
                slow_light::analysis::find_compatible_analysis(
                    sequence, signatures)) {
                std::cout << "Reusing slow-light analysis: "
                    << existing->run.path << "\n";
                postprocess::run(existing->run.path);
                return 0;
            }
            const Geometry geometry = build_geometry(sequence);
            const auto analysis = slow_light::analysis::run_analysis(
                sequence, geometry.rays, geometry.sampling, signatures);
            std::cout << "Analysis task complete: " << analysis.run.path << "\n";
            postprocess::run(analysis.run.path);
            return 0;
        }
        else if constexpr (Config::TASK == Config::Task::Fast) {
            const std::vector<fluid::FrameInfo> output_frames =
                fluid::select_frame_range(
                    sequence.frames, Config::FRAME_START, Config::FRAME_END);
            bool recompute = false;
            if (const auto existing =
                grrt::find_fast_result(output_frames, signatures.model)) {
                if (!existing->complete) {
                    run_io::RunLock lock = lock_run(existing->run);
                    run = existing->run;
                    run_lock = std::move(lock);
                    begin_resumed_run(run, output_frames);
                    recompute = true;
                }
                else {
                    std::cout << "Reusing fast-light result: "
                        << existing->run.path << "\n";
                    postprocess::run(existing->run.path);
                    postprocess::print_evpa_command(existing->run.path);
                    return 0;
                }
            }
            else {
                run = run_io::allocate_run_directory(Config::OUTPUT / "fast");
                run_io::write_run_paths(
                    run, Config::DATA, Config::GRID, Config::OUTPUT);
                run_lock = lock_run(run);
            }
            status_nt0 = output_frames.front().index;
            status_nt1 = output_frames.back().index;
            print_config(sequence, signatures, &run, nullptr, output_frames);
            const Geometry geometry = build_geometry(sequence);
            run_fast(
                run,
                sequence,
                output_frames,
                geometry,
                signatures,
                recompute);
        }
        else if constexpr (Config::TASK == Config::Task::Slow) {
            std::optional<slow_light::analysis::AnalysisResult> analysis =
                slow_light::analysis::find_compatible_analysis(
                    sequence, signatures);
            const Geometry geometry = build_geometry(sequence);
            if (!analysis) {
                analysis = slow_light::analysis::run_analysis(
                    sequence, geometry.rays, geometry.sampling, signatures);
            }
            const slow_light::regions::RegionSelection selection =
                selected_region(
                    SlowLight::REGION_MODE,
                    SlowLight::MANUAL_SET,
                    &*analysis);
            const auto slow_selection = slow_light::analysis::prepare_selection(
                sequence, geometry.rays, selection, {});
            const std::vector<fluid::FrameInfo> safe_frames =
                fluid::safe_base_frames(
                    sequence, slow_selection.left, slow_selection.right);
            if (safe_frames.empty()) {
                throw std::runtime_error(
                    "Selected slow-light window has no safe base frames.");
            }
            const std::vector<fluid::FrameInfo> output_frames =
                fluid::select_frame_range(
                    safe_frames, Config::FRAME_START, Config::FRAME_END);
            bool recompute = false;
            if (const auto existing = grrt::find_slow_result(
                output_frames, signatures, slow_selection)) {
                if (!existing->complete) {
                    run_io::RunLock lock = lock_run(existing->run);
                    run = existing->run;
                    run_lock = std::move(lock);
                    begin_resumed_run(run, output_frames);
                    recompute = true;
                }
                else {
                    std::cout << "Reusing slow-light result: "
                        << existing->run.path << "\n";
                    postprocess::run(existing->run.path);
                    postprocess::print_evpa_command(existing->run.path);
                    return 0;
                }
            }
            else {
                run = run_io::allocate_run_directory(Config::OUTPUT / "slow");
                run_io::write_run_paths(
                    run,
                    Config::DATA,
                    Config::GRID,
                    Config::OUTPUT,
                    std::filesystem::relative(analysis->run.path, run.path));
                run_lock = lock_run(run);
            }
            status_nt0 = output_frames.front().index;
            status_nt1 = output_frames.back().index;
            slow_light::analysis::write_selection_map(
                geometry.rays, slow_selection.regions, run.path);
            print_config(
                sequence, signatures, &run, &*analysis, output_frames);
            run_slow(
                run,
                sequence,
                output_frames,
                geometry,
                slow_selection,
                *analysis,
                signatures,
                recompute);
        }
        else {
            const Geometry geometry = build_geometry(sequence);
            const std::vector<fluid::FrameInfo> region_error_frames =
                fluid::sample_frames_by_step(
                    sequence, static_cast<size_t>(RegionError::FRAME_STEP));
            if (const auto existing = grrt::find_region_error_result(
                region_error_frames, SlowLight::REGION_SETS, signatures.model)) {
                if (existing->complete) {
                    std::cout << "Reusing region-error result: "
                        << existing->run.path << "\n";
                    postprocess::run(existing->run.path);
                    return 0;
                }
                run = existing->run;
                run_lock = lock_run(existing->run);
            }
            else {
                run = run_io::allocate_run_directory(
                    Config::OUTPUT / "region_error");
                run_io::write_run_paths(
                    run, Config::DATA, Config::GRID, Config::OUTPUT);
                run_lock = lock_run(run);
            }
            status_nt0 = sequence.first().index;
            status_nt1 = sequence.last().index;
            print_config(sequence, signatures, &run);
            run_region_error(
                run,
                sequence,
                geometry,
                signatures,
                SlowLight::REGION_SETS);
        }

        run_io::write_run_status(run, "complete", status_nt0, status_nt1);
        postprocess::run(run.path);
        if constexpr (
            Config::TASK == Config::Task::Fast ||
            Config::TASK == Config::Task::Slow) {
            postprocess::print_evpa_command(run.path);
        }
        run_lock.reset();
        remove_run_lock(run);
        return 0;
    }
    catch (const std::exception& error) {
        if (!run.path.empty()) {
            try {
                run_io::write_run_status(
                    run, "failed", status_nt0, status_nt1);
            }
            catch (...) {
            }
        }
        run_lock.reset();
        remove_run_lock(run);
        std::cerr << "Fatal error: " << error.what() << "\n";
        return 1;
    }
}

} // namespace grrt_app

#endif
