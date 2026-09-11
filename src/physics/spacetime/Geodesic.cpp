#include <cmath>
#include <array>
#include <iostream>
#include <algorithm>
#include <limits>
#include  "Metric.h"

std::array<double, 8> GeodesicEquation(const double &lambda, const std::array<double, 8>& y) 
{
    std::array<double, 8> dydlambda = {};

    // -------------------------
    // Extract coordinates and momentum
    // -------------------------
    const std::array<double, 4> x = { y[0], y[1], y[2], y[3] };
    const std::array<double, 4> k = { y[4], y[5], y[6], y[7] };
    // -------------------------
    // Christoffel symbols Γ^μ_{νρ}
    // -------------------------
    std::array<std::array<std::array<double, 4>, 4>, 4> conn=get_conn(x);

    // -------------------------
    // (1) Coordinate evolution: dx^μ/dλ = k^μ
    // -------------------------
    for (int mu = 0; mu < 4; ++mu) {
        dydlambda[mu] = y[4 + mu];
    }

    // -------------------------
    // (2) Momentum evolution: dk^μ/dλ = -Γ^μ_{νρ} k^ν k^ρ
    // -------------------------


    for (int mu = 0; mu < 4; ++mu) {
        double sum = 0.0;
        for (int nu = 0; nu < 4; ++nu) {
            for (int rho = 0; rho < 4; ++rho) {
                sum += conn[mu][nu][rho] * k[nu] * k[rho];
            }
        }
        dydlambda[4 + mu] = -sum;
    }

    return dydlambda;

};




std::array<double, 12> GeodesicPolarEquation(const double& lambda, const std::array<double, 12>& y)
{
    std::array<double, 12> dydlambda = {};

    const std::array<double, 4> x = { y[0], y[1], y[2], y[3] };
    const std::array<double, 4> k = { y[4], y[5], y[6], y[7] };
    const std::array<double, 4> f = { y[8], y[9], y[10], y[11] };
    std::array<std::array<std::array<double, 4>, 4>, 4> conn = get_conn(x);

    for (int mu = 0; mu < 4; ++mu) {
        dydlambda[mu] = k[mu];
    }

    for (int mu = 0; mu < 4; ++mu) {
        double ksum = 0.0;
        double fsum = 0.0;
        for (int nu = 0; nu < 4; ++nu) {
            for (int rho = 0; rho < 4; ++rho) {
                ksum += conn[mu][nu][rho] * k[nu] * k[rho];
                fsum += conn[mu][nu][rho] * k[nu] * f[rho];
            }
        }
        dydlambda[4 + mu] = -ksum;
        dydlambda[8 + mu] = -fsum;
    }

    return dydlambda;
}

///////////////////////////Put it aside temporarily
std::array<double, 4> GetRayDirection(
    const std::array<double, 4>& pos,
    double fov,
    int npix,
    int ii,
    int jj) {
    // Extract coordinates (note array index: 0=t, 1=r, 2=theta, 3=phi)
  
    std::array<double, 4> e0, e1, e2, e3;
    // Get metric
    std::array<std::array<double, 4>, 4>  gcov = MetricDown(pos);
   

    e0[0] = sqrt(((-pow(gcov[1][3], 2) + gcov[3][3] * gcov[1][1]) /
        (-2.0 * gcov[1][3] * gcov[0][3] * gcov[0][1] + gcov[3][3] * pow(gcov[0][1], 2)
            + pow(gcov[1][3], 2) * gcov[0][0] + gcov[1][1] * (pow(gcov[0][3], 2) - gcov[3][3] * gcov[0][0]))));

    e0[1] = (1.0 / (pow(gcov[1][3], 2) - gcov[3][3] * gcov[1][1]))
        * (-gcov[1][3] * gcov[0][3] + gcov[3][3] * gcov[0][1])
        * sqrt(((-pow(gcov[1][3], 2) + gcov[3][3] * gcov[1][1]) /
            (-2.0 * gcov[1][3] * gcov[0][3] * gcov[0][1] + gcov[3][3] * pow(gcov[0][1], 2)
                + pow(gcov[1][3], 2) * gcov[0][0] + gcov[1][1] * (pow(gcov[0][3], 2) - gcov[3][3] * gcov[0][0]))));

    e0[2] = 0.0;

    e0[3] = (1.0 / (pow(gcov[1][3], 2) - gcov[3][3] * gcov[1][1]))
        * (gcov[1][1] * gcov[0][3] - gcov[1][3] * gcov[0][1])
        * sqrt(((-pow(gcov[1][3], 2) + gcov[3][3] * gcov[1][1]) /
            (-2.0 * gcov[1][3] * gcov[0][3] * gcov[0][1] + gcov[3][3] * pow(gcov[0][1], 2)
                + pow(gcov[1][3], 2) * gcov[0][0] + gcov[1][1] * (pow(gcov[0][3], 2) - gcov[3][3] * gcov[0][0]))));
    // ==== e1 ====
    e1[0] = 0.0;
    e1[1] = -1.0 / sqrt(gcov[1][1]);
    e1[2] = 0.0;
    e1[3] = 0.0;
    // ==== e2 ====
    e2[0] = 0.0;
    e2[1] = 0.0;
    e2[2] = 1.0 / sqrt(gcov[2][2]);
    e2[3] = 0.0;
    // ==== e3 ====
    e3[0] = 0.0;
    e3[1] = sqrt(gcov[1][1] / (gcov[3][3] * gcov[1][1] - pow(gcov[1][3], 2))) * (gcov[1][3] / gcov[1][1]);
    e3[2] = 0.0;
    e3[3] = -sqrt(gcov[1][1] / (gcov[3][3] * gcov[1][1] - pow(gcov[1][3], 2)));



    // ---------------------------
    // Screen coordinates -> angle
    // ---------------------------
    double xscr = 2.0 * std::tan(fov / 2.0) * (ii - 0.5 * (npix + 1)) / npix;
    double yscr = 2.0 * std::tan(fov / 2.0) * (jj - 0.5 * (npix + 1)) / npix;


    double Px = std::atan2(xscr, yscr);
    double Tx = 2.0 * std::atan(std::sqrt((xscr * xscr + yscr * yscr)) / 2.0);

    // ---------------------------
    // Construct four speeds (contravariant component) taudot^μ
    // ---------------------------
    const double k = 1.0;                     // scale factor
    double cosTx = std::cos(Tx);
    double sinTx = std::sin(Tx);
    double cosPx = std::cos(Px);
    double sinPx = std::sin(Px);

    std::array<double, 4> taudot;
    for (int i = 0; i < 4; ++i) {
        taudot[i] = k * (-e0[i] + cosTx * e1[i] + sinTx * cosPx * e2[i] + sinTx * sinPx * e3[i]);
    }

    // ---------------------------
    return taudot;
}

