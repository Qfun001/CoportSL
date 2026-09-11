#include "FrameSequence.h"

#include <filesystem>
#include <stdexcept>
#include <utility>

#include "FluidBackend.h"

namespace fluid {

FrameSequence discover_frame_sequence(
    const std::filesystem::path& data_directory) {

    std::vector<FrameInfo> frames = Backend::discover_frames(data_directory);
    for (const FrameInfo& frame : frames) {
        std::error_code error;
        if (!std::filesystem::is_regular_file(frame.path, error) || error) {
            throw std::runtime_error(
                "Discovered GRMHD frame is not a readable regular file: " +
                frame.path.string());
        }
    }
    return make_frame_sequence(std::move(frames));
}

} // namespace fluid
