#pragma once
#include <array>
#include <cmath>
#include <limits>
#include <algorithm>   // for std::max, std::min
#include <iostream>

    // Returns a structure containing the results of single-step integration
    template <size_t N>
    struct StepResult {
        std::array<double, N> ynext;   // New state (next state on success, current state on failure)
        double t;                       // New time (t + h on success, original t on failure)
        double h;                       // Adjusted step size (for next try)
        bool success;                   // true indicates that this step was successfully accepted, false indicates failure (the step size has been reduced and needs to be retried)
    };

    
    template <size_t N, typename DerivFunc>
    StepResult<N> DP5_adaptive_step(DerivFunc&& f,
        const std::array<double, N>& y,
        const double& t_in,
        const double& h_in,
        const double& atol,
        const double& rtol,
        const double& hmin) {

     //initialization
        double t = t_in;
        double h = h_in;

        // DOPRI5 coefficient
        // c vector
        static constexpr double c2 = 1.0 / 5.0, c3 = 3.0 / 10.0, c4 = 4.0 / 5.0, c5 = 8.0 / 9.0, c6 = 1.0, c7 = 1.0;

        // a matrix (stores only non-zero elements, row-wise)
        static constexpr double a21 = 1.0 / 5.0;
        static constexpr double a31 = 3.0 / 40.0, a32 = 9.0 / 40.0;
        static constexpr double a41 = 44.0 / 45.0, a42 = -56.0 / 15.0, a43 = 32.0 / 9.0;
        static constexpr double a51 = 19372.0 / 6561.0, a52 = -25360.0 / 2187.0, a53 = 64448.0 / 6561.0, a54 = -212.0 / 729.0;
        static constexpr double a61 = 9017.0 / 3168.0, a62 = -355.0 / 33.0, a63 = 46732.0 / 5247.0, a64 = 49.0 / 176.0, a65 = -5103.0 / 18656.0;
        static constexpr double a71 = 35.0 / 384.0, a73 = 500.0 / 1113.0, a74 = 125.0 / 192.0, a75 = -2187.0 / 6784.0, a76 = 11.0 / 84.0;

        // Fifth-order solution coefficient b5 (for propulsion)
        static constexpr double b51 = 35.0 / 384.0, b53 = 500.0 / 1113.0, b54 = 125.0 / 192.0, b55 = -2187.0 / 6784.0, b56 = 11.0 / 84.0;
        // Fourth-order solution coefficient b4 (used for error estimation)
        static constexpr double b41 = 5179.0 / 57600.0, b43 = 7571.0 / 16695.0, b44 = 393.0 / 640.0, b45 = -92097.0 / 339200.0, b46 = 187.0 / 2100.0, b47 = 1.0 / 40.0;


        //parameters
        static constexpr double safety = 0.9;
        static constexpr double max_factor = 5.0;
        static constexpr double min_factor = 0.1;
        // For the 5th order method, the error order is 5, so the 1/5 exponent is used
        static constexpr double expo = 1.0 / 5.0;


        //Number of solution failures
        int fail_count = 0; 
        const int max_fails = 30;

        // Open up each parameter space
        std::array<double, N> k1, k2, k3, k4, k5, k6, k7, ytemp, ynext;



        while (true) {
         
             k1=f(t,y );

           
            for (size_t i = 0; i < N; ++i) ytemp[i] = y[i] + h * a21 * k1[i];
             k2=f( t + c2 * h,ytemp);

           
            for (size_t i = 0; i < N; ++i) ytemp[i] = y[i] + h * (a31 * k1[i] + a32 * k2[i]);
             k3=f( t + c3 * h,ytemp);

            
            for (size_t i = 0; i < N; ++i) ytemp[i] = y[i] + h * (a41 * k1[i] + a42 * k2[i] + a43 * k3[i]);
            k4=f( t + c4 * h,ytemp);

         
            for (size_t i = 0; i < N; ++i) ytemp[i] = y[i] + h * (a51 * k1[i] + a52 * k2[i] + a53 * k3[i] + a54 * k4[i]);
             k5=f( t + c5 * h,ytemp);

           
            for (size_t i = 0; i < N; ++i) ytemp[i] = y[i] + h * (a61 * k1[i] + a62 * k2[i] + a63 * k3[i] + a64 * k4[i] + a65 * k5[i]);
            k6=f(t + c6 * h, ytemp );

       
            for (size_t i = 0; i < N; ++i) ytemp[i] = y[i] + h * (a71 * k1[i] + a73 * k3[i] + a74 * k4[i] + a75 * k5[i] + a76 * k6[i]);
            k7=f( t + c7 * h, ytemp );





            // Compute fifth-order solution (advancing) and fourth-order solution (error estimate)

            double max_err = 0.0;
            bool valid = true; //Exception judgment

            for (size_t i = 0; i < N; ++i) {
                double y5 = y[i] + h * (b51 * k1[i] + b53 * k3[i] + b54 * k4[i] + b55 * k5[i] + b56 * k6[i]);
                double y4 = y[i] + h * (b41 * k1[i] + b43 * k3[i] + b44 * k4[i] + b45 * k5[i] + b46 * k6[i] + b47 * k7[i]);
                ynext[i] = y5;      // Advance with fifth-order solution
                double err = std::abs(y5 - y4); //local error estimate
                if (!std::isfinite(ynext[i]) || !std::isfinite(err)) {
                    valid = false;
                    break;
                }
                // Compute scalar error metric (mixed absolute/relative tolerance)
                double tol = atol + rtol * std::max(std::abs(y[i]), std::abs(ynext[i]));
                double e = err / tol;
                if (e > max_err) max_err = e;
            }


            // Check value validity
            if (!valid) {
                // NaN/Inf appears, reduce the step size and try again
                h *= 0.5;
                fail_count++;
                if (fail_count > max_fails || h < hmin) {
                    // On failure, preserve the original state and time, reduce the step, and retry.
                    return StepResult<N>{y, t, h, false};
                }
                continue;
            }




            // Is the error acceptable?
            if (max_err <= 1.0) {
                // The step size is accepted and the recommended step size for the next step is calculated.
                double factor;
                if (max_err > 1e-12) {
                    factor = safety * std::pow(max_err, -expo);
                }
                else {
                    factor = max_factor;   // The error is extremely small and can be directly magnified to the maximum
                }
                factor = std::max(min_factor, std::min(max_factor, factor));
                double h_new = h * factor;

                // Return successful result: new status, new time, new step size
                return StepResult<N>{ynext, t + h, h_new, true};
            }
            else {
                // The error is too large, reduce the step size and try again.
                double factor;
                if (max_err > 1e-12) {
                    factor = safety * std::pow(max_err, -expo);
                }
                else {
                    factor = min_factor;   // Technically wouldn't go in here, but just in case
                }
                factor = std::max(min_factor, std::min(max_factor, factor));
                h = h * factor;

                fail_count++;
                if (fail_count > max_fails || h < hmin) {
                    // On failure, preserve the original state and time, reduce the step, and retry.
                    return StepResult<N>{y, t, h, false};
                }
                // Continue looping and try again with a smaller h
            }

        }
    };
