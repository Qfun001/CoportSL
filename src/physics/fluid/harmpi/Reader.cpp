#include "Reader.h"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <limits>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>

namespace fluid::harmpi {
namespace {

template <typename Type>
Type parse_number(
    const std::vector<std::string>& tokens,
    size_t index,
    const char* name) {

    if (index >= tokens.size()) {
        throw std::runtime_error(
            std::string("Missing HARMPI header field: ") + name + ".");
    }
    size_t consumed = 0;
    try {
        if constexpr (std::is_integral_v<Type>) {
            const long long value = std::stoll(tokens[index], &consumed);
            if (value < static_cast<long long>(std::numeric_limits<Type>::min()) ||
                value > static_cast<long long>(std::numeric_limits<Type>::max())) {
                throw std::out_of_range("integer range");
            }
            if (consumed != tokens[index].size()) throw std::invalid_argument("suffix");
            return static_cast<Type>(value);
        }
        else {
            const double value = std::stod(tokens[index], &consumed);
            if (consumed != tokens[index].size() || !std::isfinite(value)) {
                throw std::invalid_argument("non-finite or suffix");
            }
            return static_cast<Type>(value);
        }
    }
    catch (const std::exception&) {
        throw std::runtime_error(
            std::string("Invalid HARMPI header field ") + name + ": " +
            tokens[index] + ".");
    }
}

uint64_t checked_cells(const std::array<int, 3>& size) {
    uint64_t cells = 1;
    for (int value : size) {
        if (value <= 0) {
            throw std::runtime_error(
                "HARMPI global grid dimensions must be positive.");
        }
        const uint64_t factor = static_cast<uint64_t>(value);
        if (cells > std::numeric_limits<uint64_t>::max() / factor) {
            throw std::runtime_error("HARMPI cell count overflows uint64.");
        }
        cells *= factor;
    }
    return cells;
}

Header parse_header(const std::vector<std::string>& tokens) {
    // The current HARMPI writes out 57 items; the old script also described a 66-item variant with 9 items appended to it.
    if (tokens.size() != 57 && tokens.size() != 66) {
        throw std::runtime_error(
            "HARMPI dump header must contain 57 or 66 fields.");
    }

    Header header;
    header.fields = tokens.size();
    header.time = parse_number<double>(tokens, 0, "time");
    for (size_t axis = 0; axis < 3; axis++) {
        header.local_size[axis] =
            parse_number<int>(tokens, 1 + axis, "local_size");
        header.global_size[axis] =
            parse_number<int>(tokens, 4 + axis, "global_size");
        header.ghost_size[axis] =
            parse_number<int>(tokens, 7 + axis, "ghost_size");
        header.start[axis] =
            parse_number<double>(tokens, 10 + axis, "start");
        header.cell_width[axis] =
            parse_number<double>(tokens, 13 + axis, "cell_width");
    }
    header.final_time = parse_number<double>(tokens, 16, "final_time");
    header.step = parse_number<int64_t>(tokens, 17, "step");
    header.spin = parse_number<double>(tokens, 18, "spin");
    header.adiabatic_index =
        parse_number<double>(tokens, 19, "adiabatic_index");
    header.inner_radius = parse_number<double>(tokens, 33, "inner_radius");
    header.outer_radius = parse_number<double>(tokens, 34, "outer_radius");
    header.hslope = parse_number<double>(tokens, 35, "hslope");
    header.radial_offset = parse_number<double>(tokens, 36, "radial_offset");
    header.primitive_count = parse_number<int>(tokens, 37, "primitive_count");
    header.entropy = parse_number<int>(tokens, 38, "entropy") != 0;
    header.cylindrified = parse_number<int>(tokens, 39, "cylindrified") != 0;
    header.theta_fraction = parse_number<double>(tokens, 40, "theta_fraction");
    header.phi_fraction = parse_number<double>(tokens, 41, "phi_fraction");
    header.radial_break = parse_number<double>(tokens, 42, "radial_break");
    header.radial_power = parse_number<double>(tokens, 43, "radial_power");
    header.radial_coefficient =
        parse_number<double>(tokens, 44, "radial_coefficient");
    header.x1_transition = parse_number<double>(tokens, 45, "x1_transition");
    header.x2_transition = parse_number<double>(tokens, 46, "x2_transition");
    header.coordinate_family =
        parse_number<int>(tokens, 56, "coordinate_family");

    if (std::abs(header.spin) > 1.0 || header.adiabatic_index <= 1.0) {
        throw std::runtime_error("HARMPI spin or adiabatic index is invalid.");
    }
    for (size_t axis = 0; axis < 3; axis++) {
        if (header.local_size[axis] <= 0 || header.ghost_size[axis] < 0 ||
            !(header.cell_width[axis] > 0.0)) {
            throw std::runtime_error("HARMPI local grid metadata is invalid.");
        }
    }
    const int expected_primitives = header.entropy ? 9 : 8;
    if (header.primitive_count != expected_primitives) {
        throw std::runtime_error(
            "Unsupported HARMPI primitive count for dump layout.");
    }
    return header;
}

} // namespace

FrameMetadata inspect_frame(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw std::runtime_error(
            "Cannot open HARMPI frame: " + path.string() + ".");
    }
    std::string line;
    if (!std::getline(input, line)) {
        throw std::runtime_error(
            "Cannot read HARMPI frame header: " + path.string() + ".");
    }
    const std::streampos position = input.tellg();
    if (position < 0) {
        throw std::runtime_error(
            "HARMPI frame has no binary payload: " + path.string() + ".");
    }
    std::istringstream stream(line);
    std::vector<std::string> tokens;
    for (std::string token; stream >> token;) tokens.push_back(std::move(token));

