#include "NonthermalDistribution.h"

#include <algorithm>
#include <cmath>
#include <numbers>

#include "src/physics/Constants.h"
#include "src/physics/Model.h"

namespace {

struct Params {
    double power;
    double gamma_min;
    double gamma_max;
    double f_nth;
};

double sign(double value) {
    if (value > 0.0) return 1.0;
    if (value < 0.0) return -1.0;
    return 0.0;
}

Params distribution_params(double theta_e, double sigma, double beta) {
    double power = 1.8 + 0.7 / std::sqrt(sigma) +
        3.7 / std::pow(sigma, 0.19) *
        std::tanh(beta * 23.4 * std::pow(sigma, 0.26));
    power = std::clamp(
        power,
        Config::P_MIN,
        Config::P_MAX);

    double fthetae = (6.0 + 15.0 * theta_e) / (4.0 + 5.0 * theta_e);
    double gamma_min = std::max(1.0, 1.0 + theta_e * fthetae);
    double gamma_max = Config::GAMMA_RATIO * gamma_min;

    double epsilon_pic = 1.0 - 1.0 / (4.2 * std::pow(sigma, 0.55) + 1.0) +
        0.64 * std::pow(sigma, 0.07) *
        std::tanh(-68.0 * std::pow(sigma, 0.13) * beta);
    epsilon_pic = std::clamp(epsilon_pic, 0.0, 1.0);

    double uth = fthetae * theta_e;
    double unth = (power - 1.0) / (power - 2.0) * gamma_min - 1.0;
    double numerator = epsilon_pic * uth;
    double denominator = (1.0 - epsilon_pic) * unth + numerator;
    double f_nth = std::abs(denominator) > 1.0e-300 ? numerator / denominator : 0.0;

    return { power, gamma_min, gamma_max, std::clamp(f_nth, 0.0, 1.0) };
}

double pitch_sine(double theta_B) {
    // Power-law formulae are singular exactly parallel to the magnetic field.
    return std::max(std::sin(theta_B), 1.0e-12);
}

double cyclotron_frequency(double B) {
    return Constants::ELECTRON_CHARGE * B /
        (2.0 * std::numbers::pi * Constants::ELECTRON_MASS * Constants::SPEED_OF_LIGHT);
}

double angular_weight(double theta_B, int model) {
    if (model == ModelConstants::PowerLawModel) return 1.0;

    constexpr double sigma_alpha = Config::BEAM_WIDTH;
    constexpr double alpha0 = Config::BEAM_ANGLE;
    double root = std::sqrt(2.0 * sigma_alpha * sigma_alpha);
    double t1 = (-1.0 - std::cos(alpha0)) / root;
    double t2 = (1.0 - std::cos(alpha0)) / root;
    double beam_norm = std::sqrt(
        2.0 * std::pow(std::numbers::pi, 3.0) * sigma_alpha * sigma_alpha) *
        (std::erf(t2) - std::erf(t1));
    double exponent = std::exp(
        -std::pow(std::cos(theta_B) - std::cos(alpha0), 2.0) /
        (2.0 * sigma_alpha * sigma_alpha));

    if (model == ModelConstants::BeamModel) {
        return 4.0 * std::numbers::pi * exponent / beam_norm;
    }

    double losscone_norm = 4.0 * std::numbers::pi - beam_norm;
    return 4.0 * std::numbers::pi * (1.0 - exponent) / losscone_norm;
}

double j_I(double n_e, double nu, double B, double theta_B, const Params& p) {
    using namespace Constants;
    double sin_theta = pitch_sine(theta_B);
    double nuc = cyclotron_frequency(B);
    double prefac = n_e * ELECTRON_CHARGE * ELECTRON_CHARGE * nuc / SPEED_OF_LIGHT;
    double denom = 2.0 * (p.power + 1.0) *
        (std::pow(p.gamma_min, 1.0 - p.power) - std::pow(p.gamma_max, 1.0 - p.power));
    double gamma_term = std::tgamma((3.0 * p.power - 1.0) / 12.0) *
        std::tgamma((3.0 * p.power + 19.0) / 12.0);
    double freq_term = std::pow(nu / (nuc * sin_theta), -(p.power - 1.0) / 2.0);
    return prefac * std::pow(3.0, p.power / 2.0) * (p.power - 1.0) * sin_theta /
        denom * gamma_term * freq_term;
}

double j_Q(double n_e, double nu, double B, double theta_B, const Params& p) {
    return j_I(n_e, nu, B, theta_B, p) *
        ((p.power + 1.0) / (p.power + 7.0 / 3.0));
}

double j_V(double n_e, double nu, double B, double theta_B, const Params& p) {
    double sin_theta = pitch_sine(theta_B);
    double factor = (171.0 / 250.0) * std::pow(p.power, 49.0 / 100.0) *
        std::cos(theta_B) / sin_theta *
        std::pow(nu / (3.0 * cyclotron_frequency(B) * sin_theta), -0.5);
    return j_I(n_e, nu, B, theta_B, p) * factor;
}

double a_I(double n_e, double nu, double B, double theta_B, const Params& p) {
    using namespace Constants;
    double sin_theta = pitch_sine(theta_B);
    double nuc = cyclotron_frequency(B);
    double prefac = n_e * ELECTRON_CHARGE * ELECTRON_CHARGE /
        (ELECTRON_MASS * SPEED_OF_LIGHT * nu);
    double denom = 4.0 *
        (std::pow(p.gamma_min, 1.0 - p.power) - std::pow(p.gamma_max, 1.0 - p.power));
    double gamma_term = std::tgamma((3.0 * p.power + 2.0) / 12.0) *
        std::tgamma((3.0 * p.power + 22.0) / 12.0);
    double freq_term = std::pow(nu / (nuc * sin_theta), -(p.power + 2.0) / 2.0);
    return prefac * std::pow(3.0, (p.power + 1.0) / 2.0) * (p.power - 1.0) /
        denom * gamma_term * freq_term;
}

double a_Q(double n_e, double nu, double B, double theta_B, const Params& p) {
    double factor = std::pow(
        17.0 * p.power / 500.0 - 43.0 / 1250.0,
        43.0 / 500.0);
    return a_I(n_e, nu, B, theta_B, p) * factor;
}

double a_V(double n_e, double nu, double B, double theta_B, const Params& p) {
    double sin_theta = pitch_sine(theta_B);
    double angular_term = 31.0 / 10.0 * std::pow(sin_theta, -48.0 / 25.0) - 31.0 / 10.0;
    double factor = std::pow(
        71.0 * p.power / 100.0 + 22.0 / 625.0,
        197.0 / 500.0) *
        std::pow(angular_term, 64.0 / 125.0) *
        std::pow(nu / (cyclotron_frequency(B) * sin_theta), -0.5) *
        sign(std::cos(theta_B));
    return a_I(n_e, nu, B, theta_B, p) * factor;
}

double rho_Q(double n_e, double nu, double B, double theta_B, const Params& p) {
    using namespace Constants;
    double sin_theta = pitch_sine(theta_B);
    double nuc = cyclotron_frequency(B);
    double p_perp = n_e * ELECTRON_CHARGE * ELECTRON_CHARGE /
        (ELECTRON_MASS * SPEED_OF_LIGHT * nuc * sin_theta) *
        (p.power - 1.0) /
        (std::pow(p.gamma_min, 1.0 - p.power) - std::pow(p.gamma_max, 1.0 - p.power));
    double term = 1.0 - std::pow(
        2.0 * nuc * sin_theta * p.gamma_min * p.gamma_min / (3.0 * nu),
        p.power / 2.0 - 1.0);
    return -p_perp * std::pow(nuc * sin_theta / nu, 3.0) *
        std::pow(p.gamma_min, 2.0 - p.power) / (p.power / 2.0 - 1.0) * term;
}

double rho_V(double n_e, double nu, double B, double theta_B, const Params& p) {
    using namespace Constants;
    double sin_theta = pitch_sine(theta_B);
    double nuc = cyclotron_frequency(B);
    double p_perp = n_e * ELECTRON_CHARGE * ELECTRON_CHARGE /
        (ELECTRON_MASS * SPEED_OF_LIGHT * nuc * sin_theta) *
        (p.power - 1.0) /
        (std::pow(p.gamma_min, 1.0 - p.power) - std::pow(p.gamma_max, 1.0 - p.power));
    return 2.0 * p_perp * (p.power + 2.0) / (p.power + 1.0) *
        std::pow(nuc * sin_theta / nu, 2.0) *
        std::pow(p.gamma_min, -(p.power + 1.0)) * std::log(p.gamma_min) *
        std::cos(theta_B) / sin_theta;
}

} // namespace

NonthermalResult NonthermalDistribution(
    double theta_e,
    double n_e,
    double nu,
    double B,
    double theta_B,
    double sigma,
    double beta,
    int model) {

    if (!(theta_e > 0.0 && n_e > 0.0 && nu > 0.0 && B > 0.0 && sigma > 0.0) ||
        !std::isfinite(beta)) {
        return {};
    }

    Params params = distribution_params(theta_e, sigma, beta);
    double weight = angular_weight(theta_B, model);

    NonthermalResult result{};
    result.jI = weight * j_I(n_e, nu, B, theta_B, params);
    result.jQ = weight * j_Q(n_e, nu, B, theta_B, params);
    result.jV = weight * j_V(n_e, nu, B, theta_B, params);
    result.aI = weight * a_I(n_e, nu, B, theta_B, params);
    result.aQ = weight * a_Q(n_e, nu, B, theta_B, params);
    result.aV = weight * a_V(n_e, nu, B, theta_B, params);

    // MATLAB's zero assignments were temporary; retain the implemented Faraday terms.
    result.rQ = rho_Q(n_e, nu, B, theta_B, params);
    result.rV = rho_V(n_e, nu, B, theta_B, params);
    result.f_nth = params.f_nth;
    return result;
}
