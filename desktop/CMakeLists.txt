cmake_minimum_required(VERSION 3.22)

project(CoportSL LANGUAGES CXX)

include(CTest)

get_filename_component(COPORTSL_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/.." ABSOLUTE)
if(NOT EXISTS "${COPORTSL_ROOT}/apps" OR
   NOT EXISTS "${COPORTSL_ROOT}/src" OR
   NOT EXISTS "${COPORTSL_ROOT}/tools" OR
   NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/native/apps" OR
   NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/native/src")
    message(FATAL_ERROR
        "The CoportSL monorepo layout is incomplete at '${COPORTSL_ROOT}'.")
endif()

# Generate a complete source tree in the build directory: the core source code is used as the basis, and the desktop diff files are subsequently overwritten.
# In this way, short include in the same directory still has the original semantics, and Git no longer saves copies of public files.
set(COPORTSL_SOURCE_TREE "${CMAKE_BINARY_DIR}/source")
file(REMOVE_RECURSE "${COPORTSL_SOURCE_TREE}")
file(MAKE_DIRECTORY "${COPORTSL_SOURCE_TREE}")
file(COPY "${COPORTSL_ROOT}/apps" DESTINATION "${COPORTSL_SOURCE_TREE}")
file(COPY "${COPORTSL_ROOT}/src" DESTINATION "${COPORTSL_SOURCE_TREE}")

# CMake's directory-copy operation skips a destination file when it is newer
# than its source. Apply every desktop overlay file explicitly so a recently
# edited core file cannot silently replace its runtime-configurable counterpart.
file(GLOB_RECURSE COPORTSL_DESKTOP_OVERLAY_FILES
    LIST_DIRECTORIES false
    RELATIVE "${CMAKE_CURRENT_SOURCE_DIR}/native"
    "${CMAKE_CURRENT_SOURCE_DIR}/native/apps/*"
    "${CMAKE_CURRENT_SOURCE_DIR}/native/src/*")
foreach(relative IN LISTS COPORTSL_DESKTOP_OVERLAY_FILES)
    get_filename_component(relative_directory "${relative}" DIRECTORY)
    file(MAKE_DIRECTORY "${COPORTSL_SOURCE_TREE}/${relative_directory}")
    file(COPY_FILE
        "${CMAKE_CURRENT_SOURCE_DIR}/native/${relative}"
        "${COPORTSL_SOURCE_TREE}/${relative}")
endforeach()

function(coportsl_resolve_sources output)
    set(resolved)
    foreach(relative IN LISTS ARGN)
        if(relative MATCHES "^(apps|src)/")
            if(NOT EXISTS "${COPORTSL_SOURCE_TREE}/${relative}")
                message(FATAL_ERROR "Required source file is missing: ${relative}")
            endif()
            list(APPEND resolved "${COPORTSL_SOURCE_TREE}/${relative}")
        elseif(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${relative}")
            list(APPEND resolved "${CMAKE_CURRENT_SOURCE_DIR}/${relative}")
        else()
            message(FATAL_ERROR "Required source file is missing: ${relative}")
        endif()
    endforeach()
    set(${output} "${resolved}" PARENT_SCOPE)
endfunction()

function(coportsl_add_executable target)
    coportsl_resolve_sources(resolved ${ARGN})
    add_executable(${target} ${resolved})
endfunction()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

find_package(OpenMP REQUIRED COMPONENTS CXX)

set(COPORTSL_COMMON_SOURCES
    src/config/NumberExpression.cpp
    src/config/Runtime.cpp
    src/grrt/ConfigCompatibility.cpp
    src/grrt/ImageError.cpp
    src/physics/fluid/FrameSequence.cpp
    src/support/Sha256.cpp
    src/support/Signature.cpp
    src/support/Event.cpp
)

set(COPORTSL_FAST_SOURCES
    src/physics/fluid/bhac/BhacBackend.cpp
    src/physics/fluid/bhac/BhacIdentity.cpp
    src/physics/fluid/FrameDiscovery.cpp
    src/physics/fluid/GridLocations.cpp
    src/grrt/SampleTransfer.cpp
    src/grrt/StokesProjection.cpp
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
    target_include_directories(
        ${target} PRIVATE
        "${COPORTSL_SOURCE_TREE}"
        "${COPORTSL_ROOT}")
    target_link_libraries(${target} PRIVATE OpenMP::OpenMP_CXX)
    if(MSVC)
        target_compile_options(${target} PRIVATE /utf-8)
    endif()
endfunction()

coportsl_add_executable(GRRT
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
    COPORTSL_SOURCE_ROOT="${COPORTSL_ROOT}")
coportsl_target(GRRT)

coportsl_add_executable(Flux
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

coportsl_add_executable(Benchmark
    apps/Main.cpp
    apps/benchmark/Benchmark.cpp
    apps/benchmark/Timing.cpp
    ${COPORTSL_BENCHMARK_CPU}
    ${COPORTSL_COMMON_SOURCES}
    ${COPORTSL_FAST_SOURCES}
    ${COPORTSL_SLOW_SOURCES}
    src/grrt/fast/RegionStats.cpp
    src/grrt/ConfigOutput.cpp
    src/grrt/Signatures.cpp
    src/support/RunDirectory.cpp
    src/grrt/slow/Analysis.cpp
    src/grrt/slow/AnalysisOutput.cpp
    src/grrt/slow/TimeOffsetStats.cpp
    src/grrt/slow/regions/RegionSelector.cpp
    src/physics/transfer/TransferSupport.cpp
)
target_compile_definitions(
    Benchmark PRIVATE COPORTSL_APP=2)
coportsl_target(Benchmark)

if(BUILD_TESTING AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/tests")
    coportsl_add_executable(NumberExpressionTests
        tests/cpp/NumberExpressionTests.cpp
        src/config/NumberExpression.cpp
    )
    target_include_directories(
        NumberExpressionTests PRIVATE
        "${COPORTSL_SOURCE_TREE}" "${COPORTSL_ROOT}")
    if(MSVC)
        target_compile_options(NumberExpressionTests PRIVATE /utf-8)
    endif()
    add_test(NAME number-expression COMMAND NumberExpressionTests)

    coportsl_add_executable(AnalyticalSolutionTests
        tests/cpp/AnalyticalSolutionTests.cpp
        src/physics/transfer/AnalyticalSolution.cpp
        src/support/numerics/LinearAlgebra.cpp
    )
    target_include_directories(
        AnalyticalSolutionTests PRIVATE
        "${COPORTSL_SOURCE_TREE}" "${COPORTSL_ROOT}")
    if(MSVC)
        target_compile_options(AnalyticalSolutionTests PRIVATE /utf-8)
    endif()
    add_test(NAME analytical-solution COMMAND AnalyticalSolutionTests)

    coportsl_add_executable(ConfigCompatibilityTests
        tests/cpp/ConfigCompatibilityTests.cpp
        src/grrt/ConfigCompatibility.cpp
    )
    target_include_directories(
        ConfigCompatibilityTests PRIVATE
        "${COPORTSL_SOURCE_TREE}" "${COPORTSL_ROOT}")
    if(MSVC)
        target_compile_options(ConfigCompatibilityTests PRIVATE /utf-8)
    endif()
    add_test(NAME config-compatibility COMMAND ConfigCompatibilityTests)

    coportsl_add_executable(TimeOffsetStatsTests
        tests/cpp/TimeOffsetStatsTests.cpp
        src/grrt/slow/TimeOffsetStats.cpp
    )
    target_include_directories(
        TimeOffsetStatsTests PRIVATE
        "${COPORTSL_SOURCE_TREE}" "${COPORTSL_ROOT}")
    if(MSVC)
        target_compile_options(TimeOffsetStatsTests PRIVATE /utf-8)
    endif()
    add_test(NAME time-offset-stats COMMAND TimeOffsetStatsTests)

    coportsl_add_executable(FrameSequenceTests
        tests/cpp/FrameSequenceTests.cpp
        src/physics/fluid/FrameSequence.cpp
    )
    target_include_directories(
        FrameSequenceTests PRIVATE
        "${COPORTSL_SOURCE_TREE}" "${COPORTSL_ROOT}")
    if(MSVC)
        target_compile_options(FrameSequenceTests PRIVATE /utf-8)
    endif()
    add_test(NAME frame-sequence COMMAND FrameSequenceTests)

    coportsl_add_executable(RunRecoveryTests
        tests/cpp/RunRecoveryTests.cpp
        src/grrt/Resume.cpp
        src/support/RunDirectory.cpp
    )
    target_include_directories(
        RunRecoveryTests PRIVATE
        "${COPORTSL_SOURCE_TREE}" "${COPORTSL_ROOT}")
    if(MSVC)
        target_compile_options(RunRecoveryTests PRIVATE /utf-8)
    endif()
    add_test(NAME run-recovery COMMAND RunRecoveryTests)

    add_test(NAME grrt-show-app COMMAND GRRT --show-app)
    set_tests_properties(
        grrt-show-app PROPERTIES
        PASS_REGULAR_EXPRESSION "^grrt")
    add_test(NAME flux-show-app COMMAND Flux --show-app)
    set_tests_properties(
        flux-show-app PROPERTIES
        PASS_REGULAR_EXPRESSION "^flux")
    add_test(NAME benchmark-show-app COMMAND Benchmark --show-app)
    set_tests_properties(
        benchmark-show-app PROPERTIES
        PASS_REGULAR_EXPRESSION "^benchmark")
    add_test(
        NAME grrt-valid-config
        COMMAND GRRT --validate-config
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/grrt-fast.json")
    add_test(
        NAME grrt-expression-config
        COMMAND GRRT --validate-config
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/grrt-expression.json")
    add_test(
        NAME benchmark-expression-config
        COMMAND Benchmark --validate-config
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/benchmark-expression.json")
    add_test(
        NAME grrt-invalid-config
        COMMAND GRRT --validate-config
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/grrt-invalid.json")
    set_tests_properties(grrt-invalid-config PROPERTIES WILL_FAIL TRUE)
endif()
