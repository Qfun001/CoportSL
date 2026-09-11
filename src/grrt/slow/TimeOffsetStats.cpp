#include "TimeOffsetStats.h"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <utility>

namespace slow_light {
namespace {

// The shortest interval covering exactly count consecutive sorted sample points; the smaller left endpoint is used for the same width.
CoverageWindow shortest_window_from_sorted(
    const CoverageWindowRequest& request,
    const std::vector<double>& sorted) {

    const size_t count = static_cast<size_t>(
        std::ceil(request.probability * static_cast<double>(sorted.size())));

    double best_left = 0.0;
    double best_right = 0.0;
    double best_width = std::numeric_limits<double>::infinity();
    for (size_t begin = 0; begin + count <= sorted.size(); begin++) {
        const double left = sorted[begin];
        const double right = sorted[begin + count - 1];
        const double width = right - left;
        if (width < best_width ||
            (width == best_width && left < best_left)) {
            best_left = left;
            best_right = right;
            best_width = width;
        }
    }
    if (!std::isfinite(best_width)) {
        throw std::runtime_error(
            "No coverage window reaches the requested sample count.");
    }
    return {request.name, best_left, best_right};
}

} // namespace

std::vector<CoverageWindow> shortest_coverage_windows(
    const std::vector<CoverageWindowRequest>& requests,
    const std::vector<double>& offsets) {

    if (offsets.empty()) {
        throw std::invalid_argument(
            "Coverage window requires at least one time offset.");
    }
    for (const CoverageWindowRequest& request : requests) {
        if (!(request.probability > 0.0 && request.probability <= 1.0) ||
            !std::isfinite(request.probability)) {
            throw std::invalid_argument(
                "Coverage probability must satisfy 0 < q <= 1.");
        }
    }

    std::vector<double> sorted = offsets;
    for (double value : sorted) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                "Coverage time offsets must be finite.");
        }
    }
    std::sort(sorted.begin(), sorted.end());

    std::vector<CoverageWindow> result;
    result.reserve(requests.size());
    for (const CoverageWindowRequest& request : requests) {
        result.push_back(shortest_window_from_sorted(request, sorted));
    }
    return result;
}

CoverageWindow shortest_coverage_window(
    std::string name,
    double probability,
    const std::vector<double>& offsets) {

    std::vector<CoverageWindowRequest> requests;
    requests.push_back({std::move(name), probability});
    auto result = shortest_coverage_windows(requests, offsets);
    return std::move(result.front());
}

} // namespace slow_light
