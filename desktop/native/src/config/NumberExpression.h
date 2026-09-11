#pragma once

#include <string_view>

namespace runtime_config {

// Parse finite real expressions in configuration; allow only pi, parentheses, and basic arithmetic operators.
double evaluate_number_expression(std::string_view expression);

} // namespace runtime_config
