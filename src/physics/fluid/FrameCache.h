#pragma once

#include <array>
#include <cstddef>
#include <filesystem>
#include <vector>

#include "FluidBackend.h"
#include "FrameSequence.h"

namespace fluid {

// Sliding fluid buffer for continuous slow-light time windows; internal slots are synchronized with the time array.
class FrameCache {
public:
    static FrameCache load(
        const FrameSequence& sequence,
        const FrameInfo& first_base,
        double time_offset_min,
        double time_offset_max);

    void advance(double base_time);

    bool sample(
        double time,
        bool fixed_frame,
        const std::array<double, 4>& x,
        const Backend::Location& location,
        State& state,
        const std::array<std::array<double, 4>, 4>& gdown,
        const std::array<std::array<double, 4>, 4>& gup) const;

    size_t bytes() const;
    size_t frame_count() const noexcept;
    double base_time() const noexcept;

private:
    FrameCache() = default;

    std::vector<double> times_;
    std::vector<size_t> slots_;
    std::vector<Backend::Frame> frame_slots_;
    std::vector<std::filesystem::path> pending_paths_;
    std::vector<double> pending_times_;
    std::vector<size_t> free_slots_;
    Backend::Frame base_frame_;
    size_t base_frame_index_ = 0;
    size_t next_frame_ = 0;
    double base_time_ = 0.0;
    double time_offset_min_ = 0.0;
    double time_offset_max_ = 0.0;
    double requested_begin_ = 0.0;
    double requested_end_ = 0.0;
    double available_begin_ = 0.0;
    double available_end_ = 0.0;
    double max_float_absolute_error_ = 0.0;
    double max_float_relative_error_ = 0.0;
};

} // namespace fluid
