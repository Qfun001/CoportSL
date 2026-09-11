#include "apps/RunConfig.h"

#if COPORTSL_APP == COPORTSL_GRRT

#include "ResultOutput.h"

#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>

#include "src/grrt/ConfigOutput.h"
#include "src/grrt/Resume.h"
#include "src/grrt/slow/TimeOrigin.h"
#include "src/support/OutputFile.h"

namespace grrt {
namespace {

std::vector<std::filesystem::path> required_stokes_files(
    std::span<const fluid::FrameInfo> frames) {

    std::vector<std::filesystem::path> files;
    files.reserve(frames.size() * 4);
    for (const fluid::FrameInfo& frame : frames) {
        for (const std::filesystem::path& file :
             resume::stokes_files({}, frame.index)) {
            files.push_back(file);
        }
    }
    return files;
}

std::string precise(double value) {
    std::ostringstream text;
    text << std::setprecision(17) << value;
    return text.str();
}

std::string region_keys(
    const slow_light::regions::RegionSelection& selection) {

    std::ostringstream text;
    for (size_t index = 0; index < selection.keys.size(); index++) {
        if (index != 0) text << ";";
        text << selection.keys[index];
    }
    return text.str();
}

bool safe_region_directory(std::string_view name) {
    constexpr std::string_view allowed =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-";
    return !name.empty() && name.find_first_not_of(allowed) == name.npos;
}

std::optional<StokesRun> find_stokes_result(
    const std::filesystem::path& category,
    std::span<const std::pair<std::string_view, std::string_view>> config_values,
    std::span<const fluid::FrameInfo> frames) {

    const std::vector<std::filesystem::path> files =
        required_stokes_files(frames);
    // Reuse complete CSV output regardless of the recorded status.
    if (const auto complete = run_io::find_latest_complete_run(
        category,
        config_values,
        files,
        static_cast<uint64_t>(Config::NPIX),
        static_cast<uint64_t>(Config::NPIX))) {
        return StokesRun{*complete, true};
    }
    // Identity matched but CSV incomplete → Continue.
    if (const auto partial = run_io::find_latest_matching_run(
        category, config_values)) {
        return StokesRun{*partial, false};
    }
    return std::nullopt;
}

void write_region_keys(
    std::ostream& out,
    const slow_light::regions::RegionSelection& selection) {

    out << "SlowLight::REGION_KEYS=";
    for (size_t index = 0; index < selection.keys.size(); index++) {
        if (index != 0) out << ";";
        out << selection.keys[index];
    }
    out << "\n";
}

} // namespace

std::string_view task_name() {
    switch (Config::TASK) {
    case Config::Task::Analysis: return "analysis";
    case Config::Task::Fast: return "fast";
    case Config::Task::Slow: return "slow";
    case Config::Task::RegionError: return "region_error";
    }
    throw std::logic_error("Unknown GRRT task.");
}

std::optional<StokesRun> find_fast_result(
    std::span<const fluid::FrameInfo> frames,
    std::string_view model_signature) {

    if (frames.empty()) return std::nullopt;
    const std::pair<std::string_view, std::string_view> config_values[] = {
        {"Config::TASK", "fast"},
        {"model_signature", model_signature}
    };
    return find_stokes_result(
        Config::OUTPUT / "fast", config_values, frames);
}

std::optional<StokesRun> find_slow_result(
    std::span<const fluid::FrameInfo> frames,
    const Signatures& signatures,
    const slow_light::analysis::SlowSelection& selection) {

    const std::string region_hash =
        slow_light::regions::definition_hash(SlowLight::REGION);
    const std::string mode =
        SlowLight::REGION_MODE == SlowLight::RegionMode::Suggest ?
        "suggest" : "manual";
    const std::string keys = region_keys(selection.regions);
    const std::string left = precise(selection.left);
    const std::string right = precise(selection.right);
    if (frames.empty()) return std::nullopt;
    const std::pair<std::string_view, std::string_view> config_values[] = {
        {"Config::TASK", "slow"},
        {"model_signature", signatures.model},
        {"analysis_signature", signatures.analysis},
        {"SlowLight::REGION_HASH", region_hash},
        {"SlowLight::REGION_MODE", mode},
        {"SlowLight::REGION_KEYS", keys},
        {"SlowLight::WINDOW", selection.window},
        {"SlowLight::LEFT", left},
        {"SlowLight::RIGHT", right}
    };
    return find_stokes_result(
        Config::OUTPUT / "slow", config_values, frames);
}

std::optional<StokesRun> find_region_error_result(
    std::span<const fluid::FrameInfo> frames,
    std::span<const slow_light::regions::RegionSelection> selections,
    std::string_view model_signature) {

    if (frames.empty() || selections.empty()) return std::nullopt;

    std::ostringstream frames_text;
    for (size_t index = 0; index < frames.size(); index++) {
        if (index != 0) frames_text << ";";
        frames_text << frames[index].index;
    }
    std::ostringstream sets_text;
    std::vector<std::filesystem::path> files;
    files.reserve(selections.size());
    for (size_t index = 0; index < selections.size(); index++) {
        if (index != 0) sets_text << ";";
        sets_text << selections[index].name;
        files.push_back(
            std::filesystem::path(selections[index].name) / "error.csv");
    }
    const std::string region_hash =
        slow_light::regions::definition_hash(SlowLight::REGION);
    const std::string frame_step = std::to_string(RegionError::FRAME_STEP);
    const std::string frames_value = frames_text.str();
    const std::string sets_value = sets_text.str();

    const std::pair<std::string_view, std::string_view> config_values[] = {
        {"Config::TASK", "region_error"},
        {"model_signature", model_signature},
        {"SlowLight::REGION_HASH", region_hash},
        {"RegionError::FRAME_STEP", frame_step},
        {"RegionError::FRAMES", frames_value},
        {"RegionError::SETS", sets_value}
    };
    if (const auto complete = run_io::find_latest_complete_run(
        Config::OUTPUT / "region_error", config_values, files)) {
        return StokesRun{*complete, true};
    }
    if (const auto partial = run_io::find_latest_matching_run(
        Config::OUTPUT / "region_error", config_values)) {
        return StokesRun{*partial, false};
    }
    return std::nullopt;
}

void write_result_config(
    const run_io::RunDirectory& run,
    const fluid::FrameSequence& sequence,
    const Signatures& signatures,
    const slow_light::analysis::SlowSelection* selection,
    const slow_light::analysis::AnalysisResult* analysis,
    std::span<const fluid::FrameInfo> output_frames,
    std::span<const fluid::FrameInfo> region_error_frames,
    std::span<const slow_light::regions::RegionSelection>
        region_error_selections) {

    const std::filesystem::path file = run.path / "config.txt";
    std::ofstream out(file);
    if (!out) {
        throw std::runtime_error(
            "Cannot write result config: " +
            (run.path / "config.txt").string());
    }
    out << "Config::TASK=" << task_name() << "\n";
    write_model_config(out, sequence, signatures);
    if (analysis != nullptr) {
        out << "analysis_signature=" << signatures.analysis << "\n";
    }
    if (selection != nullptr) {
        out << "SlowLight::REGION=" << SlowLight::REGION.name << "\n"
            << "SlowLight::REGION_HASH="
            << slow_light::regions::definition_hash(SlowLight::REGION) << "\n"
            << "TimeOrigin::NAME=" << slow_light::time_origin::NAME << "\n"
            << "TimeOrigin::RADIUS=" << slow_light::time_origin::RADIUS << "\n"
            << "SlowLight::REGION_MODE="
            << (SlowLight::REGION_MODE == SlowLight::RegionMode::Suggest ?
                "suggest" : "manual") << "\n";
        write_region_keys(out, selection->regions);
        out << "SlowLight::WINDOW=" << selection->window << "\n"
            << "SlowLight::LEFT=" << selection->left << "\n"
            << "SlowLight::RIGHT=" << selection->right << "\n";
    }
    if constexpr (Config::TASK == Config::Task::RegionError) {
        if (region_error_frames.empty()) {
            throw std::invalid_argument(
                "RegionError result config requires sampled frames.");
        }
        out << "SlowLight::REGION=" << SlowLight::REGION.name << "\n"
            << "SlowLight::REGION_HASH="
            << slow_light::regions::definition_hash(SlowLight::REGION) << "\n"
            << "RegionError::FRAME_STEP=" << RegionError::FRAME_STEP << "\n"
            << "RegionError::FRAMES=";
        for (size_t index = 0; index < region_error_frames.size(); index++) {
            if (index != 0) out << ";";
            out << region_error_frames[index].index;
        }
        out << "\n";
        if (region_error_selections.empty()) {
            throw std::invalid_argument(
                "RegionError result config requires selected regions.");
        }
        out << "RegionError::SETS=";
        for (size_t index = 0; index < region_error_selections.size(); index++) {
            if (!safe_region_directory(region_error_selections[index].name)) {
                throw std::invalid_argument(
                    "RegionError set name is not a safe directory name: " +
                    region_error_selections[index].name);
            }
            if (index != 0) out << ";";
            out << region_error_selections[index].name;
        }
        out << "\n";
        for (const auto& region : region_error_selections) {
            out << "RegionError::SET." << region.name << "="
                << region_keys(region) << "\n";
        }
    }
    output_file::close(out, file, "result config");
}

void write_stokes(
    const std::filesystem::path& directory,
    int frame,
    const std::vector<std::array<double, 4>>& image) {

    resume::discard_frame(directory, frame);
    constexpr char names[4] = {'I', 'Q', 'U', 'V'};
    for (int stokes = 0; stokes < 4; stokes++) {
        const std::filesystem::path file =
            resume::stokes_file(directory, names[stokes], frame);
        std::ofstream out(file);
        if (!out) {
            throw std::runtime_error(
                "Cannot write Stokes output: " + file.string());
        }
        for (int row = 0; row < Config::NPIX; row++) {
            for (int col = 0; col < Config::NPIX; col++) {
                const int pixel =
                    row * Config::NPIX + (Config::NPIX - 1 - col);
                out << image[static_cast<size_t>(pixel)][stokes];
                if (col + 1 != Config::NPIX) out << ",";
            }
            out << "\n";
        }
        output_file::close(out, file, "Stokes output");
        std::cout << "File written successfully to " << file << "\n";
    }
}

void write_region_errors(
    const std::filesystem::path& directory,
    std::span<const RegionErrorRecord> records,
    std::span<const slow_light::regions::RegionSelection> selections) {

    for (const auto& selection : selections) {
        if (!safe_region_directory(selection.name)) {
            throw std::invalid_argument(
                "RegionError set name is not a safe directory name: " +
                selection.name);
        }
        const std::filesystem::path relative =
            std::filesystem::path(selection.name) / "error.csv";
        const std::filesystem::path file = directory / relative;
        std::filesystem::create_directories(file.parent_path());
        std::ofstream out(file);
        if (!out) {
            throw std::runtime_error(
                "Cannot write region-error CSV: " + file.string());
        }
        out << "frame,mode,I_error,Q_error,U_error,V_error\n";
        uint64_t rows = 0;
        for (const RegionErrorRecord& record : records) {
            if (record.region_set != selection.name) continue;
            out << record.frame << "," << record.mode;
            for (double value : record.error) {
                out << "," << std::setprecision(17) << value;
            }
            out << "\n";
            rows++;
        }
        if (rows == 0) {
            throw std::runtime_error(
                "Region-error set has no records: " + selection.name);
        }
        output_file::close(out, file, "region-error CSV");
    }
}

} // namespace grrt

#endif
