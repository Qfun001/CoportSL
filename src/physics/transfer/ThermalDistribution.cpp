#include "ThermalDistribution.h"
#include "src/physics/Constants.h"
#include <cmath>

// Helper functions (visible only in the current file, use anonymous namespace or static)
namespace {
    inline double K_0(double x) { return -std::log(0.5 * x) - 0.5772; }
    inline double K_1(double x) { return 1.0 / x; }
    inline double K_2(double x) { return 2.0 / (x * x); }

    double PlanckFunction(double nu, double Te) {
        double exponent = Constants::PLANCK_CONSTANT * nu /
            (Constants::BOLTZMANN_CONSTANT * Te);
        return 2.0 * Constants::PLANCK_CONSTANT * nu * nu * nu /
            (Constants::SPEED_OF_LIGHT * Constants::SPEED_OF_LIGHT) /
            (std::exp(exponent) - 1.0);
    }

    double absorption(double j_nu, double nu, double Te) {
        return j_nu / PlanckFunction(nu, Te);
    }

    double I_I(double x) {
        return 2.5651 * (1.0 + 1.92 * std::pow(x, -1.0 / 3.0) + 0.9977 * std::pow(x, -2.0 / 3.0))
            * std::exp(-1.8899 * std::pow(x, 1.0 / 3.0));
    }

    double I_Q(double x) {
        return 2.5651 * (1.0 + 0.932 * std::pow(x, -1.0 / 3.0) + 0.4998 * std::pow(x, -2.0 / 3.0))
            * std::exp(-1.8899 * std::pow(x, 1.0 / 3.0));
    }

    double I_V(double x) {
        return (1.8138 / x + 3.423 * std::pow(x, -2.0 / 3.0) + 0.02955 * std::pow(x, -0.5) +
            2.0377 * std::pow(x, -1.0 / 3.0))
            * std::exp(-1.8899 * std::pow(x, 1.0 / 3.0));
    }

    double DeltaJ_5(double X) {
        return 0.4379 * std::log(1.0 + 0.001858 * std::pow(X, 1.503));
    }

    double f_m(double X) {
        double term1 = 2.011 * std::exp(-std::pow(X, 1.035) / 4.7);
        double term2 = std::cos(X * 0.5) * std::exp(-std::pow(X, 1.2) / 2.73);
        double term3 = 0.011 * std::exp(-X / 47.2);
        double term4 = (0.011 * std::exp(-X / 47.2) -
            std::pow(2.0, -1.0 / 3.0) * std::pow(3.0, -23.0 / 6.0) * 10000.0 *
            std::numbers::pi * std::pow(X, -8.0 / 3.0)) *
            0.5 * (1.0 + std::tanh(10.0 * std::log(X / 120.0)));
        return term1 - term2 - term3 + term4;
    }

    double j_I(double theta_e, double n_e, double nu, double B, double theta_B) {
        using namespace Constants;
        double nu_c = 3.0 * ELECTRON_CHARGE * B * std::sin(theta_B) *
            theta_e * theta_e /
            (4.0 * std::numbers::pi * ELECTRON_MASS * SPEED_OF_LIGHT);
        double x = nu / nu_c;
        return n_e * ELECTRON_CHARGE * ELECTRON_CHARGE * nu /
            (2.0 * std::sqrt(3.0) * SPEED_OF_LIGHT * theta_e * theta_e) *
            I_I(x);
    }

    double j_Q(double theta_e, double n_e, double nu, double B, double theta_B) {
        using namespace Constants;
        double nu_c = 3.0 * ELECTRON_CHARGE * B * std::sin(theta_B) *
            theta_e * theta_e /
            (4.0 * std::numbers::pi * ELECTRON_MASS * SPEED_OF_LIGHT);
        double x = nu / nu_c;
        return n_e * ELECTRON_CHARGE * ELECTRON_CHARGE * nu /
            (2.0 * std::sqrt(3.0) * SPEED_OF_LIGHT * theta_e * theta_e) *
            I_Q(x);
    }

