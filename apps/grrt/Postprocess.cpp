#include "apps/RunConfig.h"

#if COPORTSL_APP == COPORTSL_GRRT

#include "Postprocess.h"

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

#ifndef COPORTSL_SOURCE_ROOT
#define COPORTSL_SOURCE_ROOT "."
#endif

namespace grrt_app::postprocess {
namespace {

std::string quoted_path(const std::filesystem::path& path) {
    const std::string value = path.string();
    if (value.find('"') != std::string::npos) {
        throw std::invalid_argument(
            "Postprocess paths must not contain a double quote.");
    }
    return "\"" + value + "\"";
}

std::filesystem::path script_path(const char* name) {
    return std::filesystem::path(COPORTSL_SOURCE_ROOT) / "tools" / name;
}

} // namespace

void run(const std::filesystem::path& result) {
    if constexpr (!Postprocess::RUN) return;

    const std::filesystem::path output = result / "plot";
    std::filesystem::create_directories(output);
    const std::filesystem::path script = script_path("postprocess.py");
    const std::filesystem::path log = output / "postprocess.log";
    const std::string command =
        "python " + quoted_path(script) + " " + quoted_path(result) +
        " > " + quoted_path(log) + " 2>&1";
    std::cout << "Postprocess command: " << command << "\n";
    const int code = std::system(command.c_str());
    const std::filesystem::path status = output / "status.txt";
    if (code != 0) {
        std::ofstream(status) << "failed\n";
        std::cerr << "Warning: Python postprocess failed with code "
            << code << "; numerical result remains complete. See "
            << log << "\n";
        return;
    }
    std::ifstream input(status);
    std::string value;
    input >> value;
    if (value != "complete") {
        std::ofstream(status) << "failed\n";
        std::cerr << "Warning: Python postprocess returned without a complete "
            "plot status; numerical result remains complete. See "
            << log << "\n";
    }
}

void print_evpa_command(const std::filesystem::path& result) {
    std::cout << "Manual EVPA command: python "
        << quoted_path(script_path("evpa_plot.py"))
        << " " << quoted_path(result) << "\n";
}

} // namespace grrt_app::postprocess

#endif
