#include "TransferSupport.h"

#include <cmath>

CoefficientSupport coefficient_support(const TransferCoefficients& coefficients) {
    CoefficientSupport support;
    support.jI = std::abs(coefficients.J_chi[0]);
    support.jP = std::hypot(
        std::hypot(coefficients.J_chi[1], coefficients.J_chi[2]),
        coefficients.J_chi[3]);
    support.aI = std::abs(coefficients.M_chi[0][0]);
    support.aP = std::hypot(
        std::hypot(coefficients.M_chi[0][1], coefficients.M_chi[0][2]),
        coefficients.M_chi[0][3]);
    support.rhoV = std::abs(coefficients.M_chi[1][2]);
    support.rhoC = std::hypot(
        coefficients.M_chi[2][3], coefficients.M_chi[3][1]);
    return support;
}
