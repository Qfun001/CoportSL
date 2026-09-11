#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <vector>

#include "../BackendTypes.h"
#include "../State.h"

namespace support {
class Signature;
}

namespace fluid::bhac {

struct Location {
    uint32_t block = 0;
    uint32_t cell = 0;
    std::array<float, 3> weight = {};
};

struct Frame {
    std::vector<float> primitive;
    double max_float_absolute_error = 0.0;
    double max_float_relative_error = 0.0;

    size_t bytes() const { return primitive.size() * sizeof(float); }
};

class Backend {
public:
    using Location = bhac::Location;
    using Frame = bhac::Frame;

    static constexpr const char* name() { return "bhac"; }

    static void initialize_grid(
        const std::filesystem::path& first_frame,
        const std::filesystem::path& grid_file);
    static double frame_time(const std::filesystem::path& frame_file);
    static std::filesystem::path frame_path(
        const std::filesystem::path& data_dir,
        int index);
    static std::vector<FrameInfo> discover_frames(
        const std::filesystem::path& data_dir);
    static void add_input_identity(
        support::Signature& signature,
        const std::filesystem::path& grid_file,
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

private:
    static size_t frame_value_count();
};

} // namespace fluid::bhac
