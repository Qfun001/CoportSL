#pragma once

#include <string_view>

// Visual Studio users only need to modify the default value of COPORTSL_APP.
#define COPORTSL_GRRT 0
#define COPORTSL_FLUX 1
#define COPORTSL_BENCHMARK 2

#ifndef COPORTSL_APP
#define COPORTSL_APP COPORTSL_GRRT
#endif

#if COPORTSL_APP == COPORTSL_GRRT
#include "grrt/GRRTConfig.h"
#elif COPORTSL_APP == COPORTSL_FLUX
#include "flux/FluxConfig.h"
#elif COPORTSL_APP == COPORTSL_BENCHMARK
#include "benchmark/BenchmarkConfig.h"
#else
#error "Unsupported CoportSL application."
#endif

namespace Application {

#if COPORTSL_APP == COPORTSL_GRRT
inline constexpr std::string_view NAME = "grrt";
#elif COPORTSL_APP == COPORTSL_FLUX
inline constexpr std::string_view NAME = "flux";
#else
inline constexpr std::string_view NAME = "benchmark";
#endif

} // namespace Application
