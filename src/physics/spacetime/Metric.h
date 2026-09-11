#pragma once
#include <array>
#include <cmath>

// Switch to the physical spherical Kerr–Schild metric using the spin in the data header.
void SetKerrSchildMetric(double spin);

// Restore the metrics in the current application compilation configuration.
void ResetMetric();

std::array<std::array<double, 4>, 4> MetricDown(const std::array<double, 4>& x);
std::array<std::array<double, 4>, 4> MetricUp(const std::array<double, 4>& x);


std::array<std::array<std::array<double, 4>, 4>, 4> get_conn(const std::array<double, 4>& x);


double get_radial_radius(const std::array<double, 4>& x);

// Convert the angular coordinates of the current coordinate system into the physical polar angle relative to the rotation axis, in rad.
double get_polar_angle(const std::array<double, 4>& x);
