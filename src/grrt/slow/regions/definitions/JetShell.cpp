#include "JetShell.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <iomanip>
#include <numbers>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string_view>
#include <vector>

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

std::string region_key(std::string_view group, size_t index) {
    std::ostringstream text;
    text << group << "_" << std::setw(3) << std::setfill('0') << index;
    return text.str();
}

void validate_edges(std::span<const double> edges, std::string_view group) {
    if (edges.size() < 2) {
        throw std::invalid_argument(
            std::string(group) + " partition requires at least two edges.");
    }
    for (size_t i = 0; i < edges.size(); i++) {
        if (!std::isfinite(edges[i])) {
            throw std::invalid_argument(
                std::string(group) + " partition edges must be finite.");
        }
        if (i > 0 && !(edges[i] > edges[i - 1])) {
            throw std::invalid_argument(
                std::string(group) + " partition edges must be strictly increasing.");
        }
    }
}

void append_regions(
    std::vector<RegionInfo>& regions,
    std::string_view key_group,
    std::string_view label_group,
    std::span<const double> edges) {

    for (size_t i = 0; i + 1 < edges.size(); i++) {
        regions.push_back({
            region_key(key_group, i),
            std::string(label_group) + ", " + compact_value(edges[i]) +
                " <= r < " + compact_value(edges[i + 1]) + " rg"
        });
    }
}

std::optional<RegionId> radial_region(
    double radius,
    const std::vector<double>& edges,
    RegionId offset) {

    const auto upper = std::upper_bound(edges.begin(), edges.end(), radius);
    if (upper == edges.begin()) {
        return std::nullopt;
    }
    if (upper == edges.end()) {
        // The ray cache compresses coordinates to float; inverse transform rounding errors at outermost boundaries are allowed.
        const double tolerance = 8.0 * std::numeric_limits<float>::epsilon() *
            std::max(1.0, std::abs(edges.back()));
        if (radius <= edges.back() + tolerance) {
            return offset + static_cast<RegionId>(edges.size() - 2);
        }
        return std::nullopt;
    }
    return offset + static_cast<RegionId>(upper - edges.begin() - 1);
}

void append_signature_edges(
    std::ostringstream& signature,
    std::string_view name,
    std::span<const double> edges) {

    signature << ";" << name << "=";
    for (size_t i = 0; i < edges.size(); i++) {
        if (i > 0) signature << ",";
        signature << edges[i];
    }
}

} // namespace

RegionDefinition make_jet_shells(
    double jet_half_angle,
    std::span<const double> jet_edges,
    std::span<const double> non_jet_edges) {

    if (!std::isfinite(jet_half_angle) ||
        !(jet_half_angle > 0.0 && jet_half_angle < std::numbers::pi / 2.0)) {
        throw std::invalid_argument(
            "Jet half angle must be finite and lie between zero and pi/2.");
    }
    validate_edges(jet_edges, "Jet-shell jet");
    validate_edges(non_jet_edges, "Jet-shell non-jet");

    const std::vector<double> stored_jet_edges(jet_edges.begin(), jet_edges.end());
    const std::vector<double> stored_non_jet_edges(
        non_jet_edges.begin(), non_jet_edges.end());
    const RegionId jet_region_count =
        static_cast<RegionId>(stored_jet_edges.size() - 1);
    const RegionId non_jet_offset = 2 * jet_region_count;

    RegionDefinition definition;
    definition.name = "jet_shell";
    std::ostringstream signature;
    signature << std::setprecision(17) << "jet_half_angle=" << jet_half_angle;
    append_signature_edges(signature, "jet_edges", stored_jet_edges);
    append_signature_edges(signature, "non_jet_edges", stored_non_jet_edges);
    definition.signature = signature.str();

    definition.regions.reserve(
        2 * jet_region_count + stored_non_jet_edges.size() - 1);
    append_regions(definition.regions, "north", "north jet", stored_jet_edges);
    append_regions(definition.regions, "south", "south jet", stored_jet_edges);
    append_regions(definition.regions, "non_jet", "non_jet", stored_non_jet_edges);

    definition.locate = [
        jet_half_angle,
        stored_jet_edges,
        stored_non_jet_edges,
        jet_region_count,
        non_jet_offset](const Position& position) -> std::optional<RegionId> {

        const double radius = get_radial_radius(position);
        const double theta = get_polar_angle(position);
        if (!std::isfinite(radius) || !std::isfinite(theta)) {
            return std::nullopt;
        }
        if (theta < jet_half_angle) {
            return radial_region(radius, stored_jet_edges, 0);
        }
        if (theta > std::numbers::pi - jet_half_angle) {
            return radial_region(radius, stored_jet_edges, jet_region_count);
        }
        return radial_region(radius, stored_non_jet_edges, non_jet_offset);
    };
    return definition;
}

} // namespace slow_light::regions

namespace slow_light::regions::jet_shell {

namespace {

constexpr double jet_half_angle = std::numbers::pi / 8.0;
constexpr std::array jet_edges = {
    0.0, 50.0, 100.0, 120.0, 150.0, 180.0, 200.0
};
constexpr std::array non_jet_edges = {
    0.0, 20.0, 30.0, 50.0, 80.0, 100.0, 200.0
};

} // namespace

const RegionDefinition& source() {
    static const RegionDefinition definition = make_jet_shells(
        jet_half_angle, jet_edges, non_jet_edges);
    return definition;
}

} // namespace slow_light::regions::jet_shell
