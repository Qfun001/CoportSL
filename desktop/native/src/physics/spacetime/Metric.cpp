#include "src/physics/spacetime/Metric.h"
#include <array>
#include <cmath>

#include "src/physics/Model.h"




std::array<std::array<double, 4>, 4> MetricDown(const std::array<double, 4>& x) {

    using namespace ModelConstants;

    std::array<std::array<double, 4>, 4> gdown = { };

    if constexpr (metric == CAR) {

        gdown[0][0] = -1.0;
        for (int i = 1; i < 3; i++) gdown[i][i] = 1.0;

    }

    else if constexpr (metric == BL) {

        const double a = ModelConstants::blackhole_spin;
        const double r = x[1];
        const double theta = x[2];

        double cosT = std::cos(theta);
        double sinT = std::sin(theta);
        double sin2T = sinT * sinT;
        double cos2T = cosT * cosT;

        double Sigma = r * r + a * a * cos2T;
        double Delta = r * r - 2.0 * r + a * a;   // Note that M=1




        // Fill non-zero components
        gdown[0][0] = -1.0 + 2.0 * r / Sigma;                     // g_tt
        gdown[0][3] = -2.0 * a * r * sin2T / Sigma;               // g_tφ
        gdown[3][0] = gdown[0][3];                                // Symmetry
        gdown[1][1] = Sigma / Delta;                              // g_rr
        gdown[2][2] = Sigma;                                      // g_θθ
        gdown[3][3] = sin2T * (a * a + r * r + 2.0 * a * a * r * sin2T / Sigma); // g_φφ

    }
    else if constexpr (metric == MKSBHAC) {

        const double a = ModelConstants::blackhole_spin;
        const double hslope= ModelConstants::hs;


        double r = exp(x[1]);
        double theta = x[2] + 0.5 * hslope * sin(2. * x[2]);
        double sinth = sin(theta);
        double sin2th = sinth * sinth;
        double costh = cos(theta);
        double tfac = 1., rfac = r, hfac = 1. + hslope * cos(2. * x[2]), pfac = 1.;
        double rho2 = r * r + a * a * costh * costh;

        gdown[0][0] = (-1. + 2. * r / rho2) * tfac * tfac;
        gdown[0][1] = (2. * r / rho2) * tfac * rfac;
        gdown[0][3] = (-2. * a * r * sin2th / rho2) * tfac * pfac;
        gdown[1][0] = gdown[0][1];
        gdown[1][1] = (1. + 2. * r / rho2) * rfac * rfac;
        gdown[1][3] = (-a * sin2th * (1. + 2. * r / rho2)) * rfac * pfac;
        gdown[2][2] = rho2 * hfac * hfac;
        gdown[3][0] = gdown[0][3];
        gdown[3][1] = gdown[1][3];
        gdown[3][3] = sin2th * (rho2 + a * a * sin2th * (1. + 2. * r / rho2)) * pfac * pfac;

    }

    return  gdown;


}


std::array<std::array<double, 4>, 4> MetricUp(const std::array<double, 4>& x) {

    using namespace ModelConstants;

    std::array<std::array<double, 4>, 4> gup = { };

    if constexpr (metric == CAR) {

        gup[0][0] = -1.0;
        for (int i = 1; i < 3; i++) gup[i][i] = 1.0;

    }

    else if constexpr (metric == BL) {

        const double a = ModelConstants::blackhole_spin;
        double r = x[1];          // Radial coordinates
        double th = x[2];          // polar angle


        double sin_th = std::sin(th);
        double cos_th = std::cos(th);
        double sin2_th = sin_th * sin_th;
        double cos2_th = cos_th * cos_th;

        double delta = r * r - 2.0 * r + a * a;
        double sigma = r * r + a * a * cos2_th;




        // Fill non-zero components
        gup[0][0] = -((r * r + a * a) * (r * r + a * a) - a * a * sin2_th * delta) / (sigma * delta); // g^{tt}
        gup[0][3] = -2.0 * r * a / (sigma * delta);                                                   // g^{tφ}
        gup[3][0] = gup[0][3];                                                                         // Symmetry
        gup[1][1] = delta / sigma;                                                                     // g^{rr}
        gup[2][2] = 1.0 / sigma;                                                                       // g^{θθ}
        gup[3][3] = (delta - a * a * sin2_th) / (sigma * delta * sin2_th);                            // g^{φφ}

    }
    else if constexpr (metric == MKSBHAC) {

        const double a = ModelConstants::blackhole_spin;
        const double hslope = ModelConstants::hs;


        double r = exp(x[1]);
        double theta = x[2] + 0.5 * hslope * sin(2. * x[2]);
        double sinth = sin(theta);
        double sin2th = sinth * sinth;
        double costh = cos(theta);
        double irho2 = 1. / (r * r + a * a * costh * costh);
        double hfac = 1. + hslope * cos(2. * x[2]);

        gup[0][0] = -1. - 2. * r * irho2;
        gup[0][1] = 2. * irho2;
        gup[1][0] = gup[0][1];
        gup[1][1] = irho2 * (r * (r - 2.) + a * a) / (r * r);
        gup[1][3] = a * irho2 / r;
        gup[2][2] = irho2 / (hfac * hfac);
        gup[3][1] = gup[1][3];
        gup[3][3] = irho2 / (sin2th);

    }








    return gup;
}







