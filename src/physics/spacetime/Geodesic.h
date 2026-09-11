#pragma once
#include <cmath>
#include <array>
#include <iostream>
#include <algorithm>
#include <limits>


std::array<double, 8> GeodesicEquation(const double& lambda, const std::array<double, 8>& y);

std::array<double, 12> GeodesicPolarEquation(const double& lambda, const std::array<double, 12>& y);

std::array<double, 4> GetRayDirection(
    const std::array<double, 4>& pos,
    double fov,
    int npix,
    int ii,
    int jj);
