#pragma once

#include <array>
#include <cstddef>

#include "Reader.h"

namespace fluid::harmpi {

using Vector4 = std::array<double, 4>;
using Matrix4 = std::array<std::array<double, 4>, 4>;

struct PhysicalVectors {
    Vector4 u = {};
    Vector4 b = {};
};

Vector4 physical_coordinates(const Header& header, const Vector4& code);

bool code_coordinates(
    const Header& header,
    const Vector4& physical,
    Vector4& code);

Matrix4 coordinate_jacobian(const Header& header, const Vector4& code);

Vector4 transform_contravariant(
    const Matrix4& jacobian,
    const Vector4& code_vector);

PhysicalVectors physical_vectors(
    const Header& header,
    const Vector4& code,
    const RadiationCell& cell);

} // namespace fluid::harmpi
