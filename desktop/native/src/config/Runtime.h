#pragma once

#include <filesystem>
#include <string>

namespace runtime_config {

void load(const std::filesystem::path& path);
void validate();
std::string defaults_json();
std::string capabilities_json();
bool cancellation_requested();
void throw_if_cancelled();

} // namespace runtime_config
