#include "HarmpiBackend.h"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <limits>
#include <optional>
#include <sstream>
#include <stdexcept>

#include "apps/RunConfig.h"
#include "Coordinates.h"
#include "src/physics/spacetime/Metric.h"

namespace fluid::harmpi {
namespace {

std::optional<Header> grid_header;
Frame active_frame;

void require_grid() {
    if (!grid_header.has_value()) {
        throw std::runtime_error("HARMPI grid has not been initialized.");
    }
}

void validate_grid(const Header& header) {
    require_grid();
    const Header& expected = *grid_header;
    if (header.global_size != expected.global_size ||
        header.start != expected.start ||
        header.cell_width != expected.cell_width ||
        header.spin != expected.spin ||
        header.adiabatic_index != expected.adiabatic_index ||
        header.hslope != expected.hslope ||
        header.radial_offset != expected.radial_offset ||
        header.radial_break != expected.radial_break ||
        header.radial_power != expected.radial_power ||
        header.radial_coefficient != expected.radial_coefficient ||
        header.coordinate_family != expected.coordinate_family ||
        header.cylindrified != expected.cylindrified) {
        throw std::runtime_error("HARMPI frame grid metadata changed.");
    }
}

} // namespace

void Backend::initialize_grid(
    const std::filesystem::path& first_frame,
    const std::filesystem::path&) {

    const Header header = inspect_frame(first_frame).header;
    // A complete verification of coordinate families and parameters is triggered via an internal unit.
    const Vector4 code = {
        header.time,
        header.start[0] + 0.5 * header.cell_width[0],
        header.start[1] + 0.5 * header.cell_width[1],
        header.start[2] + 0.5 * header.cell_width[2]};
    static_cast<void>(physical_coordinates(header, code));
    SetKerrSchildMetric(header.spin);
    grid_header = header;
    active_frame = Frame{};
}

double Backend::frame_time(const std::filesystem::path& frame_file) {
    return inspect_frame(frame_file).header.time;
}

std::filesystem::path Backend::frame_path(
    const std::filesystem::path& data_dir,
    int index) {

    std::ostringstream name;
    name << "dump-" << std::setw(2) << std::setfill('0') << index;
    return data_dir / name.str();
}

std::vector<FrameInfo> Backend::discover_frames(
    const std::filesystem::path& data_dir) {

    return harmpi::discover_frames(data_dir);
}

void Backend::load_active_frame(const std::filesystem::path& frame_file) {
    active_frame = load_frame(frame_file);
}

Backend::Frame Backend::load_frame(
    const std::filesystem::path& frame_file) {

    Frame frame = harmpi::load_frame(frame_file);
    validate_grid(frame.metadata.header);
    return frame;
}

GridStats Backend::grid_stats() {
    require_grid();
    GridStats stats;
    stats.leaf_blocks = 1;
    for (size_t axis = 0; axis < 3; axis++) {
        stats.cells_per_block_axis[axis] = static_cast<size_t>(
            grid_header->global_size[axis]);
    }
    stats.cells_per_block = static_cast<size_t>(
        static_cast<uint64_t>(grid_header->global_size[0]) *
        static_cast<uint64_t>(grid_header->global_size[1]) *
        static_cast<uint64_t>(grid_header->global_size[2]));
    stats.active_cells = stats.cells_per_block;
    stats.primitive_values = stats.active_cells * 10;
    stats.resident_bytes = stats.active_cells * sizeof(RadiationCell);
    return stats;
}

bool Backend::probe_grid(
    const Position& x,
    const WaveVector& k,
    uint64_t& hint,
    double& max_step) {

    require_grid();
    Vector4 code = {};
    if (!code_coordinates(*grid_header, x, code)) return false;
    const Matrix4 jacobian = coordinate_jacobian(*grid_header, code);
    max_step = std::numeric_limits<double>::infinity();
    for (size_t axis = 0; axis < 3; axis++) {
        const double k_code = k[axis + 1] /
            jacobian[axis + 1][axis + 1];
        if (k_code != 0.0) {
            max_step = std::min(
                max_step,
                std::abs(grid_header->cell_width[axis] / k_code));
        }
    }
    hint = 0;
    max_step *= Config::RAY_CELL;
    return std::isfinite(max_step) && max_step > 0.0;
}

bool Backend::locate(
    const Position& x,
    uint64_t& hint,
    Location& location) {

    require_grid();
    hint = 0;
    return harmpi::locate(*grid_header, x, location);
}

bool Backend::sample_active(
    const Position& x,
    const Location& location,
    State& state,
    const MetricTensor& gdown,
    const MetricTensor&) {

    if (active_frame.cells.empty()) {
        throw std::runtime_error("HARMPI active frame has not been loaded.");
    }
    return sample_state(active_frame, x, location, gdown, state);
}

bool Backend::sample_frame(
    const Frame& frame,
    const Position& x,
    const Location& location,
    State& state,
    const MetricTensor& gdown,
    const MetricTensor&) {

    return sample_state(frame, x, location, gdown, state);
}

bool Backend::sample_frames(
    const Frame& first,
    const Frame& second,
    double weight,
    const Position& x,
    const Location& location,
    State& state,
    const MetricTensor& gdown,
    const MetricTensor&) {

    return sample_frames_state(
        first, second, weight, x, location, gdown, state);
}

} // namespace fluid::harmpi
