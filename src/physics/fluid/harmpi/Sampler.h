#pragma once

#include <array>
#include <cstdint>

#include "Coordinates.h"
#include "src/physics/fluid/State.h"

namespace fluid::harmpi {

struct Location {
    std::array<uint32_t, 3> lower = {};
    std::array<float, 3> weight = {};
};

struct CodeSample {
    double rho = 0.0;
    double internal_energy = 0.0;
    Vector4 u_code = {};
    Vector4 b_code = {};
};

bool locate(
    const Header& header,
    const Vector4& physical,
    Location& location);

CodeSample interpolate(const Frame& frame, const Location& location);

CodeSample interpolate_frames(
    const Frame& first,
    const Frame& second,
    double weight,
    const Location& location);

bool sample_state(
    const Frame& frame,
    const Vector4& physical,
    const Location& location,
    const MetricTensor& metric,
    State& state);

bool sample_frames_state(
    const Frame& first,
    const Frame& second,
    double weight,
    const Vector4& physical,
    const Location& location,
    const MetricTensor& metric,
    State& state);

} // namespace fluid::harmpi
