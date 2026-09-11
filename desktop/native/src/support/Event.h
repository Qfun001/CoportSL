#pragma once

#include <filesystem>
#include <string_view>

namespace event {

void stage(std::string_view name);
void progress(int current, int total, int frame);
void result(const std::filesystem::path& path, bool reused);
void error(std::string_view message);

} // namespace event
