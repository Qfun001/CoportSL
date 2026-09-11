#include "BhacBackend.h"

#include <stdexcept>

#include "src/support/Signature.h"

namespace fluid::bhac {

void Backend::add_input_identity(
    support::Signature& signature,
    const std::filesystem::path& grid_file,
    const FrameInfo& first_frame) {

    if (first_frame.path.empty()) {
        throw std::invalid_argument(
            "BHAC input identity requires a first snapshot path.");
    }
    signature.add_string("Input::BACKEND", name());
    signature.add_file("Input::GRID_CONTENT", grid_file);
    signature.add_file("Input::FIRST_FRAME_CONTENT", first_frame.path);
}

} // namespace fluid::bhac
