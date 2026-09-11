cmake_minimum_required(VERSION 3.22)

project(CoportSL LANGUAGES CXX)

include(CTest)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

find_package(OpenMP REQUIRED COMPONENTS CXX)

set(COPORTSL_COMMON_SOURCES
    src/grrt/ConfigCompatibility.cpp
    src/grrt/ImageError.cpp
    src/physics/fluid/FrameSequence.cpp
    src/support/Sha256.cpp
    src/support/Signature.cpp
)

set(COPORTSL_FAST_SOURCES
    src/physics/fluid/Scaling.cpp
    src/physics/fluid/bhac/BhacBackend.cpp
    src/physics/fluid/bhac/BhacIdentity.cpp
    src/physics/fluid/FrameDiscovery.cpp
    src/physics/fluid/GridLocations.cpp
    src/grrt/SampleTransfer.cpp
    src/grrt/TransferSample.cpp
    src/grrt/StokesProjection.cpp
    src/grrt/fast/AnalyticTransfer.cpp
    src/physics/medium/Coefficients.cpp
    src/physics/medium/analytic/Slab.cpp
    src/physics/transfer/AnalyticalSolution.cpp
    src/grrt/RayGeometry.cpp
    src/grrt/fast/FastTransfer.cpp
    src/physics/spacetime/Geodesic.cpp
    src/support/numerics/LinearAlgebra.cpp
    src/physics/spacetime/Metric.cpp
    src/physics/transfer/NonthermalDistribution.cpp
    src/physics/transfer/PlasmaRadiation.cpp
    src/physics/fluid/bhac/Reader.cpp
    src/physics/transfer/ThermalDistribution.cpp
)

set(COPORTSL_SLOW_SOURCES
    src/physics/fluid/FrameCache.cpp
    src/grrt/slow/AnalysisStore.cpp
    src/grrt/slow/regions/Region.cpp
    src/grrt/slow/regions/RegionDefinition.cpp
    src/grrt/slow/regions/definitions/JetShell.cpp
    src/grrt/slow/regions/definitions/Shell.cpp
    src/grrt/slow/TimeOrigin.cpp
    src/grrt/slow/SlowTransfer.cpp
)

