#include "Sampler.h"

#include <algorithm>
#include <cmath>
#include <numbers>
#include <stdexcept>

#include "src/physics/fluid/Scaling.h"

namespace fluid::harmpi {
namespace {

bool phi_is_periodic(const Header& header) {
    const double extent =
        header.cell_width[2] * header.global_size[2];
    return std::abs(extent - 2.0 * std::numbers::pi) < 1e-8;
}

uint32_t wrap(int value, uint32_t size) {
    int result = value % static_cast<int>(size);
    if (result < 0) result += static_cast<int>(size);
    return static_cast<uint32_t>(result);
}

} // namespace

bool locate(
    const Header& header,
    const Vector4& physical,
    Location& location) {

    Vector4 code = {};
    if (!code_coordinates(header, physical, code)) return false;
    const bool periodic_phi = phi_is_periodic(header);
    for (size_t axis = 0; axis < 3; axis++) {
        const uint32_t size = static_cast<uint32_t>(header.global_size[axis]);
        if (size == 1) {
            location.lower[axis] = 0;
            location.weight[axis] = 0.0f;
            continue;
        }
        const double coordinate =
            (code[axis + 1] - header.start[axis]) /
            header.cell_width[axis] - 0.5;
        if (axis == 2 && periodic_phi) {
            const int lower = static_cast<int>(std::floor(coordinate));
            location.lower[axis] = wrap(lower, size);
            location.weight[axis] = static_cast<float>(coordinate - lower);
        }
        else if (coordinate <= 0.0) {
            location.lower[axis] = 0;
            location.weight[axis] = 0.0f;
        }
        else if (coordinate >= static_cast<double>(size - 1)) {
            location.lower[axis] = size - 1;
            location.weight[axis] = 0.0f;
        }
        else {
            const uint32_t lower = static_cast<uint32_t>(std::floor(coordinate));
            location.lower[axis] = lower;
            location.weight[axis] = static_cast<float>(coordinate - lower);
        }
    }
    return true;
}

CodeSample interpolate(const Frame& frame, const Location& location) {
    if (frame.cells.size() != frame.metadata.cells) {
        throw std::invalid_argument("HARMPI frame cell count is inconsistent.");
    }
    std::array<std::array<uint32_t, 2>, 3> index = {};
    for (size_t axis = 0; axis < 3; axis++) {
        const uint32_t size = static_cast<uint32_t>(
            frame.metadata.header.global_size[axis]);
        if (location.lower[axis] >= size) {
            throw std::out_of_range("HARMPI interpolation location is invalid.");
        }
        index[axis][0] = location.lower[axis];
        if (axis == 2 && phi_is_periodic(frame.metadata.header)) {
            index[axis][1] = (location.lower[axis] + 1) % size;
        }
        else {
            index[axis][1] = std::min(location.lower[axis] + 1, size - 1);
        }
    }

    CodeSample sample;
    for (int di = 0; di < 2; di++) {
        for (int dj = 0; dj < 2; dj++) {
            for (int dk = 0; dk < 2; dk++) {
                const double weight =
                    (di == 0 ? 1.0 - location.weight[0] : location.weight[0]) *
                    (dj == 0 ? 1.0 - location.weight[1] : location.weight[1]) *
                    (dk == 0 ? 1.0 - location.weight[2] : location.weight[2]);
                const uint64_t flat = cell_index(
                    frame.metadata.header,
                    static_cast<int>(index[0][di]),
                    static_cast<int>(index[1][dj]),
                    static_cast<int>(index[2][dk]));
                const RadiationCell& cell = frame.cells[static_cast<size_t>(flat)];
                sample.rho += weight * cell.rho;
                sample.internal_energy += weight * cell.internal_energy;
                for (size_t component = 0; component < 4; component++) {
                    sample.u_code[component] += weight * cell.u_code[component];
                    sample.b_code[component] += weight * cell.b_code[component];
                }
            }
        }
    }
    return sample;
}

CodeSample interpolate_frames(
    const Frame& first,
    const Frame& second,
    double weight,
    const Location& location) {

    if (first.metadata.header.global_size !=
            second.metadata.header.global_size ||
        first.metadata.header.start != second.metadata.header.start ||
        first.metadata.header.cell_width !=
            second.metadata.header.cell_width ||
        first.metadata.header.spin != second.metadata.header.spin ||
        first.metadata.header.adiabatic_index !=
            second.metadata.header.adiabatic_index ||
        first.metadata.header.hslope != second.metadata.header.hslope ||
        first.metadata.header.radial_offset !=
            second.metadata.header.radial_offset ||
        first.metadata.header.radial_break !=
            second.metadata.header.radial_break ||
        first.metadata.header.radial_power !=
            second.metadata.header.radial_power ||
        first.metadata.header.radial_coefficient !=
            second.metadata.header.radial_coefficient ||
        first.metadata.header.coordinate_family !=
            second.metadata.header.coordinate_family ||
        first.metadata.header.cylindrified !=
            second.metadata.header.cylindrified) {
        throw std::invalid_argument(
            "HARMPI frames do not share one interpolation grid.");
    }
    CodeSample result = interpolate(first, location);
    const CodeSample next = interpolate(second, location);
    weight = std::clamp(weight, 0.0, 1.0);
    result.rho = result.rho * (1.0 - weight) + next.rho * weight;
    result.internal_energy = result.internal_energy * (1.0 - weight) +
        next.internal_energy * weight;
    for (size_t component = 0; component < 4; component++) {
        result.u_code[component] =
            result.u_code[component] * (1.0 - weight) +
            next.u_code[component] * weight;
        result.b_code[component] =
            result.b_code[component] * (1.0 - weight) +
            next.b_code[component] * weight;
    }
    return result;
}

namespace {

bool make_state(
    const Header& header,
    const CodeSample& sample,
    const Vector4& physical,
    const MetricTensor& metric,
    State& state) {

    Vector4 code = {};
    if (!code_coordinates(header, physical, code)) return false;
    state = State{};
    const Matrix4 jacobian = coordinate_jacobian(header, code);
    state.U_u = transform_contravariant(jacobian, sample.u_code);
    state.B_u = transform_contravariant(jacobian, sample.b_code);

    double velocity_norm = 0.0;
    for (size_t row = 0; row < 4; row++) {
        for (size_t column = 0; column < 4; column++) {
            velocity_norm += state.U_u[row] *
                metric[row][column] * state.U_u[column];
        }
    }
    if (!(velocity_norm < 0.0) || !std::isfinite(velocity_norm)) return false;
    const double velocity_scale = 1.0 / std::sqrt(-velocity_norm);
    for (double& component : state.U_u) component *= velocity_scale;

    double velocity_magnetic = 0.0;
    for (size_t row = 0; row < 4; row++) {
        for (size_t column = 0; column < 4; column++) {
            state.U_d[row] += metric[row][column] * state.U_u[column];
            velocity_magnetic += state.U_u[row] *
                metric[row][column] * state.B_u[column];
        }
    }
    // Linear interpolation does not preserve the four-vector constraint; renormalizes $u^\mu$ at the query point and projects $b^\mu$ into its orthogonal subspace.
    for (size_t component = 0; component < 4; component++) {
        state.B_u[component] += velocity_magnetic * state.U_u[component];
    }
    double magnetic_norm = 0.0;
    for (size_t row = 0; row < 4; row++) {
        for (size_t column = 0; column < 4; column++) {
            state.B_d[row] += metric[row][column] * state.B_u[column];
        }
        magnetic_norm += state.B_u[row] * state.B_d[row];
    }
    for (size_t axis = 0; axis < 3; axis++) {
        state.dx_local[axis] = std::abs(
            jacobian[axis + 1][axis + 1] *
            header.cell_width[axis]);
    }
    set_radiative_scalars(
        state,
        sample.rho,
        sample.internal_energy,
        header.adiabatic_index,
        magnetic_norm);
    return true;
}

} // namespace

bool sample_state(
    const Frame& frame,
    const Vector4& physical,
    const Location& location,
    const MetricTensor& metric,
    State& state) {

    return make_state(
        frame.metadata.header,
        interpolate(frame, location),
        physical,
        metric,
        state);
}

bool sample_frames_state(
    const Frame& first,
    const Frame& second,
    double weight,
    const Vector4& physical,
    const Location& location,
    const MetricTensor& metric,
    State& state) {

    return make_state(
        first.metadata.header,
        interpolate_frames(first, second, weight, location),
        physical,
        metric,
        state);
}

} // namespace fluid::harmpi
