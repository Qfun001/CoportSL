#pragma once

#include <array>
#include <cstdint>
#include <filesystem>
#include <vector>

#include "../BackendTypes.h"

namespace fluid::harmpi {

struct Header {
    size_t fields = 0;
    double time = 0.0;
    std::array<int, 3> local_size = {};
    std::array<int, 3> global_size = {};
    std::array<int, 3> ghost_size = {};
    std::array<double, 3> start = {};
    std::array<double, 3> cell_width = {};
    double final_time = 0.0;
    int64_t step = 0;
    double spin = 0.0;
    double adiabatic_index = 0.0;
    double inner_radius = 0.0;
    double outer_radius = 0.0;
    double hslope = 0.0;
    double radial_offset = 0.0;
    int primitive_count = 0;
    bool entropy = false;
    bool cylindrified = false;
    double theta_fraction = 0.0;
    double phi_fraction = 0.0;
    double radial_break = 0.0;
    double radial_power = 0.0;
    double radial_coefficient = 0.0;
    double x1_transition = 0.0;
    double x2_transition = 0.0;
    int coordinate_family = 0;
};

struct FrameMetadata {
    Header header;
    uint64_t header_bytes = 0;
    uint64_t file_bytes = 0;
    uint64_t cells = 0;
    size_t body_fields = 0;
};

// Only the native fluid volume required for radiative transfer is retained, and the components remain in the HARMPI calculated coordinates.
struct RadiationCell {
    float rho = 0.0f;
    float internal_energy = 0.0f;
    std::array<float, 4> u_code = {};
    std::array<float, 4> b_code = {};
};

struct Frame {
    FrameMetadata metadata;
    std::vector<RadiationCell> cells;
    double max_float_absolute_error = 0.0;
    double max_float_relative_error = 0.0;

    size_t bytes() const { return cells.size() * sizeof(RadiationCell); }
};

FrameMetadata inspect_frame(const std::filesystem::path& path);

Frame load_frame(const std::filesystem::path& path);

uint64_t cell_index(
    const Header& header,
    int i,
    int j,
    int k);

std::vector<FrameInfo> discover_frames(
    const std::filesystem::path& data_directory);

} // namespace fluid::harmpi