function(coportsl_target target)
    target_include_directories(${target} PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
    target_link_libraries(${target} PRIVATE OpenMP::OpenMP_CXX)
    if(MSVC)
        target_compile_options(${target} PRIVATE /utf-8)
    endif()
endfunction()

add_executable(GRRT
    apps/Main.cpp
    apps/grrt/GRRT.cpp
    apps/grrt/Postprocess.cpp
    src/grrt/ConfigOutput.cpp
    src/grrt/ResultOutput.cpp
    src/grrt/Resume.cpp
    src/grrt/Signatures.cpp
    ${COPORTSL_COMMON_SOURCES}
    ${COPORTSL_FAST_SOURCES}
    ${COPORTSL_SLOW_SOURCES}
    src/grrt/fast/RegionStats.cpp
    src/grrt/fast/RegionExclusion.cpp
    src/support/RunDirectory.cpp
    src/grrt/slow/Analysis.cpp
    src/grrt/slow/AnalysisOutput.cpp
    src/grrt/slow/TimeOffsetStats.cpp
    src/grrt/slow/regions/RegionSelector.cpp
    src/physics/transfer/TransferSupport.cpp
)
target_compile_definitions(
    GRRT PRIVATE
    COPORTSL_APP=0
    COPORTSL_SOURCE_ROOT="${CMAKE_CURRENT_SOURCE_DIR}")
coportsl_target(GRRT)

add_executable(Flux
    apps/Main.cpp
    apps/flux/Flux.cpp
    ${COPORTSL_COMMON_SOURCES}
    ${COPORTSL_FAST_SOURCES}
)
target_compile_definitions(
    Flux PRIVATE COPORTSL_APP=1)
coportsl_target(Flux)

if(WIN32)
    set(COPORTSL_BENCHMARK_CPU apps/benchmark/platform/CpuWindows.cpp)
elseif(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    set(COPORTSL_BENCHMARK_CPU apps/benchmark/platform/CpuLinux.cpp)
else()
    message(FATAL_ERROR "Benchmark CPU selection supports only Windows and Linux.")
endif()

add_executable(Benchmark
    apps/Main.cpp
    apps/benchmark/Benchmark.cpp
    apps/benchmark/Timing.cpp
    ${COPORTSL_BENCHMARK_CPU}
    ${COPORTSL_COMMON_SOURCES}
    ${COPORTSL_FAST_SOURCES}
    ${COPORTSL_SLOW_SOURCES}
    src/grrt/ConfigOutput.cpp
    src/grrt/Signatures.cpp
    src/support/RunDirectory.cpp
)
target_compile_definitions(
    Benchmark PRIVATE COPORTSL_APP=2)
coportsl_target(Benchmark)

if(BUILD_TESTING AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/tests")
    add_executable(HarmpiReaderTests
        tests/cpp/HarmpiReaderTests.cpp
        src/physics/fluid/Scaling.cpp
        src/physics/fluid/harmpi/Coordinates.cpp
        src/physics/fluid/harmpi/HarmpiBackend.cpp
        src/physics/fluid/harmpi/HarmpiIdentity.cpp
        src/physics/fluid/harmpi/Reader.cpp
        src/physics/fluid/harmpi/Sampler.cpp
        src/physics/fluid/FrameSequence.cpp
        src/grrt/slow/regions/RegionDefinition.cpp
        src/grrt/slow/regions/definitions/JetShell.cpp
        src/grrt/slow/regions/definitions/Shell.cpp
        src/physics/spacetime/Metric.cpp
        src/support/Sha256.cpp
        src/support/Signature.cpp
    )
    target_include_directories(
        HarmpiReaderTests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
    if(MSVC)
        target_compile_options(HarmpiReaderTests PRIVATE /utf-8)
    endif()
    add_test(NAME harmpi-reader COMMAND HarmpiReaderTests)

    add_executable(AnalyticMediumTests
        tests/cpp/AnalyticMediumTests.cpp
        src/grrt/fast/AnalyticTransfer.cpp
        src/grrt/TransferSample.cpp
        src/grrt/StokesProjection.cpp
        src/physics/medium/Coefficients.cpp
        src/physics/medium/analytic/Slab.cpp
        src/physics/transfer/AnalyticalSolution.cpp
        src/physics/spacetime/Metric.cpp
        src/support/numerics/LinearAlgebra.cpp
        src/grrt/slow/regions/RegionDefinition.cpp
        src/grrt/slow/regions/definitions/JetShell.cpp
        src/grrt/slow/regions/definitions/Shell.cpp
    )
    target_compile_definitions(AnalyticMediumTests PRIVATE COPORTSL_APP=0)
    coportsl_target(AnalyticMediumTests)
    add_test(NAME analytic-medium COMMAND AnalyticMediumTests)

    add_executable(AnalyticalSolutionTests
        tests/cpp/AnalyticalSolutionTests.cpp
        src/physics/transfer/AnalyticalSolution.cpp
        src/support/numerics/LinearAlgebra.cpp
    )
    target_include_directories(
        AnalyticalSolutionTests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
    if(MSVC)
        target_compile_options(AnalyticalSolutionTests PRIVATE /utf-8)
    endif()
    add_test(NAME analytical-solution COMMAND AnalyticalSolutionTests)

    add_executable(TimeOffsetStatsTests
        tests/cpp/TimeOffsetStatsTests.cpp
        src/grrt/slow/TimeOffsetStats.cpp
    )
    target_include_directories(
        TimeOffsetStatsTests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
    if(MSVC)
        target_compile_options(TimeOffsetStatsTests PRIVATE /utf-8)
    endif()
    add_test(NAME time-offset-stats COMMAND TimeOffsetStatsTests)

    add_executable(BhacReaderTests
        tests/cpp/BhacReaderTests.cpp
        ${COPORTSL_COMMON_SOURCES}
        ${COPORTSL_FAST_SOURCES}
        src/grrt/slow/regions/RegionDefinition.cpp
        src/grrt/slow/regions/definitions/JetShell.cpp
        src/grrt/slow/regions/definitions/Shell.cpp
    )
    target_compile_definitions(BhacReaderTests PRIVATE COPORTSL_APP=0)
    coportsl_target(BhacReaderTests)
    add_test(NAME bhac-reader COMMAND BhacReaderTests)

    add_executable(OutputFileTests
        tests/cpp/OutputFileTests.cpp
    )
    target_include_directories(
        OutputFileTests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
    if(MSVC)
        target_compile_options(OutputFileTests PRIVATE /utf-8)
    endif()
    add_test(NAME output-file COMMAND OutputFileTests)

    add_executable(RunDirectoryTests
        tests/cpp/RunDirectoryTests.cpp
        src/support/RunDirectory.cpp
    )
    target_include_directories(
        RunDirectoryTests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
    if(MSVC)
        target_compile_options(RunDirectoryTests PRIVATE /utf-8)
    endif()
    add_test(NAME run-directory COMMAND RunDirectoryTests)

    add_executable(SignatureTests
        tests/cpp/SignatureTests.cpp
        src/grrt/Signatures.cpp
        src/grrt/slow/regions/RegionDefinition.cpp
        src/grrt/slow/regions/definitions/JetShell.cpp
        src/grrt/slow/regions/definitions/Shell.cpp
        src/physics/fluid/FrameSequence.cpp
        src/physics/fluid/bhac/BhacIdentity.cpp
        src/physics/spacetime/Metric.cpp
        src/support/Sha256.cpp
        src/support/Signature.cpp
    )
    target_compile_definitions(SignatureTests PRIVATE COPORTSL_APP=0)
    target_include_directories(
        SignatureTests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
    if(MSVC)
        target_compile_options(SignatureTests PRIVATE /utf-8)
    endif()
    add_test(NAME signatures COMMAND SignatureTests)

    add_executable(ConfigCompatibilityTests
        tests/cpp/ConfigCompatibilityTests.cpp
        src/grrt/ConfigCompatibility.cpp
    )
    target_include_directories(
        ConfigCompatibilityTests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
    if(MSVC)
        target_compile_options(ConfigCompatibilityTests PRIVATE /utf-8)
    endif()
    add_test(NAME config-compatibility COMMAND ConfigCompatibilityTests)

    add_executable(AnalysisCompatibilityTests
        tests/cpp/AnalysisCompatibilityTests.cpp
        src/grrt/ConfigCompatibility.cpp
        src/grrt/slow/AnalysisStore.cpp
        src/grrt/slow/regions/Region.cpp
        src/grrt/slow/regions/RegionDefinition.cpp
        src/grrt/slow/regions/definitions/JetShell.cpp
        src/grrt/slow/regions/definitions/Shell.cpp
        src/physics/fluid/FrameSequence.cpp
        src/physics/spacetime/Metric.cpp
        src/support/RunDirectory.cpp
    )
    target_compile_definitions(AnalysisCompatibilityTests PRIVATE COPORTSL_APP=0)
    target_include_directories(
        AnalysisCompatibilityTests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
    if(MSVC)
        target_compile_options(AnalysisCompatibilityTests PRIVATE /utf-8)
    endif()
    add_test(NAME analysis-compatibility COMMAND AnalysisCompatibilityTests)

    add_executable(RunRecoveryTests
        tests/cpp/RunRecoveryTests.cpp
        src/grrt/Resume.cpp
        src/support/RunDirectory.cpp
    )
    target_include_directories(
        RunRecoveryTests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
    if(MSVC)
        target_compile_options(RunRecoveryTests PRIVATE /utf-8)
    endif()
    add_test(NAME run-recovery COMMAND RunRecoveryTests)

    add_executable(FrameSequenceTests
        tests/cpp/FrameSequenceTests.cpp
        src/physics/fluid/FrameSequence.cpp
    )
    target_include_directories(
        FrameSequenceTests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
    if(MSVC)
        target_compile_options(FrameSequenceTests PRIVATE /utf-8)
    endif()
    add_test(NAME frame-sequence COMMAND FrameSequenceTests)

    add_test(NAME grrt-show-app COMMAND GRRT --show-app)
    set_tests_properties(
        grrt-show-app PROPERTIES PASS_REGULAR_EXPRESSION "^grrt")
    add_test(NAME flux-show-app COMMAND Flux --show-app)
    set_tests_properties(
        flux-show-app PROPERTIES PASS_REGULAR_EXPRESSION "^flux")
    add_test(NAME benchmark-show-app COMMAND Benchmark --show-app)
    set_tests_properties(
        benchmark-show-app PROPERTIES PASS_REGULAR_EXPRESSION "^benchmark")
endif()
