#include "Event.h"

#include <iostream>
#include <string>

#include "third_party/nlohmann/json.hpp"

namespace event {
namespace {

void write(const nlohmann::json& value) {
    std::cout << "COPORTSL_EVENT " << value.dump() << "\n";
    std::cout.flush();
}

std::string path_text(const std::filesystem::path& path) {
    const std::u8string value = path.generic_u8string();
    return std::string(
        reinterpret_cast<const char*>(value.data()), value.size());
}

} // namespace

void stage(std::string_view name) {
    write({{"type", "stage"}, {"name", name}});
}

void progress(int current, int total, int frame) {
    write({
        {"type", "progress"},
        {"current", current},
        {"total", total},
        {"frame", frame}
    });
}

void result(const std::filesystem::path& path, bool reused) {
    write({
        {"type", "result"},
        {"path", path_text(path)},
        {"reused", reused}
    });
}

void error(std::string_view message) {
    write({{"type", "error"}, {"message", message}});
}

} // namespace event
