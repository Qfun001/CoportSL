#pragma once

#include <array>
#include <cstdint>
#include <vector>

#include "src/physics/fluid/BackendTypes.h"

namespace ray {

struct RayPoint {
    float x[3];      // Spatial coordinates x1, x2, x3.
    float k[4];      // Inverse wave vector.
    float f[4];      // Polarization reference vector moving parallel to the ray.
    float dl;        // The affine parameter step size of the current sampling point.
    float dt;        // The coordinate delay relative to the earliest time of all valid sampling points.
};

struct RayEndpoint {
    float x[4];
    float k[4];
    float f[4];
    uint8_t valid = 0;
};

struct TimeOffsetDiagnostics {
    double time_offset_origin = 0.0;
    double full_window = 0.0;
    double max_float_error_bound = 0.0;
    double max_reverse_time_step = 0.0;
    uint64_t monotonicity_violations = 0;
    uint64_t violating_rays = 0;
};

struct RayGeometry {
    int npix = 0;
    double fov = 0.0;
    std::array<double, 4> observer = {};
    std::vector<uint64_t> ray_offset;
    std::vector<RayPoint> samples;
    std::vector<RayEndpoint> endpoints;
    TimeOffsetDiagnostics diagnostics;
};

inline std::array<double, 4> position(const RayPoint& point) {
    return { 0.0, point.x[0], point.x[1], point.x[2] };
}

inline std::array<double, 4> wave_vector(const RayPoint& point) {
    return { point.k[0], point.k[1], point.k[2], point.k[3] };
}

inline std::array<double, 4> polar_vector(const RayPoint& point) {
    return { point.f[0], point.f[1], point.f[2], point.f[3] };
}

// Construct fixed ray geometry and normalized coordinate delay.
RayGeometry build_ray_geometry(
    int npix,
    double fov,
    const std::array<double, 4>& observer,
    fluid::GridProbe grid_probe);

} // namespace ray
