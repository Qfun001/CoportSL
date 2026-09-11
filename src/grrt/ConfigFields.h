#pragma once

#include <cstdint>
#include <ostream>
#include <string>
#include <string_view>
#include <utility>

#include "apps/RunConfig.h"
#include "src/grrt/slow/TimeOrigin.h"
#include "src/physics/Model.h"
#include "src/physics/fluid/FluidBackend.h"
#include "src/physics/fluid/FrameSequence.h"

namespace grrt {

// Enumerations use integers in stable signatures and canonical literals in user-facing configuration.
struct NamedInt {
    int64_t value = 0;
    std::string_view name;
};

// Only used for result configuration and does not enter model signature.
struct OutputOnlyString {
    std::string_view value;
};

struct ConfigFieldWriter {
    std::ostream& out;

    void operator()(std::string_view name, int64_t value) const {
        out << name << "=" << value << "\n";
    }

    void operator()(std::string_view name, double value) const {
        out << name << "=" << value << "\n";
    }

    void operator()(std::string_view name, std::string_view value) const {
        out << name << "=" << value << "\n";
    }

    void operator()(std::string_view name, NamedInt value) const {
        out << name << "=" << value.name << "\n";
    }

    void operator()(std::string_view name, OutputOnlyString value) const {
        out << name << "=" << value.value << "\n";
    }
};

template <typename Visitor>
void visit_model_fields(
    const fluid::FrameSequence& sequence,
    Visitor&& visitor) {

    visitor(
        "Config::FLUID_BACKEND",
        OutputOnlyString{fluid::Backend::name()});
    visitor("Input::T0", sequence.first().time);
    visitor("Input::DT", sequence.dt);
    if (sequence.uniform) {
        // Keep existing signatures for consecutive equally spaced BHAC jobs unchanged.
    }
    else {
        visitor("Input::CADENCE", std::string_view("irregular"));
        visitor(
            "Input::FRAME_COUNT",
            static_cast<int64_t>(sequence.frames.size()));
        for (size_t index = 0; index < sequence.frames.size(); index++) {
            const std::string prefix =
                "Input::FRAME." + std::to_string(index);
            visitor(
                prefix + ".INDEX",
                static_cast<int64_t>(sequence.frames[index].index));
            visitor(prefix + ".TIME", sequence.frames[index].time);
        }
    }
    visitor("Config::NPIX", static_cast<int64_t>(Config::NPIX));
    visitor("Config::FOV", Config::FOV);
    visitor("Config::NU", Config::NU);
    visitor("Config::OBS_T", Config::OBS_T);
    visitor("Config::OBS_R", Config::OBS_R);
    visitor("Config::OBS_TH", Config::OBS_TH);
    visitor("Config::OBS_PH", Config::OBS_PH);
    visitor("Config::METRIC", static_cast<int64_t>(Config::METRIC));
    visitor("Config::SPIN", Config::SPIN);
    visitor("Config::HS", Config::HS);
    visitor(
        "Config::ELECTRON",
        NamedInt{
            static_cast<int64_t>(Config::ELECTRON),
            ModelConstants::electron_model_name()});
    visitor("Config::MBH", Config::MBH);
    visitor("Config::MDOT", Config::MDOT);
    visitor("Config::MDOT_SIM", Config::MDOT_SIM);
    visitor("Config::R_LOW", Config::R_LOW);
    visitor("Config::R_HIGH", Config::R_HIGH);
    visitor("Config::BETA0", Config::BETA0);
    visitor("Config::SIGMA_MAX", Config::SIGMA_MAX);
    visitor("Config::THETAE_EMIT", Config::THETAE_EMIT);
    visitor("Config::NE_EMIT", Config::NE_EMIT);
    visitor("Config::POL_LIMIT", Config::POL_LIMIT);
    if constexpr (Config::ELECTRON != Config::THERMAL) {
        visitor("Config::P_MIN", Config::P_MIN);
        visitor("Config::P_MAX", Config::P_MAX);
        visitor("Config::GAMMA_RATIO", Config::GAMMA_RATIO);
    }
    if constexpr (Config::ELECTRON == Config::BEAM ||
        Config::ELECTRON == Config::LOSS_CONE) {
        visitor("Config::BEAM_ANGLE", Config::BEAM_ANGLE);
        visitor("Config::BEAM_WIDTH", Config::BEAM_WIDTH);
    }
    visitor("Config::RAY_ATOL", Config::RAY_ATOL);
    visitor("Config::RAY_RTOL", Config::RAY_RTOL);
    visitor("Config::RAY_HMIN", Config::RAY_HMIN);
    visitor("Config::RAY_LMAX", Config::RAY_LMAX);
    visitor("Config::RAY_H0", Config::RAY_H0);
    visitor("Config::RAY_CELL", Config::RAY_CELL);
    visitor("Config::RAY_HORIZON", Config::RAY_HORIZON);
    visitor("Config::R_SOURCE", Config::R_SOURCE);
}

template <typename Visitor>
void visit_analysis_fields(Visitor&& visitor) {
    visitor("Analysis::SAMPLE_DT", Analysis::SAMPLE_DT);
    visitor(
        "Analysis::REGION_TOLERANCES.jI",
        Analysis::REGION_TOLERANCES.jI);
    visitor(
        "Analysis::REGION_TOLERANCES.jP",
        Analysis::REGION_TOLERANCES.jP);
    visitor(
        "Analysis::REGION_TOLERANCES.aI",
        Analysis::REGION_TOLERANCES.aI);
    visitor(
        "Analysis::REGION_TOLERANCES.aP",
        Analysis::REGION_TOLERANCES.aP);
    visitor(
        "Analysis::REGION_TOLERANCES.rhoV",
        Analysis::REGION_TOLERANCES.rhoV);
    visitor(
        "Analysis::REGION_TOLERANCES.rhoC",
        Analysis::REGION_TOLERANCES.rhoC);
}

template <typename Visitor>
void visit_time_origin_fields(Visitor&& visitor) {
    visitor(
        "TimeOrigin::NAME",
        std::string_view(slow_light::time_origin::NAME));
    visitor("TimeOrigin::RADIUS", slow_light::time_origin::RADIUS);
}

} // namespace grrt
