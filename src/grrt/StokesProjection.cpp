#include "StokesProjection.h"

#include <cmath>

#include "src/support/numerics/LinearAlgebra.h"
#include "src/physics/spacetime/Metric.h"

namespace screen {

namespace {

std::array<double, 4> endpoint_vector(const float values[4]) {
    return { values[0], values[1], values[2], values[3] };
}

double sign_of(double value) {
    if (value > 0.0) return 1.0;
    if (value < 0.0) return -1.0;
    return 0.0;
}

double projection_angle(
    const std::array<double, 4>& k,
    const std::array<double, 4>& f,
    const std::array<std::array<double, 4>, 4>& gdown) {

    const std::array<double, 4> u = { 1.0, 0.0, 0.0, 0.0 };
    const std::array<double, 4> d = { 0.0, 0.0, -1.0, 0.0 };
    std::array<std::array<double, 4>, 4> orientation = {};
    for (int i = 0; i < 4; i++) {
        orientation[i][0] = u[i];
        orientation[i][1] = k[i];
        orientation[i][2] = f[i];
        orientation[i][3] = d[i];
    }
    const double determinant = det4(orientation);
    if (std::abs(determinant) < 1e-300) return 0.0;
    return -sign_of(determinant) * PcAngle(u, k, f, d, gdown);
}

} // namespace

std::array<double, 4> project_stokes(
    const ray::RayGeometry& rays,
    int pixel,
    const std::array<double, 4>& stokes) {

    if (pixel < 0 || pixel >= static_cast<int>(rays.endpoints.size())) return stokes;
    const ray::RayEndpoint& endpoint = rays.endpoints[static_cast<size_t>(pixel)];
    if (!endpoint.valid) return stokes;

    const auto x = endpoint_vector(endpoint.x);
    const auto k = endpoint_vector(endpoint.k);
    const auto f = endpoint_vector(endpoint.f);
    const double chi = projection_angle(k, f, MetricDown(x));
    const double c2 = std::cos(2.0 * chi);
    const double s2 = std::sin(2.0 * chi);
    return {
        stokes[0],
        stokes[1] * c2 - stokes[2] * s2,
        stokes[1] * s2 + stokes[2] * c2,
        stokes[3]
    };
}

} // namespace screen