    FrameMetadata metadata;
    metadata.header = parse_header(tokens);
    metadata.header_bytes = static_cast<uint64_t>(position);
    metadata.file_bytes = std::filesystem::file_size(path);
    metadata.cells = checked_cells(metadata.header.global_size);
    metadata.body_fields = metadata.header.entropy ? 42 : 41;
    const uint64_t fields = static_cast<uint64_t>(metadata.body_fields);
    if (metadata.cells >
        (std::numeric_limits<uint64_t>::max() - metadata.header_bytes) /
        (fields * sizeof(float))) {
        throw std::runtime_error("HARMPI payload size overflows uint64.");
    }
    const uint64_t expected = metadata.header_bytes +
        metadata.cells * fields * sizeof(float);
    if (metadata.file_bytes != expected) {
        std::ostringstream message;
        message << "HARMPI frame payload size mismatch: expected "
            << expected << " bytes, found " << metadata.file_bytes << ".";
        throw std::runtime_error(message.str());
    }
    return metadata;
}

Frame load_frame(const std::filesystem::path& path) {
    Frame frame;
    frame.metadata = inspect_frame(path);
    if (frame.metadata.cells > std::numeric_limits<size_t>::max()) {
        throw std::runtime_error("HARMPI frame is too large for this process.");
    }
    frame.cells.resize(static_cast<size_t>(frame.metadata.cells));

    std::ifstream input(path, std::ios::binary);
    input.seekg(static_cast<std::streamoff>(frame.metadata.header_bytes));
    if (!input) {
        throw std::runtime_error(
            "Cannot seek to HARMPI frame payload: " + path.string() + ".");
    }

    constexpr size_t chunk_cells = 4096;
    const size_t fields = frame.metadata.body_fields;
    std::vector<float> buffer(chunk_cells * fields);
    const size_t u_offset = 9 +
        static_cast<size_t>(frame.metadata.header.primitive_count) + 1;
    const size_t b_offset = u_offset + 8;
    size_t first = 0;
    while (first < frame.cells.size()) {
        const size_t count = std::min(chunk_cells, frame.cells.size() - first);
        const size_t values = count * fields;
        input.read(
            reinterpret_cast<char*>(buffer.data()),
            static_cast<std::streamsize>(values * sizeof(float)));
        if (!input) {
            throw std::runtime_error(
                "Cannot read complete HARMPI frame payload: " +
                path.string() + ".");
        }
        for (size_t local = 0; local < count; local++) {
            const float* source = buffer.data() + local * fields;
            RadiationCell& target = frame.cells[first + local];
            target.rho = source[9];
            target.internal_energy = source[10];
            for (size_t component = 0; component < 4; component++) {
                target.u_code[component] = source[u_offset + component];
                target.b_code[component] = source[b_offset + component];
            }
        }
        first += count;
    }
    return frame;
}

uint64_t cell_index(
    const Header& header,
    int i,
    int j,
    int k) {

    const auto& size = header.global_size;
    if (i < 0 || i >= size[0] || j < 0 || j >= size[1] ||
        k < 0 || k >= size[2]) {
        throw std::out_of_range("HARMPI cell index is outside the global grid.");
    }
    return (static_cast<uint64_t>(i) * static_cast<uint64_t>(size[1]) +
        static_cast<uint64_t>(j)) * static_cast<uint64_t>(size[2]) +
        static_cast<uint64_t>(k);
}

std::vector<FrameInfo> discover_frames(
    const std::filesystem::path& data_directory) {

    static const std::regex name_pattern(R"(^dump-(\d+)$)");
    std::vector<FrameInfo> frames;
    for (const auto& entry : std::filesystem::directory_iterator(data_directory)) {
        if (!entry.is_regular_file()) continue;
        std::smatch match;
        const std::string name = entry.path().filename().string();
        if (!std::regex_match(name, match, name_pattern)) continue;
        const long long index = std::stoll(match[1].str());
        if (index > std::numeric_limits<int>::max()) {
            throw std::runtime_error("HARMPI source frame index exceeds int range.");
        }
        const FrameMetadata metadata = inspect_frame(entry.path());
        frames.push_back({
            static_cast<int>(index), entry.path(), metadata.header.time});
    }
    std::sort(frames.begin(), frames.end(), [](const auto& first, const auto& second) {
        return first.index < second.index;
    });
    return frames;
}

} // namespace fluid::harmpi
