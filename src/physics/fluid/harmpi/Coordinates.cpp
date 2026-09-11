#include "Coordinates.h"

#include <cmath>
#include <numbers>
#include <stdexcept>

namespace fluid::harmpi {
namespace {

void validate_coordinates(const Header& header, const Vector4& code) {
    if (header.coordinate_family != 1 || header.cylindrified) {
        throw std::runtime_error(
            "Only non-cylindrified HARMPI Gammie coordinates are supported.");
    }
    if (!(header.radial_break > header.radial_offset) ||
        !(header.radial_power > 0.0) || header.radial_coefficient < 0.0 ||
        !(header.hslope > 0.0 && header.hslope < 2.0)) {
        throw std::runtime_error("HARMPI coordinate parameters are invalid.");
    }
    for (double value : code) {
        if (!std::isfinite(value)) {
            throw std::runtime_error("HARMPI code coordinate is not finite.");
        }
    }
}

struct RadialMap {
    double radius = 0.0;
    double derivative = 0.0;
};

double map_polar(const Header& header, double x2) {
    return std::numbers::pi / 2.0 * (1.0 + x2) +
        (1.0 - header.hslope) / 2.0 *
        std::sin(std::numbers::pi * (1.0 + x2));
}

RadialMap map_radial(const Header& header, double x1) {
    // HARMPI uses a hyperexponential radial grid outside breakpoints, and derivatives are used for four-vector transformations simultaneously.
    const double x1_break = std::log(
        header.radial_break - header.radial_offset);
    double exponent = x1;
    double exponent_derivative = 1.0;
    if (x1 > x1_break) {
        const double distance = x1 - x1_break;
        exponent += header.radial_coefficient *
            std::pow(distance, header.radial_power);
        exponent_derivative += header.radial_coefficient *
            header.radial_power *
            std::pow(distance, header.radial_power - 1.0);
    }
    const double scale = std::exp(exponent);
    if (!std::isfinite(scale) || !std::isfinite(exponent_derivative)) {
        throw std::runtime_error("HARMPI radial coordinate overflows.");
    }
    return {scale + header.radial_offset, scale * exponent_derivative};
}

} // namespace

Vector4 physical_coordinates(const Header& header, const Vector4& code) {
    validate_coordinates(header, code);
    const RadialMap radial = map_radial(header, code[1]);
    Vector4 physical = code;
    physical[1] = radial.radius;
    physical[2] = map_polar(header, code[2]);
    if (!std::isfinite(physical[2])) {
        throw std::runtime_error("HARMPI polar coordinate is not finite.");
    }
    return physical;
}

bool code_coordinates(
    const Header& header,
    const Vector4& physical,
    Vector4& code) {

    validate_coordinates(header, physical);
    const double x1_min = header.start[0];
    const double x1_max = x1_min +
        header.cell_width[0] * header.global_size[0];
    const double r_min = map_radial(header, x1_min).radius;
    const double r_max = map_radial(header, x1_max).radius;
    const double x2_min = header.start[1];
    const double x2_max = x2_min +
        header.cell_width[1] * header.global_size[1];
    const double theta_min = map_polar(header, x2_min);
    const double theta_max = map_polar(header, x2_max);
    const double tolerance = 1e-12;
    if (physical[1] < r_min * (1.0 - tolerance) ||
        physical[1] > r_max * (1.0 + tolerance) ||
        physical[2] < theta_min - tolerance ||
        physical[2] > theta_max + tolerance) {
        return false;
    }

    // The two coordinate mappings are strictly monotonic within the supported parameter range, and the bipartite inverse solution avoids runaway Newton step sizes in the superexponential region.
    double low = x1_min;
    double high = x1_max;
    for (int iteration = 0; iteration < 80; iteration++) {
        const double middle = (low + high) / 2.0;
        if (map_radial(header, middle).radius < physical[1]) low = middle;
        else high = middle;
    }
    code = physical;
    code[1] = (low + high) / 2.0;

    low = x2_min;
    high = x2_max;
    for (int iteration = 0; iteration < 80; iteration++) {
        const double middle = (low + high) / 2.0;
        if (map_polar(header, middle) < physical[2]) low = middle;
        else high = middle;
    }
    code[2] = (low + high) / 2.0;

    const double phi_min = header.start[2];
    const double phi_extent =
        header.cell_width[2] * header.global_size[2];
    const bool periodic = std::abs(phi_extent - 2.0 * std::numbers::pi) < 1e-8;
    if (periodic) {
        code[3] = phi_min + std::fmod(physical[3] - phi_min, phi_extent);
        if (code[3] < phi_min) code[3] += phi_extent;
    }
    else if (physical[3] < phi_min - tolerance ||
        physical[3] > phi_min + phi_extent + tolerance) {
        return false;
    }
    return true;
}

Matrix4 coordinate_jacobian(const Header& header, const Vector4& code) {
    validate_coordinates(header, code);
    const RadialMap radial = map_radial(header, code[1]);
    Matrix4 jacobian = {};
    jacobian[0][0] = 1.0;
    jacobian[1][1] = radial.derivative;
    jacobian[2][2] = std::numbers::pi / 2.0 +
        (1.0 - header.hslope) / 2.0 * std::numbers::pi *
        std::cos(std::numbers::pi * (1.0 + code[2]));
    jacobian[3][3] = 1.0;
    return jacobian;
}

Vector4 transform_contravariant(
    const Matrix4& jacobian,
    const Vector4& code_vector) {

    Vector4 physical = {};
    for (size_t row = 0; row < 4; row++) {
        for (size_t column = 0; column < 4; column++) {
            physical[row] += jacobian[row][column] * code_vector[column];
        }
    }
    return physical;
}

PhysicalVectors physical_vectors(
    const Header& header,
    const Vector4& code,
    const RadiationCell& cell) {

    const Matrix4 jacobian = coordinate_jacobian(header, code);
    Vector4 u_code = {};
    Vector4 b_code = {};
    for (size_t component = 0; component < 4; component++) {
        u_code[component] = cell.u_code[component];
        b_code[component] = cell.b_code[component];
    }
    return {
        transform_contravariant(jacobian, u_code),
        transform_contravariant(jacobian, b_code)};
}

} // namespace fluid::harmpi