double get_radial_radius(const std::array<double, 4>& x) {

    using namespace ModelConstants;



    if constexpr (metric == CAR) {

		return std::sqrt(x[1] * x[1] + x[2] * x[2] + x[3] * x[3]);  // Euclidean distance

    }
    else if constexpr (metric == BL) {
        return x[1];  // Radial coordinates
    }
    else if constexpr (metric == MKSBHAC) {
        return exp(x[1]);  // Radial coordinates
	}



};



double get_polar_angle(const std::array<double, 4>& x) {

    using namespace ModelConstants;

    if constexpr (metric == CAR) {
        const double cylindrical_radius = std::hypot(x[1], x[2]);
        return std::atan2(cylindrical_radius, x[3]);
    }
    else if constexpr (metric == MKSBHAC) {
        return x[2] + 0.5 * hs * std::sin(2.0 * x[2]);
    }
    else {
        return x[2];
    }
}

















std::array<std::array<std::array<double, 4>, 4>,4> get_conn(const std::array<double, 4>& x)
{

    double x0 = x[0];
    double x1 = x[1];
    double x2 = x[2];
    double x3 = x[3];

    static constexpr double epsilon = 1e-5;


    //initialization
    std::array<std::array<std::array<double, 4>, 4>, 4> ChristoffelSymbols = {};
    std::array<std::array<std::array<double, 4>, 4>, 4> conn = {};

    std::array<std::array<double, 4>, 4>   gcon = {};
    std::array<std::array<double, 4>, 4>   gcovh = {};
    std::array<std::array<double, 4>, 4>   gcovl = {};
    std::array<double, 4>   xh = {};
    std::array<double, 4>   xl = {};


    for (int kk = 0; kk < 4; kk++) {
        int x0del = kk == 0 ? 1 : 0;
        int x1del = kk == 1 ? 1 : 0;
        int x2del = kk == 2 ? 1 : 0;
        int x3del = kk == 3 ? 1 : 0;

        xh = {x0 + x0del * epsilon, x1 + x1del * epsilon, x2 + x2del * epsilon, x3 + x3del * epsilon };
        xl = {x0 - x0del * epsilon, x1 - x1del * epsilon, x2 - x2del * epsilon, x3 - x3del * epsilon };

        gcovh = MetricDown(xh);
        gcovl = MetricDown(xl);


        for (int ii = 0; ii < 4; ii++)
            for (int jj = 0; jj < 4; jj++)
                conn[ii][jj][kk] = (gcovh[ii][jj] - gcovl[ii][jj]) / (2 * epsilon);
    }


    gcon= MetricUp(x);

    /* finally, raise index */
    for (int ii = 0; ii < 4; ii++)
        for (int jj = 0; jj < 4; jj++)
            for (int kk = 0; kk < 4; kk++) {
                ChristoffelSymbols[ii][jj][kk] = 0.0;
                for (int ll = 0; ll < 4; ll++) ChristoffelSymbols[ii][jj][kk] += 0.5 * gcon[ii][ll]*
                    (conn[jj][ll][kk] + conn[kk][ll][jj] - conn[kk][jj][ll]) ;
            }

    return ChristoffelSymbols;
}