    double j_V(double theta_e, double n_e, double nu, double B, double theta_B) {
        using namespace Constants;
        double nu_c = 3.0 * ELECTRON_CHARGE * B * std::sin(theta_B) *
            theta_e * theta_e /
            (4.0 * std::numbers::pi * ELECTRON_MASS * SPEED_OF_LIGHT);
        double x = nu / nu_c;
        return 2.0 * n_e * ELECTRON_CHARGE * ELECTRON_CHARGE * nu /
            std::tan(theta_B) /
            (3.0 * std::sqrt(3.0) * SPEED_OF_LIGHT * theta_e * theta_e * theta_e) *
            I_V(x);
    }

    double rho_Q(double theta_e, double n_e, double nu, double B, double theta_B) {
        using namespace Constants;
        double c1 = 4.0 * std::numbers::pi * n_e * ELECTRON_CHARGE * ELECTRON_CHARGE / ELECTRON_MASS;
        double omega = ELECTRON_CHARGE * B / (ELECTRON_MASS * SPEED_OF_LIGHT);
        double nu_c = 3.0 * ELECTRON_CHARGE * B * std::sin(theta_B) *
            theta_e * theta_e /
            (4.0 * std::numbers::pi * ELECTRON_MASS * SPEED_OF_LIGHT);
        double X = std::sqrt(nu_c / nu * std::sqrt(8.0) / 3.0 * 1000.0);
        double Thetaer = 1.0 / theta_e;
        return c1 * omega * omega * std::pow(std::sin(theta_B), 2.0) *
            f_m(X) / SPEED_OF_LIGHT /
            std::pow(2.0 * std::numbers::pi * nu, 3.0) / 2.0 *
            (K_1(Thetaer) / K_2(Thetaer) + 6.0 * theta_e);
    }

    double rho_V(double theta_e, double n_e, double nu, double B, double theta_B) {
        using namespace Constants;
        double c1 = 4.0 * std::numbers::pi * n_e * ELECTRON_CHARGE * ELECTRON_CHARGE / ELECTRON_MASS;
        double omega = ELECTRON_CHARGE * B / (ELECTRON_MASS * SPEED_OF_LIGHT);
        double nu_c = 3.0 * ELECTRON_CHARGE * B * std::sin(theta_B) *
            theta_e * theta_e /
            (4.0 * std::numbers::pi * ELECTRON_MASS * SPEED_OF_LIGHT);
        double X = std::sqrt(nu_c / nu * std::sqrt(8.0) / 3.0 * 1000.0);
        double Thetaer = 1.0 / theta_e;
        return c1 * omega * std::cos(theta_B) / SPEED_OF_LIGHT /
            std::pow(2.0 * std::numbers::pi * nu, 2.0) *
            (K_0(Thetaer) - DeltaJ_5(X)) / K_2(Thetaer);
    }
} // unnamed namespace

// Main function definition
ThermalResult ThermalDistribution(double n_e, double theta_e, double B, double theta_B, double nu ) 
{
    ThermalResult res;
    res.jI = j_I(theta_e, n_e, nu, B, theta_B);
    res.jQ = j_Q(theta_e, n_e, nu, B, theta_B);
    res.jU = 0.0;
    res.jV = j_V(theta_e, n_e, nu, B, theta_B);

    double Te = theta_e * Constants::MEC2 / Constants::BOLTZMANN_CONSTANT;
    res.aI = absorption(res.jI, nu, Te);
    res.aQ = absorption(res.jQ, nu, Te);
    res.aU = 0.0;
    res.aV = absorption(res.jV, nu, Te);

    res.rQ = rho_Q(theta_e, n_e, nu, B, theta_B);
    res.rU = 0.0;
    res.rV = rho_V(theta_e, n_e, nu, B, theta_B);
    return res;
}
