#include "apps/RunConfig.h"

#if COPORTSL_APP == COPORTSL_FLUX

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numbers>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "src/physics/Constants.h"
#include "src/physics/Model.h"
#include "src/grrt/fast/FastTransfer.h"
#include "src/physics/fluid/FluidBackend.h"
#include "src/physics/fluid/GridLocations.h"
#include "src/grrt/RayGeometry.h"

namespace {

constexpr double PC = 3.086e18; // Parsec, in cm.
constexpr double JY = 1.0e-23; // CGS flux density corresponding to 1 Jy.

struct FluxStats {
    int count = 0;
    double sum = 0.0;
    double sum_square = 0.0;
    double min = std::numeric_limits<double>::infinity();
    double max = -std::numeric_limits<double>::infinity();

    void add(double value) {
        count++;
        sum += value;
        sum_square += value * value;
        min = std::min(min, value);
        max = std::max(max, value);
    }

    double mean() const {
        return count == 0 ? std::numeric_limits<double>::quiet_NaN() : sum / count;
    }

    double stddev() const {
        if (count == 0) return std::numeric_limits<double>::quiet_NaN();
        const double avg = mean();
        const double variance = std::max(0.0, sum_square / count - avg * avg);
        return std::sqrt(variance);
    }
};

double flux_jy(const std::vector<std::array<double, 4>>& image) {
    double total_i = 0.0;
    for (const auto& pixel : image) {
        if (!std::isnan(pixel[0])) total_i += pixel[0];
    }

    const double npix = static_cast<double>(Config::NPIX);
    const double screen_flux = total_i *
        (2.0 * std::numbers::pi / (npix * npix)) *
        (1.0 - std::cos(Config::FOV / 2.0));
    const double luminosity_density = 4.0 * std::numbers::pi *
        Config::OBS_R * Config::OBS_R * Constants::rg * Constants::rg * screen_flux;
    const double distance_cm = Config::DISTANCE_PC * PC;
    return luminosity_density /
        (4.0 * std::numbers::pi * distance_cm * distance_cm) / JY;
}

void print_config() {
    const double start_time = fluid::Backend::frame_time(fluid::Backend::frame_path(Config::DATA, Config::NT0));
    const double end_time = fluid::Backend::frame_time(fluid::Backend::frame_path(Config::DATA, Config::NT1));
    const int frame_count = (Config::NT1 - Config::NT0) / Config::DNT + 1;

    std::cout << "Flux estimate configuration\n"
        << "  electron_model=" << ModelConstants::electron_model_name() << "\n"
        << "  fluid_backend=" << fluid::Backend::name() << "\n"
        << "  frames=" << Config::NT0 << ".." << Config::NT1 << "\n"
        << "  frame_step=" << Config::DNT << "\n"
        << "  sampled_frame_count=" << frame_count << "\n"
        << "  time_range_rg_over_c=" << start_time << ".." << end_time << "\n"
        << "  time_span_rg_over_c=" << end_time - start_time << "\n"
        << "  image=" << Config::NPIX << "x" << Config::NPIX << "\n"
        << "  fov_rad=" << Config::FOV << "\n"
        << "  observer_theta_deg=" << Config::OBS_TH * 180.0 / std::numbers::pi << "\n"
        << "  observer_radius=" << Config::OBS_R << " rg\n"
        << "  distance_pc=" << Config::DISTANCE_PC << "\n"
        << "  mdot=" << Config::MDOT << " Msun/yr\n"
        << "  mdot_sim=" << Config::MDOT_SIM << " MBH/T_unit\n"
        << "  target_flux_jy=" << Config::TARGET_FLUX_JY << "\n"
        << "  data_dir=" << Config::DATA << "\n"
        << "  grid_file=" << Config::GRID << "\n"
        << "  frequencies_GHz=";

    for (size_t i = 0; i < Config::NU.size(); i++) {
        if (i != 0) std::cout << ",";
        std::cout << Config::NU[i] / 1e9;
    }
    std::cout << "\n";
}

void print_summary(double nu, const FluxStats& stats) {
    if (stats.count == 0) {
        throw std::runtime_error("No flux samples were calculated.");
    }

    const double mean = stats.mean();
    const double linear_mdot = mean > 0.0 ?
        Config::MDOT * Config::TARGET_FLUX_JY / mean :
        std::numeric_limits<double>::quiet_NaN();
    const double sqrt_mdot = mean > 0.0 ?
        Config::MDOT * std::sqrt(Config::TARGET_FLUX_JY / mean) :
        std::numeric_limits<double>::quiet_NaN();

    std::cout << std::setprecision(10)
        << "Flux summary\n"
        << "  nu_GHz=" << nu / 1e9 << "\n"
        << "  frame_count=" << stats.count << "\n"
        << "  mean_flux_jy=" << mean << "\n"
        << "  min_flux_jy=" << stats.min << "\n"
        << "  max_flux_jy=" << stats.max << "\n"
        << "  std_flux_jy=" << stats.stddev() << "\n"
        << "  target_flux_jy=" << Config::TARGET_FLUX_JY << "\n"
        << "  current_mdot_msun_per_year=" << Config::MDOT << "\n"
        << "  suggested_mdot_linear=" << linear_mdot << "\n"
        << "  suggested_mdot_sqrt=" << sqrt_mdot << "\n"
        << "  note=suggested_mdot values are only first guesses; rerun Flux after changing MDOT.\n";
}

void run_flux() {
    fluid::Backend::initialize_grid(fluid::Backend::frame_path(Config::DATA, Config::NT0), Config::GRID);
    const ray::RayGeometry rays =
        ray::build_ray_geometry(
            Config::NPIX,
            Config::FOV,
            Config::OBS,
            fluid::Backend::probe_grid);
    const fluid::GridLocations sampling = fluid::locate_ray_samples(rays);

    std::vector<FluxStats> stats(Config::NU.size());
    std::vector<std::array<double, 4>> image;

    for (int nt = Config::NT0; nt <= Config::NT1; nt += Config::DNT) {
        fluid::Backend::load_active_frame(fluid::Backend::frame_path(Config::DATA, nt));
        for (size_t i = 0; i < Config::NU.size(); i++) {
            const auto start = std::chrono::high_resolution_clock::now();
            fast_light::compute_image(rays, sampling, Config::NU[i], image);
            const double value = flux_jy(image);
            if (!std::isfinite(value)) {
                throw std::runtime_error("Non-finite flux at frame " + std::to_string(nt));
            }
            stats[i].add(value);
            const auto end = std::chrono::high_resolution_clock::now();
            const std::chrono::duration<double> duration = end - start;
            std::cout << std::setprecision(10)
                << "Flux frame: nt=" << nt
                << " nu_GHz=" << Config::NU[i] / 1e9
                << " flux_jy=" << value
                << " runtime=" << duration.count() << " s\n";
        }
    }

    for (size_t i = 0; i < Config::NU.size(); i++) {
        print_summary(Config::NU[i], stats[i]);
    }
}

} // namespace

namespace flux_app {

int run() {
    try {
        print_config();
        run_flux();
        return 0;
    }
    catch (const std::exception& error) {
        std::cerr << "Fatal error: " << error.what() << "\n";
        return 1;
    }
}

} // namespace flux_app

#endif
