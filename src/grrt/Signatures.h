#pragma once

#include <filesystem>
#include <string>

#include "src/physics/fluid/FrameSequence.h"

namespace grrt {

struct Signatures {
    std::string input;
    std::string model;
    std::string analysis;
};

// According to the immutable GRMHD evolution data set convention, only the grid and the first frame content are read; subsequent consecutive frames are not hashed frame by frame.
// To avoid sequentially reading the entire large snapshot every time it is started. When the data production process changes, it must be rerun using a new data set.
Signatures make_signatures(const fluid::FrameSequence& sequence);
Signatures make_signatures(
    const fluid::FrameSequence& sequence,
    const std::filesystem::path& grid_file);

} // namespace grrt
