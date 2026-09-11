#pragma once

#include <filesystem>
#include <map>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace grrt {

enum class ConfigValueKind {
    Text,
    Integer,
    Floating,
    Sha256
};

struct ConfigFieldExpectation {
    std::string name;
    std::string value;
    ConfigValueKind kind = ConfigValueKind::Text;
};

struct ConfigComparison {
    bool compatible = false;
    std::vector<std::string> approximate_fields;
    std::vector<std::string> different_fields;
};

using ConfigValues = std::map<std::string, std::string, std::less<>>;

bool is_sha256(std::string_view value);

bool read_config_values(
    const std::filesystem::path& path,
    ConfigValues& values);

ConfigComparison compare_config_values(
    const ConfigValues& actual,
    std::span<const ConfigFieldExpectation> expected,
    double relative_tolerance = 1.0e-11);

std::string config_double(double value);

} // namespace grrt
