#pragma once

#include <array>

namespace fluid {

using FourVector = std::array<double, 4>;
using MetricTensor = std::array<std::array<double, 4>, 4>;

// Unified fluid states required for radiative transfer; individual data backends are responsible for populating these physical quantities.
struct State {
    FourVector U_u = {};
    FourVector B_u = {};
    FourVector U_d = {};
    FourVector B_d = {};
    double n_e = 0.0;
    double B = 0.0;
    double theta_e = 0.0;
    double sigma = 0.0;
    double sigma_min = 0.0;
    double beta = 0.0;
    std::array<double, 3> dx_local = {};
};

} // namespace fluid
