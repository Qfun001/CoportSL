#pragma once

#include <array>
#include <filesystem>

namespace grrt::resume {

std::filesystem::path stokes_file(
    const std::filesystem::path& directory,
    char component,
    int frame);

std::array<std::filesystem::path, 4> stokes_files(
    const std::filesystem::path& directory,
    int frame);

// Clear all old components of a frame before writing it to avoid mixing in legacy CSV after failure.
void discard_frame(const std::filesystem::path& directory, int frame);

} // namespace grrt::resume
