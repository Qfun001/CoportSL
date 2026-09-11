#pragma once

#include <string>
#include <vector>

namespace slow_light {

struct CoverageWindow {
    std::string name;
    double left = 0.0;
    double right = 0.0;
};

struct CoverageWindowRequest {
    std::string name;
    double probability = 0.0;
};

std::vector<CoverageWindow> shortest_coverage_windows(
    const std::vector<CoverageWindowRequest>& requests,
    const std::vector<double>& offsets);

CoverageWindow shortest_coverage_window(
    std::string name,
    double probability,
    const std::vector<double>& offsets);

} // namespace slow_light
