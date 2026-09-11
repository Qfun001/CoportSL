#pragma once

#include <filesystem>

namespace grrt_app::postprocess {

void run(const std::filesystem::path& result);
void print_evpa_command(const std::filesystem::path& result);

} // namespace grrt_app::postprocess
