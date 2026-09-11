#include "LinearAlgebra.h"

#include <algorithm>
#include <cmath>

namespace {

double det3(const std::array<std::array<double, 3>, 3>& matrix) {
    return matrix[0][0] * (matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1])
        - matrix[0][1] * (matrix[1][0] * matrix[2][2] - matrix[1][2] * matrix[2][0])
        + matrix[0][2] * (matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0]);
}

double angle_from_inner_products(
    double numerator,
    double first_norm2,
    double second_norm2) {

    if (!std::isfinite(numerator) ||
        !(first_norm2 >= 0.0) || !std::isfinite(first_norm2) ||
        !(second_norm2 >= 0.0) || !std::isfinite(second_norm2)) {
        return 0.0;
    }
    constexpr double eps = 1.0e-15;
    const double denominator =
        std::sqrt(first_norm2) * std::sqrt(second_norm2) + eps;
    if (!std::isfinite(denominator)) return 0.0;
    const double cosine = numerator / denominator;
    if (!std::isfinite(cosine)) return 0.0;
    return std::acos(std::clamp(cosine, -1.0, 1.0));
}

} // namespace

double det4(const std::array<std::array<double, 4>, 4>& matrix) {
    const std::array<std::array<double, 3>, 3> minor0 = {{
        {matrix[1][1], matrix[1][2], matrix[1][3]},
        {matrix[2][1], matrix[2][2], matrix[2][3]},
        {matrix[3][1], matrix[3][2], matrix[3][3]}
    }};
    const std::array<std::array<double, 3>, 3> minor1 = {{
        {matrix[1][0], matrix[1][2], matrix[1][3]},
        {matrix[2][0], matrix[2][2], matrix[2][3]},
        {matrix[3][0], matrix[3][2], matrix[3][3]}
    }};
    const std::array<std::array<double, 3>, 3> minor2 = {{
        {matrix[1][0], matrix[1][1], matrix[1][3]},
        {matrix[2][0], matrix[2][1], matrix[2][3]},
        {matrix[3][0], matrix[3][1], matrix[3][3]}
    }};
    const std::array<std::array<double, 3>, 3> minor3 = {{
        {matrix[1][0], matrix[1][1], matrix[1][2]},
        {matrix[2][0], matrix[2][1], matrix[2][2]},
        {matrix[3][0], matrix[3][1], matrix[3][2]}
    }};

    return matrix[0][0] * det3(minor0)
        - matrix[0][1] * det3(minor1)
        + matrix[0][2] * det3(minor2)
        - matrix[0][3] * det3(minor3);
}

PitchAngleResult PitchAngle(
    const std::array<double, 4>& u,
    const std::array<double, 4>& k,
    const std::array<double, 4>& B,
    const std::array<std::array<double, 4>, 4>& metric) {

    double B0 = 0.0;
    double k0 = 0.0;
    for (int i = 0; i < 4; i++) {
        for (int j = 0; j < 4; j++) {
            B0 += u[i] * metric[i][j] * B[j];
            k0 += u[i] * metric[i][j] * k[j];
        }
    }

    std::array<double, 4> projected_B = {};
    std::array<double, 4> projected_k = {};
    for (int i = 0; i < 4; i++) {
        projected_B[i] = B[i] + B0 * u[i];
        projected_k[i] = k[i] + k0 * u[i];
    }

    double B_dot_k = 0.0;
    double B_dot_B = 0.0;
    double k_dot_k = 0.0;
    for (int i = 0; i < 4; i++) {
        for (int j = 0; j < 4; j++) {
            B_dot_k += projected_B[i] * metric[i][j] * projected_k[j];
            B_dot_B += projected_B[i] * metric[i][j] * projected_B[j];
            k_dot_k += projected_k[i] * metric[i][j] * projected_k[j];
        }
    }

    const double magnitude =
        B_dot_B > 0.0 && std::isfinite(B_dot_B) ?
        std::sqrt(B_dot_B) : 0.0;
    const double angle = angle_from_inner_products(
        B_dot_k, k_dot_k, B_dot_B);
    return {angle, magnitude};
}

double PcAngle(
    const std::array<double, 4>& u,
    const std::array<double, 4>& k,
    const std::array<double, 4>& f,
    const std::array<double, 4>& B,
    const std::array<std::array<double, 4>, 4>& metric) {

    double B0 = 0.0;
    double k0 = 0.0;
    double f0 = 0.0;
    for (int i = 0; i < 4; i++) {
        for (int j = 0; j < 4; j++) {
            B0 += u[i] * metric[i][j] * B[j];
            k0 += u[i] * metric[i][j] * k[j];
            f0 += u[i] * metric[i][j] * f[j];
        }
    }

    std::array<double, 4> projected_B = {};
    std::array<double, 4> projected_k = {};
    std::array<double, 4> projected_f = {};
    for (int i = 0; i < 4; i++) {
        projected_B[i] = B[i] + B0 * u[i];
        projected_k[i] = k[i] + k0 * u[i];
        projected_f[i] = f[i] + f0 * u[i];
    }

    double k_dot_k = 0.0;
    double k_dot_B = 0.0;
    double k_dot_f = 0.0;
    for (int i = 0; i < 4; i++) {
        for (int j = 0; j < 4; j++) {
            k_dot_k += projected_k[i] * metric[i][j] * projected_k[j];
            k_dot_B += projected_k[i] * metric[i][j] * projected_B[j];
            k_dot_f += projected_k[i] * metric[i][j] * projected_f[j];
        }
    }
    for (int i = 0; i < 4; i++) {
        projected_B[i] -= (k_dot_B / k_dot_k) * projected_k[i];
        projected_f[i] -= (k_dot_f / k_dot_k) * projected_k[i];
    }

    double B_dot_f = 0.0;
    double B_dot_B = 0.0;
    double f_dot_f = 0.0;
    for (int i = 0; i < 4; i++) {
        for (int j = 0; j < 4; j++) {
            B_dot_f += projected_B[i] * metric[i][j] * projected_f[j];
            B_dot_B += projected_B[i] * metric[i][j] * projected_B[j];
            f_dot_f += projected_f[i] * metric[i][j] * projected_f[j];
        }
    }

    return angle_from_inner_products(B_dot_f, f_dot_f, B_dot_B);
}

std::array<double, 4> GetPolarVec(
    const std::array<double, 4>& k,
    const std::array<std::array<double, 4>, 4>& metric_up) {

    constexpr double eps = 1.0e-30;
    int first = 1;
    int second = 2;
    if (std::abs(k[second]) < eps) second = 3;
    if (std::abs(k[second]) < eps) {
        first = 2;
        second = 1;
    }
    if (std::abs(k[second]) < eps) return {0.0, 0.0, 0.0, 0.0};

    std::array<double, 4> covector = {0.0, 0.0, 0.0, 0.0};
    covector[first] = 1.0;
    covector[second] = -k[first] / k[second];

    std::array<double, 4> vector = {0.0, 0.0, 0.0, 0.0};
    for (int mu = 0; mu < 4; mu++) {
        for (int nu = 0; nu < 4; nu++) {
            vector[mu] += covector[nu] * metric_up[nu][mu];
        }
    }

    double norm2 = 0.0;
    for (int mu = 0; mu < 4; mu++) norm2 += covector[mu] * vector[mu];
    const double norm = std::sqrt(std::abs(norm2));
    if (norm < eps || !std::isfinite(norm)) return {0.0, 0.0, 0.0, 0.0};

    for (double& value : vector) value /= norm;
    return vector;
}
