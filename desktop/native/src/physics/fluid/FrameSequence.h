#pragma once

#include <cstddef>
#include <filesystem>
#include <vector>

#include "src/physics/fluid/BackendTypes.h"

namespace fluid {

// A unique, validated sequence of equally spaced snapshots from a production run.
struct FrameSequence {
    std::vector<FrameInfo> frames;
    double dt = 0.0; // The physical time interval between adjacent snapshots, in units defined by the fluid backend.

    const FrameInfo& first() const;
    const FrameInfo& last() const;
};

// Sort by logical frame number and verify that frame numbers are continuous, time-limited, and strictly equally spaced.
FrameSequence make_frame_sequence(std::vector<FrameInfo> frames);

// Snapshots are discovered by the Active Fluid backend and a verification timeline is established for reuse on a run.
FrameSequence discover_frame_sequence(
    const std::filesystem::path& data_directory);

// Sparse sampling at physical intervals; always includes the first and last frames of the input.
std::vector<FrameInfo> sample_frames(
    const FrameSequence& sequence,
    double sample_dt);

std::vector<FrameInfo> sample_frames_by_step(
    const FrameSequence& sequence,
    size_t frame_step);

// Returns a baseline snapshot supported by the input timeline at both ends of the window.
std::vector<FrameInfo> safe_base_frames(
    const FrameSequence& sequence,
    double window_left,
    double window_right);

} // namespace fluid
