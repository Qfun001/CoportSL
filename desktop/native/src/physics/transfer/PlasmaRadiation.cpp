#include "src/physics/transfer/PlasmaRadiation.h"

#include <array>
#include <cmath>

#include "src/support/numerics/LinearAlgebra.h"
#include "src/physics/spacetime/Metric.h"
#include "src/physics/transfer/NonthermalDistribution.h"
#include "src/physics/transfer/ThermalDistribution.h"
#include "src/physics/Constants.h"
#include "src/physics/Model.h"

namespace {

double sign_of(double value) {
    if (value > 0.0) return 1.0;
    if (value < 0.0) return -1.0;
    return 0.0;
}

double polarization_angle(
    const std::array<double, 4>& u,
    const std::array<double, 4>& k,
    const std::array<double, 4>& f,
    const std::array<double, 4>& b,
    const std::array<std::array<double, 4>, 4>& gdown) {

    std::array<std::array<double, 4>, 4> orientation = {};
    for (int i = 0; i < 4; i++) {
        orientation[i][0] = u[i];
        orientation[i][1] = k[i];
        orientation[i][2] = f[i];
        orientation[i][3] = b[i];
    }

    double det = det4(orientation);
    if (std::abs(det) < 1e-300) return 0.0;
    return sign_of(det) * PcAngle(u, k, f, b, gdown);
}

struct LocalCoefficients {
    double jI = 0.0, jQ = 0.0, jU = 0.0, jV = 0.0;
    double aI = 0.0, aQ = 0.0, aU = 0.0, aV = 0.0;
    double rQ = 0.0, rU = 0.0, rV = 0.0;
};

LocalCoefficients thermal_coefficients(const Radiation& radiation) {
    ThermalResult thermal = ThermalDistribution(
        radiation.ne,
        radiation.thetae,
        radiation.B,
        radiation.thetaB,
        radiation.nu);
    return {
        thermal.jI, thermal.jQ, thermal.jU, thermal.jV,
        thermal.aI, thermal.aQ, thermal.aU, thermal.aV,
        thermal.rQ, thermal.rU, thermal.rV
    };
}

LocalCoefficients mixed_coefficients(
    const LocalCoefficients& thermal,
    const NonthermalResult& nonthermal) {

    double f_nth = nonthermal.f_nth;
    if (f_nth <= 0.0) return thermal;

    double f_th = 1.0 - f_nth;
    return {
        f_nth * nonthermal.jI + f_th * thermal.jI,
        f_nth * nonthermal.jQ + f_th * thermal.jQ,
        f_nth * nonthermal.jU + f_th * thermal.jU,
        f_nth * nonthermal.jV + f_th * thermal.jV,
        f_nth * nonthermal.aI + f_th * thermal.aI,
        f_nth * nonthermal.aQ + f_th * thermal.aQ,
        f_nth * nonthermal.aU + f_th * thermal.aU,
        f_nth * nonthermal.aV + f_th * thermal.aV,
        f_nth * nonthermal.rQ + f_th * thermal.rQ,
        f_nth * nonthermal.rU + f_th * thermal.rU,
        f_nth * nonthermal.rV + f_th * thermal.rV
    };
}

void limit_polarization(LocalCoefficients& coefficients) {
    double polarized_j = coefficients.jQ * coefficients.jQ + coefficients.jV * coefficients.jV;
    if (polarized_j > 0.0) {
        double scale = std::abs(coefficients.jI) / std::sqrt(polarized_j);
        if (scale < 1.0) {
            coefficients.jQ *= Config::POL_LIMIT * scale;
            coefficients.jV *= Config::POL_LIMIT * scale;
        }
    }

    double polarized_a = coefficients.aQ * coefficients.aQ + coefficients.aV * coefficients.aV;
    if (polarized_a > 0.0) {
        double scale = std::abs(coefficients.aI) / std::sqrt(polarized_a);
        if (scale < 1.0) {
            coefficients.aQ *= Config::POL_LIMIT * scale;
            coefficients.aV *= Config::POL_LIMIT * scale;
        }
    }
}

LocalCoefficients local_coefficients(const Radiation& radiation) {
    // Match the validity range used by MATLAB GetRadiationParameter.m.
    if (!(radiation.thetae > Config::THETAE_EMIT &&
        radiation.ne > Config::NE_EMIT &&
        radiation.sigma < ModelConstants::SIGMA_MAX)) {
        return {};
    }

    LocalCoefficients coefficients = thermal_coefficients(radiation);
    if (ModelConstants::ElectronModel != ModelConstants::ThermalModel) {
        NonthermalResult nonthermal = NonthermalDistribution(
            radiation.thetae,
            radiation.ne,
            radiation.nu,
            radiation.B,
            radiation.thetaB,
            radiation.sigma,
            radiation.beta,
            ModelConstants::ElectronModel);
        coefficients = mixed_coefficients(coefficients, nonthermal);
    }

    limit_polarization(coefficients);
    return coefficients;
}

} // namespace

Radiation PlasmaRadiation(
    const std::array<double, 4>& x,
    const std::array<double, 4>& k,
    const std::array<double, 4>& f,
    const double& nu0,
    const fluid::State* fluid) {

    auto gdown = MetricDown(x);
    const std::array<double, 4>& u = fluid->U_u;
    const std::array<double, 4>& b = fluid->B_u;

    double dot_uk = 0.0;
    for (int i = 0; i < 4; i++) {
        for (int j = 0; j < 4; j++) {
            dot_uk += u[i] * gdown[i][j] * k[j];
        }
    }

    double rsf = -1.0 / dot_uk;
    double nu = nu0 / rsf;
    double theta_B = PitchAngle(u, k, b, gdown).thetaB;

    Radiation radiation{};
    radiation.ne = fluid->n_e;
    radiation.thetae = fluid->theta_e;
    radiation.sigma = fluid->sigma;
    radiation.beta = fluid->beta;
    radiation.B = fluid->B;
    radiation.thetaB = theta_B;
    radiation.nu = nu;
    radiation.chi = polarization_angle(u, k, f, b, gdown);
    radiation.rsf = rsf;
    return radiation;
}

TransferCoefficients transfer_coefficients(const Radiation& radiation) {
    LocalCoefficients coefficients = local_coefficients(radiation);
    double c2 = std::cos(2.0 * radiation.chi);
    double s2 = std::sin(2.0 * radiation.chi);
    double jfac = Constants::rg * radiation.rsf * radiation.rsf;
    double mfac = Constants::rg / radiation.rsf;

    TransferCoefficients result{};
    result.J_chi = {
        jfac * coefficients.jI,
        jfac * coefficients.jQ * c2,
        jfac * coefficients.jQ * s2,
        jfac * coefficients.jV
    };
    result.M_chi = { {
        {mfac * coefficients.aI, mfac * coefficients.aQ * c2, mfac * coefficients.aQ * s2, mfac * coefficients.aV},
        {mfac * coefficients.aQ * c2, mfac * coefficients.aI, mfac * coefficients.rV, -mfac * coefficients.rQ * s2},
        {mfac * coefficients.aQ * s2, -mfac * coefficients.rV, mfac * coefficients.aI, mfac * coefficients.rQ * c2},
        {mfac * coefficients.aV, mfac * coefficients.rQ * s2, -mfac * coefficients.rQ * c2, mfac * coefficients.aI}
    } };
    return result;
}
