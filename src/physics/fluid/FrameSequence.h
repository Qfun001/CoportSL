#pragma once

#include <filesystem>
#include <span>
#include <vector>

#include "BackendTypes.h"

namespace fluid {

// A unique, authenticated sequence of snapshots from a production run. Source frame numbers can be sparse,
// But it must be uniquely incremented; dt is the minimum adjacent physical time interval.
struct FrameSequence {
    std::vector<FrameInfo> frames;
    double dt = 0.0; // Minimum neighbor separation, units defined by fluid backend.
    bool uniform = true; // Whether all adjacent intervals are equal within numerical tolerance.

    const FrameInfo& first() const;
    const FrameInfo& last() const;
};

// Sort by source frame number and verify that frame numbers are uniquely increasing, time-limited, and strictly increasing.
FrameSequence make_frame_sequence(std::vector<FrameInfo> frames);

// Snapshots are discovered by the Active Fluid backend and a verification timeline is established for reuse on a run.
FrameSequence discover_frame_sequence(
    const std::filesystem::path& data_directory);

// Sparse sampling according to physical time intervals; non-uniform time axis selection is no earlier than the first frame of each target moment,
// And always includes the first and last frame of the input.
std::vector<FrameInfo> sample_frames(
    const FrameSequence& sequence,
    double sample_dt);

// Sampling starts from the first frame in positive integer frame steps; unaligned last frames are not added additionally.
std::vector<FrameInfo> sample_frames_by_step(
    const FrameSequence& sequence,
    size_t frame_step);

// Only output frames are selected; negative bounds mean using the first or last frame of the available range, respectively.
std::vector<FrameInfo> select_frame_range(
    std::span<const FrameInfo> available,
    int frame_start,
    int frame_end);

// Returns a baseline snapshot supported by the input timeline at both ends of the window.
std::vector<FrameInfo> safe_base_frames(
    const FrameSequence& sequence,
    double window_left,
    double window_right);

} // namespace fluid
