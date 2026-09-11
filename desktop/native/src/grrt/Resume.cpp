#include "src/grrt/Resume.h"

#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <system_error>

namespace grrt::resume {

std::filesystem::path stokes_file(
    const std::filesystem::path& directory,
    char component,
    int frame) {

    std::ostringstream name;
    name << component << std::setw(4) << std::setfill('0') << frame << ".csv";
    return directory / name.str();
}

std::array<std::filesystem::path, 4> stokes_files(
    const std::filesystem::path& directory,
    int frame) {

    return {
        stokes_file(directory, 'I', frame),
        stokes_file(directory, 'Q', frame),
        stokes_file(directory, 'U', frame),
        stokes_file(directory, 'V', frame)
    };
}

void discard_frame(const std::filesystem::path& directory, int frame) {
    for (const std::filesystem::path& file : stokes_files(directory, frame)) {
        std::error_code error;
        std::filesystem::remove(file, error);
        if (error) {
            throw std::filesystem::filesystem_error(
                "Cannot remove incomplete Stokes frame", file, error);
        }
    }
}

} // namespace grrt::resume
