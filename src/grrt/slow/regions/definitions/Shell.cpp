#include "Shell.h"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>

#include "src/physics/spacetime/Metric.h"

namespace slow_light::regions {

namespace {

std::string compact_value(double value) {
    std::ostringstream text;
    text << std::defaultfloat << std::setprecision(6) << value;
    std::string result = text.str();
    std::replace(result.begin(), result.end(), '.', 'p');
    return result;
}

std::string region_key(size_t index) {
    std::ostringstream text;
    text << "region_" << std::setw(3) << std::setfill('0') << index;
    return text.str();
}

} // namespace

RegionDefinition make_shells(std::span<const double> edges) {
    if (edges.size() < 2) {
        throw std::invalid_argument("Shell partition requires at least two edges.");
    }
    for (size_t i = 0; i < edges.size(); i++) {
        if (!std::isfinite(edges[i])) {
            throw std::invalid_argument("Shell partition edges must be finite.");
        }
        if (i > 0 && !(edges[i] > edges[i - 1])) {
            throw std::invalid_argument(
                "Shell partition edges must be strictly increasing.");
        }
    }

    const std::vector<double> stored_edges(edges.begin(), edges.end());
    RegionDefinition definition;
    definition.name = "shell";
    std::ostringstream signature;
    signature << std::setprecision(17);
    for (size_t i = 0; i < stored_edges.size(); i++) {
        if (i > 0) signature << ",";
        signature << stored_edges[i];
    }
    definition.signature = signature.str();
    definition.regions.reserve(stored_edges.size() - 1);
    for (size_t i = 0; i + 1 < stored_edges.size(); i++) {
        definition.regions.push_back({
            region_key(i),
            compact_value(stored_edges[i]) + " <= r < " +
                compact_value(stored_edges[i + 1]) + " rg"
        });
    }
    definition.locate = [stored_edges](const Position& position)
        -> std::optional<RegionId> {
        const double radius = get_radial_radius(position);
        const auto upper = std::upper_bound(
            stored_edges.begin(), stored_edges.end(), radius);
        if (upper == stored_edges.begin()) {
            return std::nullopt;
        }
        if (upper == stored_edges.end()) {
            // The ray cache compresses coordinates to float; inverse transform rounding errors at outermost boundaries are allowed.
            const double tolerance = 8.0 * std::numeric_limits<float>::epsilon() *
                std::max(1.0, std::abs(stored_edges.back()));
            if (radius <= stored_edges.back() + tolerance) {
                return static_cast<RegionId>(stored_edges.size() - 2);
            }
            return std::nullopt;
        }
        return static_cast<RegionId>(upper - stored_edges.begin() - 1);
    };
    return definition;
}

} // namespace slow_light::regions

namespace slow_light::regions::shell {

namespace {

constexpr std::array edges = {
    0.0, 20.0, 30.0, 50.0, 80.0, 100.0, 200.0
};

} // namespace

const RegionDefinition& source() {
    static const RegionDefinition definition = make_shells(edges);
    return definition;
}

} // namespace slow_light::regions::shell
