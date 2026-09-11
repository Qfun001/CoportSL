#pragma once

#include <filesystem>
#include <vector>

#include "../BackendTypes.h"
#include "../State.h"
#include "Reader.h"
#include "Sampler.h"

namespace support {
class Signature;
}

namespace fluid::harmpi {

class Backend {
public:
    using Location = harmpi::Location;
    using Frame = harmpi::Frame;

    static constexpr const char* name() { return "harmpi"; }

    static void initialize_grid(
        const std::filesystem::path& first_frame,
        const std::filesystem::path& unused_grid_file = {});
    static double frame_time(const std::filesystem::path& frame_file);
    static std::filesystem::path frame_path(
        const std::filesystem::path& data_dir,
        int index);
    static std::vector<FrameInfo> discover_frames(
        const std::filesystem::path& data_dir);
    static void add_input_identity(
        support::Signature& signature,
        const std::filesystem::path& unused_grid_file,
        const FrameInfo& first_frame);
    static void load_active_frame(const std::filesystem::path& frame_file);
    static Frame load_frame(const std::filesystem::path& frame_file);
    static GridStats grid_stats();

    static bool probe_grid(
        const Position& x,
        const WaveVector& k,
        uint64_t& hint,
        double& max_step);
    static bool locate(const Position& x, uint64_t& hint, Location& location);

    static bool sample_active(
        const Position& x,
        const Location& location,
        State& state,
        const MetricTensor& gdown,
        const MetricTensor& gup);
    static bool sample_frame(
        const Frame& frame,
        const Position& x,
        const Location& location,
        State& state,
        const MetricTensor& gdown,
        const MetricTensor& gup);
    static bool sample_frames(
        const Frame& first,
        const Frame& second,
        double weight,
        const Position& x,
        const Location& location,
        State& state,
        const MetricTensor& gdown,
        const MetricTensor& gup);
};

} // namespace fluid::harmpi
