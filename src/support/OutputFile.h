#pragma once

#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>
#include <string_view>

namespace output_file {

inline void close(
    std::ofstream& out,
    const std::filesystem::path& file,
    std::string_view description) {

    out.close();
    if (!out) {
        throw std::runtime_error(
            "Cannot finish " + std::string(description) + ": " +
            file.string());
    }
}

} // namespace output_file
