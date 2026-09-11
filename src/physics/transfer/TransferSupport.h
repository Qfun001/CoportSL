#pragma once

#include "PlasmaRadiation.h"

struct CoefficientSupport {
    double jI = 0.0;
    double jP = 0.0;
    double aI = 0.0;
    double aP = 0.0;
    double rhoV = 0.0;
    double rhoC = 0.0;
};

CoefficientSupport coefficient_support(const TransferCoefficients& coefficients);
