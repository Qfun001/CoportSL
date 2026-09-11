#include <array>
#include <cmath>
#include <algorithm>

#include "AnalyticalSolution.h"

std::array<double,4> AnalyticalSolution(
    const std::array<double,4>& j,
    const std::array<std::array<double,4>,4>& M,
    const std::array<double,4>& S,
    double dlam
) {
    constexpr double SMALL = 1e-9;
    constexpr int NDIM = 4;
    const bool zero_source = std::all_of(
        j.begin(), j.end(), [](double value) { return value == 0.0; });
    if (zero_source && std::all_of(
        S.begin(), S.end(), [](double value) { return value == 0.0; })) {
        return {};
    }

    // --- Extract parameters ---
    double aI = M[0][0];
    double aQ = M[0][1];
    double aU = M[0][2];
    double aV = M[0][3];

    double rQ = M[2][3];
    double rU = M[3][1];
    double rV = M[1][2];

    double jI = j[0];
    double jQ = j[1];
    double jU = j[2];
    double jV = j[3];

    double SI0 = S[0];
    double SQ0 = S[1];
    double SU0 = S[2];
    double SV0 = S[3];

    // ---Intermediate amount ---
    double alpha2 = aQ*aQ + aU*aU + aV*aV;
    double rho2   = rQ*rQ + rU*rU + rV*rV;
    double alphadrho = aQ*rQ + aU*rU + aV*rV;

    double T = 2.0 * std::sqrt( std::pow((alpha2 - rho2),2)/4.0 + alphadrho* alphadrho);
    double sig = (alphadrho > 0.0 ? 1.0 : (alphadrho < 0.0 ? -1.0 : 0.0));
    double ith = 1.0 / (T + SMALL);
    double L1 = std::sqrt(0.5*T + 0.5*(alpha2 - rho2)) + SMALL;
    double L2 = std::sqrt(0.5*T - 0.5*(alpha2 - rho2)) + SMALL;

    // ---Matrix initialization ---
    std::array<std::array<double,4>,4> M1{}, M2{}, M3{}, M4{}, O{}, P{};
    for (int i=0;i<NDIM;++i) {
        for (int j=0;j<NDIM;++j) {
            M1[i][j]=0.0; M2[i][j]=0.0; M3[i][j]=0.0; M4[i][j]=0.0;
            O[i][j]=0.0;  P[i][j]=0.0;
        }
    }
    for (int i=0;i<NDIM;++i) M1[i][i] = 1.0;

    // ---Construction M2 ---
    M2[0][1]= ith*(L2*aQ - sig*L1*rQ);
    M2[0][2]= ith*(L2*aU - sig*L1*rU);
    M2[0][3]= ith*(L2*aV - sig*L1*rV);
    M2[1][0]= M2[0][1];
    M2[1][2]= ith*(sig*L1*aV + L2*rV);
    M2[1][3]= ith*(-sig*L1*aU - L2*rU);
    M2[2][0]= M2[0][2];
    M2[2][1]= ith*(-sig*L1*aV - L2*rV);
    M2[2][3]= ith*(sig*L1*aQ + L2*rQ);
    M2[3][0]= M2[0][3];
    M2[3][1]= ith*(sig*L1*aU + L2*rU);
    M2[3][2]= ith*(-sig*L1*aQ - L2*rQ);

    // ---Construction M3 ---
    M3[0][1]= ith*(L1*aQ + sig*L2*rQ);
    M3[0][2]= ith*(L1*aU + sig*L2*rU);
    M3[0][3]= ith*(L1*aV + sig*L2*rV);
    M3[1][0]= M3[0][1];
    M3[1][2]= ith*(-sig*L2*aV + L1*rV);
    M3[1][3]= ith*(sig*L2*aU - L1*rU);
    M3[2][0]= M3[0][2];
    M3[2][1]= ith*(sig*L2*aV - L1*rV);
    M3[2][3]= ith*(-sig*L2*aQ + L1*rQ);
    M3[3][0]= M3[0][3];
    M3[3][1]= ith*(-sig*L2*aU + L1*rU);
    M3[3][2]= ith*(sig*L2*aQ - L1*rQ);

    // ---Construction M4 ---
    M4[0][0]= 2.*ith*(alpha2+rho2)/2.;
    M4[0][1]= 2.*ith*(aV*rU - aU*rV);
    M4[0][2]= 2.*ith*(aQ*rV - aV*rQ);
    M4[0][3]= 2.*ith*(aU*rQ - aQ*rU);

    M4[1][0]= 2.*ith*(aU*rV - aV*rU);
    M4[1][1]= 2.*ith*(aQ*aQ + rQ*rQ - (alpha2+rho2)/2.);
    M4[1][2]= 2.*ith*(aQ*aU + rQ*rU);
    M4[1][3]= 2.*ith*(aV*aQ + rV*rQ);

    M4[2][0]= 2.*ith*(aV*rQ - aQ*rV);
    M4[2][1]= 2.*ith*(aQ*aU + rQ*rU);
    M4[2][2]= 2.*ith*(aU*aU + rU*rU - (alpha2+rho2)/2.);
    M4[2][3]= 2.*ith*(aU*aV + rU*rV);

    M4[3][0]= 2.*ith*(aQ*rU - aU*rQ);
    M4[3][1]= 2.*ith*(aV*aQ + rV*rQ);
    M4[3][2]= 2.*ith*(aU*aV + rU*rV);
    M4[3][3]= 2.*ith*(aV*aV + rV*rV - (alpha2+rho2)/2.);

    // --- Factor ---
    double fac1 = 0.0;
    double fac2 = 0.0;
    if (!zero_source) {
        fac1 = 1.0 / (aI*aI - L1*L1);
        fac2 = 1.0 / (aI*aI + L2*L2);
    }
    double l1dlam = L1*dlam;
    double l2dlam = L2*dlam;
    double EaIdlam = std::exp(-aI*dlam);
    // Keep exp(-aI*dlam)*cosh/sinh finite in optically thick cells.
    double exp_cosh = 0.5 * (
        std::exp(-(aI - L1) * dlam) +
        std::exp(-(aI + L1) * dlam));
    double exp_sinh = 0.5 * (
        std::exp(-(aI - L1) * dlam) -
        std::exp(-(aI + L1) * dlam));
    double exp_cos = EaIdlam * std::cos(l2dlam);
    double exp_sin = EaIdlam * std::sin(l2dlam);

    // --- Calculate O and P ---
    for (int k=0;k<NDIM;++k){
        for (int l=0;l<NDIM;++l){
            O[k][l] =
                0.5*(exp_cosh+exp_cos)*M1[k][l]
              - exp_sin*M2[k][l]
              - exp_sinh*M3[k][l]
              + 0.5*(exp_cosh-exp_cos)*M4[k][l];

            if (!zero_source) {
                P[k][l] =
                    (-L1*fac1*M3[k][l] + 0.5*aI*fac1*(M1[k][l]+ M4[k][l])) +
                    (-L2*fac2*M2[k][l] + 0.5*aI*fac2*(M1[k][l]- M4[k][l])) -
                    ((-L1*fac1*M3[k][l] + 0.5*aI*fac1*(M1[k][l]+M4[k][l]))*exp_cosh +
                     (-L2*fac2*M2[k][l] + 0.5*aI*fac2*(M1[k][l]-M4[k][l]))*exp_cos +
                     (-aI*fac2*M2[k][l] - 0.5*L2*fac2*(M1[k][l]-M4[k][l]))*exp_sin -
                     ( aI*fac1*M3[k][l] - 0.5*L1*fac1*(M1[k][l]+M4[k][l]))*exp_sinh);
            }
        }
    }

    // ---Output ---
    double SI = O[0][0]*SI0 + O[0][1]*SQ0 + O[0][2]*SU0 + O[0][3]*SV0;
    double SQ = O[1][0]*SI0 + O[1][1]*SQ0 + O[1][2]*SU0 + O[1][3]*SV0;
    double SU = O[2][0]*SI0 + O[2][1]*SQ0 + O[2][2]*SU0 + O[2][3]*SV0;
    double SV = O[3][0]*SI0 + O[3][1]*SQ0 + O[3][2]*SU0 + O[3][3]*SV0;
    if (!zero_source) {
        SI += P[0][0]*jI + P[0][1]*jQ + P[0][2]*jU + P[0][3]*jV;
        SQ += P[1][0]*jI + P[1][1]*jQ + P[1][2]*jU + P[1][3]*jV;
        SU += P[2][0]*jI + P[2][1]*jQ + P[2][2]*jU + P[2][3]*jV;
        SV += P[3][0]*jI + P[3][1]*jQ + P[3][2]*jU + P[3][3]*jV;
    }

    return {SI,SQ,SU,SV};
}
