#include "ConfigCompatibility.h"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <fstream>
#include <limits>

namespace grrt {
namespace {

template <typename T>
bool parse_integer(std::string_view text, T& value) {
    const char* begin = text.data();
    const char* end = begin + text.size();
    const auto [position, error] = std::from_chars(begin, end, value);
    return error == std::errc{} && position == end;
}

bool parse_double(std::string_view text, double& value) {
    const char* begin = text.data();
    const char* end = begin + text.size();
    const auto [position, error] = std::from_chars(begin, end, value);
    return error == std::errc{} && position == end && std::isfinite(value);
}

bool close_relative(double actual, double expected, double tolerance) {
    if (actual == expected) return true;
    return std::abs(actual - expected) <=
        tolerance * std::max(std::abs(actual), std::abs(expected));
}

} // namespace

bool is_sha256(std::string_view value) {
    if (value.size() != 64) return false;
    for (const char character : value) {
        if (!((character >= '0' && character <= '9') ||
            (character >= 'a' && character <= 'f'))) {
            return false;
        }
    }
    return true;
}

bool read_config_values(
    const std::filesystem::path& path,
    ConfigValues& values) {

    values.clear();
    std::ifstream input(path);
    if (!input) return false;
    std::string line;
    while (std::getline(input, line)) {
        const size_t separator = line.find('=');
        if (separator == std::string::npos || separator == 0) return false;
        std::string name = line.substr(0, separator);
        std::string value = line.substr(separator + 1);
        if (!values.emplace(std::move(name), std::move(value)).second) {
            return false;
        }
    }
    return input.eof() && !values.empty();
}

ConfigComparison compare_config_values(
    const ConfigValues& actual,
    std::span<const ConfigFieldExpectation> expected,
    double relative_tolerance) {

    ConfigComparison result;
    if (!std::isfinite(relative_tolerance) || relative_tolerance < 0.0) {
        result.different_fields.push_back("relative_tolerance");
        return result;
    }
    for (const ConfigFieldExpectation& field : expected) {
        const auto item = actual.find(field.name);
        if (item == actual.end()) {
            result.different_fields.push_back(field.name);
            continue;
        }
        const std::string_view value = item->second;
        bool same = false;
        switch (field.kind) {
        case ConfigValueKind::Text:
            same = value == field.value;
            break;
        case ConfigValueKind::Integer: {
            int64_t actual_value = 0;
            int64_t expected_value = 0;
            same = parse_integer(value, actual_value) &&
                parse_integer(field.value, expected_value) &&
                actual_value == expected_value;
            break;
        }
        case ConfigValueKind::Floating: {
            double actual_value = 0.0;
            double expected_value = 0.0;
            if (parse_double(value, actual_value) &&
                parse_double(field.value, expected_value)) {
                if (actual_value == expected_value) {
                    same = true;
                }
                else if (close_relative(
                    actual_value, expected_value, relative_tolerance)) {
                    same = true;
                    result.approximate_fields.push_back(field.name);
                }
            }
            break;
        }
        case ConfigValueKind::Sha256:
            same = is_sha256(value) && is_sha256(field.value) &&
                value == field.value;
            break;
        }
        if (!same) result.different_fields.push_back(field.name);
    }
    result.compatible = result.different_fields.empty();
    return result;
}

std::string config_double(double value) {
    char buffer[64] = {};
    const auto [position, error] = std::to_chars(
        buffer,
        buffer + sizeof(buffer),
        value,
        std::chars_format::general,
        std::numeric_limits<double>::max_digits10);
    if (error != std::errc{}) return {};
    return std::string(buffer, position);
}

} // namespace grrt
