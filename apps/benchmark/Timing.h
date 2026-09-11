#pragma once

#include <chrono>
#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

#include "src/physics/fluid/BackendTypes.h"

namespace benchmark {

using Clock = std::chrono::steady_clock;

struct CpuSet {
    unsigned long id = 0;
    uint32_t group = 0;
    uint32_t logical_index = 0;
    uint32_t core_index = 0;
    uint32_t efficiency_class = 0;
};

struct CpuSelection {
    std::string mode;
    int requested_threads = 0;
    int actual_threads = 0;
    std::vector<CpuSet> available;
    std::vector<CpuSet> selected;
};

struct TimingRecord {
    uint64_t rays = 0;
    uint64_t samples = 0;
    bool warmup = false;
    double frame_update_s = 0.0;
    double transfer_s = 0.0;
};

double seconds(Clock::time_point begin, Clock::time_point end);
std::string cpu_name();
CpuSelection select_cpu_sets(const std::string& mode, int threads);
void write_summary(
    const std::filesystem::path& file,
    const std::string& light,
    int npix,
    int cores,
    size_t grid_points,
    size_t grid_bytes,
    size_t frame_bytes,
    const std::vector<TimingRecord>& records);

} // namespace benchmark
