#pragma once

#include <array>

#include "src/grrt/RayGeometry.h"
#include "src/physics/fluid/State.h"
#include "src/physics/transfer/PlasmaRadiation.h"

namespace grrt {

using MetricTensor = std::array<std::array<double, 4>, 4>;

// A single ray sampling point participates in the common geometric quantities of fluid reading and radiation transfer.
struct TransferSample {
    std::array<double, 4> x;
    std::array<double, 4> k;
    std::array<double, 4> f;
    MetricTensor gdown;
    MetricTensor gup;
    double dl = 0.0;
};

TransferSample make_transfer_sample(const ray::RayPoint& sample);

TransferCoefficients evaluate_transfer(
    const TransferSample& sample,
    fluid::State& state,
    double nu);

} // namespace grrt
