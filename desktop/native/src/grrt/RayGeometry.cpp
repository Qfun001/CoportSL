#include "src/grrt/RayGeometry.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

#include "src/support/numerics/DP5.h"
#include "src/support/numerics/LinearAlgebra.h"
#include "src/physics/spacetime/Metric.h"
#include "src/physics/Model.h"
#include "src/physics/spacetime/Geodesic.h"

namespace ray {

namespace {

void pixel_position(int pixel, int npix, int& col, int& row) {
    int number = pixel + 1;
    col = number % npix;
    if (col == 0) col = npix;
    row = (number - col) / npix + 1;
}

struct BuiltRay {
    std::vector<RayPoint> samples;
    RayEndpoint endpoint = {};
    double min_offset = std::numeric_limits<double>::infinity();
    double max_offset = -std::numeric_limits<double>::infinity();
    double max_float_error = 0.0;
    double max_reverse_time_step = 0.0;
    uint64_t monotonicity_violations = 0;
};

template <size_t N, typename DerivFunc>
std::array<double, N> rk5_step(
    DerivFunc&& f,
    const std::array<double, N>& y,
    double t,
    double h) {

    static constexpr double c2 = 1.0 / 5.0;
    static constexpr double c3 = 3.0 / 10.0;
    static constexpr double c4 = 4.0 / 5.0;
    static constexpr double c5 = 8.0 / 9.0;
    static constexpr double c6 = 1.0;
    static constexpr double a21 = 1.0 / 5.0;
    static constexpr double a31 = 3.0 / 40.0;
    static constexpr double a32 = 9.0 / 40.0;
    static constexpr double a41 = 44.0 / 45.0;
    static constexpr double a42 = -56.0 / 15.0;
    static constexpr double a43 = 32.0 / 9.0;
    static constexpr double a51 = 19372.0 / 6561.0;
    static constexpr double a52 = -25360.0 / 2187.0;
    static constexpr double a53 = 64448.0 / 6561.0;
    static constexpr double a54 = -212.0 / 729.0;
    static constexpr double a61 = 9017.0 / 3168.0;
    static constexpr double a62 = -355.0 / 33.0;
    static constexpr double a63 = 46732.0 / 5247.0;
    static constexpr double a64 = 49.0 / 176.0;
    static constexpr double a65 = -5103.0 / 18656.0;
    static constexpr double b1 = 35.0 / 384.0;
    static constexpr double b3 = 500.0 / 1113.0;
    static constexpr double b4 = 125.0 / 192.0;
    static constexpr double b5 = -2187.0 / 6784.0;
    static constexpr double b6 = 11.0 / 84.0;

    std::array<double, N> temp = {};
    std::array<double, N> next = {};
    std::array<double, N> k1 = f(t, y);
    for (size_t i = 0; i < N; i++) temp[i] = y[i] + h * a21 * k1[i];
    std::array<double, N> k2 = f(t + c2 * h, temp);
    for (size_t i = 0; i < N; i++) temp[i] = y[i] + h * (a31 * k1[i] + a32 * k2[i]);
    std::array<double, N> k3 = f(t + c3 * h, temp);
    for (size_t i = 0; i < N; i++) temp[i] = y[i] + h * (a41 * k1[i] + a42 * k2[i] + a43 * k3[i]);
    std::array<double, N> k4 = f(t + c4 * h, temp);
    for (size_t i = 0; i < N; i++) {
        temp[i] = y[i] + h * (a51 * k1[i] + a52 * k2[i] + a53 * k3[i] + a54 * k4[i]);
    }
    std::array<double, N> k5 = f(t + c5 * h, temp);
    for (size_t i = 0; i < N; i++) {
        temp[i] = y[i] + h * (
            a61 * k1[i] + a62 * k2[i] + a63 * k3[i] + a64 * k4[i] + a65 * k5[i]);
    }
    std::array<double, N> k6 = f(t + c6 * h, temp);

    for (size_t i = 0; i < N; i++) {
        next[i] = y[i] + h * (
            b1 * k1[i] + b3 * k3[i] + b4 * k4[i] + b5 * k5[i] + b6 * k6[i]);
    }
    return next;
}

bool trace_backward(
    std::array<double, 8>& y,
    double& h,
    std::vector<double>& steps,
    fluid::GridProbe grid_probe) {

    double lambda = 0.0;
    uint64_t grid_hint = 0;

    while (lambda < Config::RAY_LMAX) {
        std::array<double, 4> x = { y[0], y[1], y[2], y[3] };
        const std::array<double, 4> k = { y[4], y[5], y[6], y[7] };
        double grid_step = h;
        if (grid_probe(x, k, grid_hint, grid_step)) {
            h = grid_step;
        }

        StepResult<8> result = DP5_adaptive_step(
            GeodesicEquation,
            y,
            lambda,
            h,
            Config::RAY_ATOL,
            Config::RAY_RTOL,
            Config::RAY_HMIN);
        if (!result.success) {
            std::cerr << "Step failed at lambda = " << lambda << ", h = " << h << std::endl;
            return false;
        }

        steps.push_back(result.t - lambda);
        y = result.ynext;
        lambda = result.t;
        h = result.h;

        x = { y[0], y[1], y[2], y[3] };
        double rr = get_radial_radius(x);
        if (rr < Config::RAY_HORIZON * ModelConstants::horizon_radius() ||
            (rr > R_source && y[5] > 0.0)) {
            return true;
        }
    }

    return false;
}

RayPoint make_sample(
    const std::array<double, 4>& x,
    const std::array<double, 4>& k,
    const std::array<double, 4>& f,
    double dl,
    double raw_offset) {

    RayPoint sample = {};
    sample.x[0] = static_cast<float>(x[1]);
    sample.x[1] = static_cast<float>(x[2]);
    sample.x[2] = static_cast<float>(x[3]);
    for (int i = 0; i < 4; i++) sample.k[i] = static_cast<float>(k[i]);
    for (int i = 0; i < 4; i++) sample.f[i] = static_cast<float>(f[i]);
    sample.dl = static_cast<float>(dl);
    sample.dt = static_cast<float>(raw_offset);
    return sample;
}

RayEndpoint make_endpoint(const std::array<double, 12>& y, bool valid) {
    RayEndpoint endpoint = {};
    endpoint.valid = valid ? 1 : 0;
    for (int i = 0; i < 4; i++) {
        endpoint.x[i] = static_cast<float>(y[i]);
        endpoint.k[i] = static_cast<float>(y[4 + i]);
        endpoint.f[i] = static_cast<float>(y[8 + i]);
    }
    return endpoint;
}

BuiltRay build_ray(
    int pixel,
    int npix,
    double fov,
    const std::array<double, 4>& observer,
    fluid::GridProbe grid_probe) {

    int col = 0, row = 0;
    pixel_position(pixel, npix, col, row);

    std::array<double, 4> initial_k = GetRayDirection(observer, fov, npix, col, row);
    std::array<double, 8> y = {
        observer[0], observer[1], observer[2], observer[3],
        initial_k[0], initial_k[1], initial_k[2], initial_k[3]
    };

    double h = Config::RAY_H0;
    std::vector<double> steps;
    steps.reserve(1024);
    if (!trace_backward(y, h, steps, grid_probe)) return {};

    for (int i = 0; i < 4; ++i) y[4 + i] = -y[4 + i];

    std::array<double, 4> x0 = { y[0], y[1], y[2], y[3] };
    std::array<double, 4> k0 = { y[4], y[5], y[6], y[7] };
    std::array<double, 4> f0 = GetPolarVec(k0, MetricUp(x0));
    std::array<double, 12> state = {
        x0[0], x0[1], x0[2], x0[3],
        k0[0], k0[1], k0[2], k0[3],
        f0[0], f0[1], f0[2], f0[3]
    };

    double lambda = 0.0;
    uint64_t grid_hint = 0;
    BuiltRay build;
    build.samples.reserve(384);

    std::array<double, 4> x = { state[0], state[1], state[2], state[3] };
    std::array<double, 4> k = { state[4], state[5], state[6], state[7] };
    std::array<double, 4> f = { state[8], state[9], state[10], state[11] };
    double previous_sample_time = -std::numeric_limits<double>::infinity();

    for (auto it = steps.rbegin(); it != steps.rend(); ++it) {
        double dl = *it;
        double rr = get_radial_radius(x);

        if (rr < R_source) {
            double grid_step = dl;
            if (grid_probe(x, k, grid_hint, grid_step)) {
                double raw_offset = observer[0] - x[0];
                float stored_offset = static_cast<float>(raw_offset);
                build.min_offset = std::min(build.min_offset, raw_offset);
                build.max_offset = std::max(build.max_offset, raw_offset);
                build.max_float_error = std::max(
                    build.max_float_error,
                    std::abs(static_cast<double>(stored_offset) - raw_offset));

                if (x[0] < previous_sample_time) {
                    build.monotonicity_violations++;
                    build.max_reverse_time_step = std::max(
                        build.max_reverse_time_step,
                        previous_sample_time - x[0]);
                }
                previous_sample_time = x[0];
                build.samples.push_back(make_sample(x, k, f, dl, raw_offset));
            }
        }

        state = rk5_step(GeodesicPolarEquation, state, lambda, dl);
        lambda += dl;
        x = { state[0], state[1], state[2], state[3] };
        k = { state[4], state[5], state[6], state[7] };
        f = { state[8], state[9], state[10], state[11] };
    }

    build.endpoint = make_endpoint(state, !steps.empty());
    return build;
}

} // namespace

RayGeometry build_ray_geometry(
    int npix,
    double fov,
    const std::array<double, 4>& observer,
    fluid::GridProbe grid_probe) {

    if (grid_probe == nullptr) {
        throw std::invalid_argument("Ray construction requires a fluid grid probe.");
    }

    RayGeometry cache;
    cache.npix = npix;
    cache.fov = fov;
    cache.observer = observer;

    const int nray = npix * npix;
    std::vector<BuiltRay> per_ray(nray);

#pragma omp parallel for schedule(dynamic, 1)
    for (int pixel = 0; pixel < nray; pixel++) {
        per_ray[pixel] = build_ray(pixel, npix, fov, observer, grid_probe);
    }

    cache.ray_offset.resize(static_cast<size_t>(nray) + 1);
    cache.endpoints.resize(static_cast<size_t>(nray));
    uint64_t total = 0;
    double time_offset_origin = std::numeric_limits<double>::infinity();
    double max_raw_offset = -std::numeric_limits<double>::infinity();
    double max_raw_float_error = 0.0;

    for (int pixel = 0; pixel < nray; pixel++) {
        cache.ray_offset[pixel] = total;
        total += static_cast<uint64_t>(per_ray[pixel].samples.size());
        cache.endpoints[pixel] = per_ray[pixel].endpoint;
        if (!per_ray[pixel].samples.empty()) {
            time_offset_origin = std::min(time_offset_origin, per_ray[pixel].min_offset);
            max_raw_offset = std::max(max_raw_offset, per_ray[pixel].max_offset);
        }
        max_raw_float_error = std::max(max_raw_float_error, per_ray[pixel].max_float_error);
        cache.diagnostics.monotonicity_violations += per_ray[pixel].monotonicity_violations;
        if (per_ray[pixel].monotonicity_violations != 0) {
            cache.diagnostics.violating_rays++;
        }
        cache.diagnostics.max_reverse_time_step = std::max(
            cache.diagnostics.max_reverse_time_step,
            per_ray[pixel].max_reverse_time_step);
    }
    cache.ray_offset[nray] = total;

    if (!std::isfinite(time_offset_origin)) time_offset_origin = 0.0;
    float stored_origin = static_cast<float>(time_offset_origin);
    double origin_float_error = std::abs(static_cast<double>(stored_origin) - time_offset_origin);

    cache.samples.reserve(static_cast<size_t>(total));
    for (int pixel = 0; pixel < nray; pixel++) {
        for (RayPoint& sample : per_ray[pixel].samples) {
            sample.dt = std::max(0.0f, sample.dt - stored_origin);
            cache.samples.push_back(sample);
        }
        std::vector<RayPoint>().swap(per_ray[pixel].samples);
    }

    cache.diagnostics.time_offset_origin = time_offset_origin;
    cache.diagnostics.full_window =
        std::isfinite(max_raw_offset) ? max_raw_offset - time_offset_origin : 0.0;
    cache.diagnostics.max_float_error_bound =
        max_raw_float_error + origin_float_error +
        std::numeric_limits<float>::epsilon() * std::abs(cache.diagnostics.full_window);

    std::cout << "Ray geometry built: rays=" << nray
        << " samples=" << cache.samples.size()
        << " memory=" << (static_cast<double>(cache.samples.size() * sizeof(RayPoint)) /
            (1024.0 * 1024.0 * 1024.0))
        << " GiB\n";
    std::cout << "Time-offset geometry: origin=" << cache.diagnostics.time_offset_origin
        << " full_window=" << cache.diagnostics.full_window
        << " max_float_error_bound=" << cache.diagnostics.max_float_error_bound
        << " monotonicity_violations=" << cache.diagnostics.monotonicity_violations
        << " violating_rays=" << cache.diagnostics.violating_rays
        << " max_reverse_time_step=" << cache.diagnostics.max_reverse_time_step << "\n";

    return cache;
}

} // namespace ray
