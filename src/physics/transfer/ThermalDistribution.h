#pragma once
//#ifndef THERMAL_EMISSION_H
//#define THERMAL_EMISSION_H

struct ThermalResult {
    double jI, jQ, jU, jV;   // Emission coefficient
    double aI, aQ, aU, aV;   // absorption coefficient
    double rQ, rU, rV;       // Faraday rotation coefficient
};

// Main function declaration
ThermalResult  ThermalDistribution(double n_e, double theta_e, double B, double theta_B, double nu);
