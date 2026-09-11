#pragma once
#include <array>
#include <cmath>
#include <algorithm>

std::array<double,4> AnalyticalSolution(
    const std::array<double,4>& j,
    const std::array<std::array<double,4>,4>& M,
    const std::array<double,4>& S,
    double dlam
);
