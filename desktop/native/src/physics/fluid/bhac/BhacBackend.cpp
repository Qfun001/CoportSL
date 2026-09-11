#include "src/physics/fluid/bhac/BhacBackend.h"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <string>

#include "apps/RunConfig.h"
#include "Reader.h"

namespace fluid::bhac {

namespace {

BhacStencil to_stencil(const Location& location) {
    BhacStencil stencil = {};
    stencil.igrid = static_cast<int>(location.block);
    stencil.cell = static_cast<int>(location.cell);
    for (int i = 0; i < 3; i++) {
        stencil.del[i] = static_cast<double>(location.weight[static_cast<size_t>(i)]);
        stencil.dx_local[i] = block_info[stencil.igrid].dxc_block[i];
    }
    return stencil;
}

Location from_stencil(const BhacStencil& stencil) {
    Location location;
    location.block = static_cast<uint32_t>(stencil.igrid);
    location.cell = static_cast<uint32_t>(stencil.cell);
    for (int i = 0; i < 3; i++) {
        location.weight[static_cast<size_t>(i)] = static_cast<float>(stencil.del[i]);
    }
    return location;
}

std::array<double, NPRIM> interpolate_frame(
    const Frame& frame,
    const BhacStencil& stencil) {

    if (frame.primitive.size() != grmhd_primitive_count()) {
        throw std::invalid_argument("BHAC frame payload has an unexpected size.");
    }
    std::array<double, NPRIM> primitive = {};
    interpolate_grmhd_primitives(frame.primitive.data(), stencil, primitive);
    return primitive;
}

} // namespace

void Backend::initialize_grid(
    const std::filesystem::path& first_frame,
    const std::filesystem::path& grid_file) {

    std::string frame = first_frame.string();
    std::string grid = grid_file.string();
    init_grmhd_grid(frame.data(), grid.data());
}

double Backend::frame_time(const std::filesystem::path& frame_file) {
    return read_grmhd_time(frame_file.string().c_str());
}

std::filesystem::path Backend::frame_path(
    const std::filesystem::path& data_dir,
    int index) {

    std::ostringstream name;
    name << "data" << std::setw(4) << std::setfill('0') << index << ".dat";
    return data_dir / name.str();
}

std::vector<FrameInfo> Backend::discover_frames(
    const std::filesystem::path& data_dir) {

    std::vector<FrameInfo> frames;
    for (const auto& entry : std::filesystem::directory_iterator(data_dir)) {
        if (!entry.is_regular_file() || entry.path().extension() != ".dat") continue;
        const std::string stem = entry.path().stem().string();
        if (!stem.starts_with("data") || stem.size() <= 4) continue;
        const std::string suffix = stem.substr(4);
        if (!std::all_of(suffix.begin(), suffix.end(), [](unsigned char value) {
            return std::isdigit(value) != 0;
        })) continue;
        frames.push_back({
            std::stoi(suffix),
            entry.path(),
            frame_time(entry.path())
        });
    }
    std::sort(frames.begin(), frames.end(), [](const FrameInfo& a, const FrameInfo& b) {
        return a.index < b.index;
    });
    return frames;
}

void Backend::load_active_frame(const std::filesystem::path& frame_file) {
    std::string frame = frame_file.string();
    load_grmhd_frame(frame.data());
}

Backend::Frame Backend::load_frame(const std::filesystem::path& frame_file) {
    load_active_frame(frame_file);
    Frame frame;
    frame.primitive.resize(frame_value_count());
    const FloatCopyError error = copy_grmhd_primitives(frame.primitive.data());
    frame.max_float_absolute_error = error.max_absolute;
    frame.max_float_relative_error = error.max_relative;
    return frame;
}

size_t Backend::frame_value_count() {
    return grmhd_primitive_count();
}

GridStats Backend::grid_stats() {
    const GrmhdGridStats source = grmhd_grid_stats();
    GridStats result;
    result.leaf_blocks = source.leaf_blocks;
    result.cells_per_block_axis = source.cells_per_block_axis;
    result.cells_per_block = source.cells_per_block;
    result.active_cells = source.active_cells;
    result.primitive_values = source.primitive_values;
    result.resident_bytes =
        source.primitive_values * sizeof(double) +
        source.active_cells * 3 * sizeof(double) * 2 +
        source.leaf_blocks * sizeof(block);
    return result;
}

bool Backend::probe_grid(
    const Position& x,
    const WaveVector& k,
    uint64_t& hint,
    double& max_step) {

    BhacStencil stencil = {};
    if (!get_fluid_stencil(x, static_cast<int>(hint), stencil)) return false;
    hint = static_cast<uint64_t>(stencil.igrid);
    max_step = Config::RAY_CELL * std::min({
        std::abs(stencil.dx_local[0] / k[1]),
        std::abs(stencil.dx_local[1] / k[2]),
        std::abs(stencil.dx_local[2] / k[3])
    });
    return true;
}

bool Backend::locate(const Position& x, uint64_t& hint, Location& location) {
    BhacStencil stencil = {};
    if (!get_fluid_stencil(x, static_cast<int>(hint), stencil)) return false;
    hint = static_cast<uint64_t>(stencil.igrid);
    location = from_stencil(stencil);
    return true;
}

bool Backend::sample_active(
    const Position& x,
    const Location& location,
    State& state,
    const MetricTensor& gdown,
    const MetricTensor& gup) {

    return get_fluid_params_cached(
        x, to_stencil(location), &state, gdown, gup) != 0;
}

bool Backend::sample_frame(
    const Frame& frame,
    const Position& x,
    const Location& location,
    State& state,
    const MetricTensor& gdown,
    const MetricTensor& gup) {

    const BhacStencil stencil = to_stencil(location);
    const auto primitive = interpolate_frame(frame, stencil);
    return get_fluid_params_from_primitives(
        x, stencil, primitive, &state, gdown, gup) != 0;
}

bool Backend::sample_frames(
    const Frame& first,
    const Frame& second,
    double weight,
    const Position& x,
    const Location& location,
    State& state,
    const MetricTensor& gdown,
    const MetricTensor& gup) {

    const BhacStencil stencil = to_stencil(location);
    auto primitive = interpolate_frame(first, stencil);
    const auto next = interpolate_frame(second, stencil);
    weight = std::clamp(weight, 0.0, 1.0);
    for (int variable = 0; variable < NPRIM; variable++) {
        primitive[static_cast<size_t>(variable)] =
            primitive[static_cast<size_t>(variable)] * (1.0 - weight) +
            next[static_cast<size_t>(variable)] * weight;
    }
    return get_fluid_params_from_primitives(
        x, stencil, primitive, &state, gdown, gup) != 0;
}

} // namespace fluid::bhac
