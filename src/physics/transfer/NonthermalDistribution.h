#pragma once

struct NonthermalResult {
    double jI, jQ, jU, jV;
    double aI, aQ, aU, aV;
    double rQ, rU, rV;
    double f_nth;  // Local nonthermal electron number fraction.
};

// Compute the selected nonthermal coefficients and the local mixing fraction.
NonthermalResult NonthermalDistribution(double theta_e, double n_e, double nu,
    double B, double theta_B,
    double sigma, double beta, int model);
