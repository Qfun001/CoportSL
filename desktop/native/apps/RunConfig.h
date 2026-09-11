#pragma once

#include <string_view>

#define COPORTSL_GRRT 0
#define COPORTSL_FLUX 1
#define COPORTSL_BENCHMARK 2

#ifndef COPORTSL_APP
#define COPORTSL_APP COPORTSL_GRRT
#endif

// Resolve from the overlay root to avoid preemptive matching of configuration headers with the same name in the shared core directory.
#if COPORTSL_APP == COPORTSL_GRRT
#include "apps/grrt/GRRTConfig.h"
#elif COPORTSL_APP == COPORTSL_FLUX
#include "apps/flux/FluxConfig.h"
#elif COPORTSL_APP == COPORTSL_BENCHMARK
#include "apps/benchmark/BenchmarkConfig.h"
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