//std::array<double, 4> GetRayDirection(
//    const std::array<double, 4>& pos,
//    double fov,
//    int npix,
//    int ii,
//    int jj) {
//    //Extract coordinates (note array index: 0=t, 1=r, 2=theta, 3=phi)
//
//
//    // Get the metric
//    std::array<std::array<double, 4>, 4> gdown = MetricDown(pos);
//
//
//    double gtt = gdown[0][0];
//    double grr = gdown[1][1];
//    double gThetaTheta = gdown[2][2];
//    double gPhiPhi = gdown[3][3];
//    double gtPhi = gdown[0][3]; // t-phi component of covariance metric
//
//    // ---------------------------
//    // Calculate ZAMO basis vectors (contravariant components)
//    // ---------------------------
//    double denom = gtt * gPhiPhi - gtPhi * gtPhi;          // g_tt g_φφ - (g_tφ)^2
//    double factor = std::sqrt(-(gPhiPhi / denom)); // normalization factor
//
//    std::array<double, 4> e0 = {
//        factor * 1.0,
//        0.0,
//        0.0,
//        factor * (-gtPhi / gPhiPhi)
//    };
//
//    std::array<double, 4> e1 = {
//        0.0,
//        -1.0 / std::sqrt(grr),
//        0.0,
//        0.0
//    };
//
//    std::array<double, 4> e2 = {
//        0.0,
//        0.0,
//        1.0 / std::sqrt(gThetaTheta),
//        0.0
//    };
//
//    std::array<double, 4> e3 = {
//        0.0,
//        0.0,
//        0.0,
//        -1.0 / std::sqrt(gPhiPhi)
//    };
//
//    // ---------------------------
//    //Screen coordinates -> angle
//    // ---------------------------
//    double xscr = 2.0 * std::tan(fov / 2.0) * (ii - 0.5 * (npix + 1)) / npix;
//    double yscr = 2.0 * std::tan(fov / 2.0) * (jj - 0.5 * (npix + 1)) / npix;
//
//
//    double Px = std::atan2(xscr, yscr);
//    double Tx = 2.0 * std::atan(std::sqrt((xscr * xscr + yscr * yscr)) / 2.0);
//
//    // ---------------------------
//    // Construct four speeds (inverse component) taudot^μ
//    // ---------------------------
//    const double k = 1.0; // scale factor
//    double cosTx = std::cos(Tx);
//    double sinTx = std::sin(Tx);
//    double cosPx = std::cos(Px);
//    double sinPx = std::sin(Px);
//
//    std::array<double, 4> taudot;
//    for (int i = 0; i < 4; ++i) {
//        taudot[i] = k * (-e0[i] + cosTx * e1[i] + sinTx * cosPx * e2[i] + sinTx * sinPx * e3[i]);
//    }
//
//    // ---------------------------
//    return taudot;
//}
//
