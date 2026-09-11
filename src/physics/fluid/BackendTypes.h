#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <vector>

namespace fluid {

using Position = std::array<double, 4>;
using WaveVector = std::array<double, 4>;

struct GridStats {
    size_t leaf_blocks = 0;
    std::array<size_t, 3> cells_per_block_axis = {};
    size_t cells_per_block = 0;
    size_t active_cells = 0;
    size_t primitive_values = 0;
    size_t resident_bytes = 0;
};

struct FrameInfo {
    int index = 0;
    std::filesystem::path path;
    double time = 0.0;
};

// Returns whether the position is within the active grid, given the maximum affine step allowed by the local grid.
using GridProbe = bool (*)(
    const Position& x,
    const WaveVector& k,
    uint64_t& hint,
    double& max_step);

} // namespace fluid
