#pragma once

#include <array>

double det4(const std::array<std::array<double, 4>, 4>& matrix);

struct PitchAngleResult {
    double thetaB;
    double B;
};

PitchAngleResult PitchAngle(
    const std::array<double, 4>& u,
    const std::array<double, 4>& k,
    const std::array<double, 4>& B,
    const std::array<std::array<double, 4>, 4>& metric);

double PcAngle(
    const std::array<double, 4>& u,
    const std::array<double, 4>& k,
    const std::array<double, 4>& f,
    const std::array<double, 4>& B,
    const std::array<std::array<double, 4>, 4>& metric);

std::array<double, 4> GetPolarVec(
    const std::array<double, 4>& k,
    const std::array<std::array<double, 4>, 4>& metric_up);
