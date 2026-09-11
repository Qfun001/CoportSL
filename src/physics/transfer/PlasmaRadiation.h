#pragma once

#include <span>
#include <vector>
#include <array>
#include <utility>

#include "src/physics/fluid/State.h"

struct Radiation {
    double ne;
    double thetae;
    double sigma;
    double sigma_min;
    double beta;   
    double B;
    double thetaB;
    double nu;
    double chi;  
    double rsf;
};


Radiation PlasmaRadiation(const std::array< double, 4>& x,
    const std::array< double, 4>& k,
    const std::array< double, 4>& f,
    const double& nu0,
    const fluid::State* fluid);


struct TransferCoefficients {
    std::array<double, 4> J_chi;
    std::array<std::array<double, 4>, 4> M_chi;
};

TransferCoefficients transfer_coefficients(const Radiation& radiation);
