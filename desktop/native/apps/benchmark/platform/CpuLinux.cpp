#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include "apps/benchmark/Timing.h"

#include <cerrno>
#include <cstring>
#include <fstream>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>

#include <sched.h>

namespace benchmark {

namespace {

uint32_t read_topology_value(int cpu, const char* name, uint32_t fallback) {
    const std::filesystem::path file =
        std::filesystem::path("/sys/devices/system/cpu") /
        ("cpu" + std::to_string(cpu)) / "topology" / name;
    std::ifstream in(file);
    uint32_t value = fallback;
    if (in >> value) return value;
    return fallback;
}

std::vector<CpuSet> discover_cpu_sets() {
    cpu_set_t allowed;
    CPU_ZERO(&allowed);
    if (sched_getaffinity(0, sizeof(allowed), &allowed) != 0) {
        throw std::runtime_error(
            "Unable to query Linux CPU affinity: " + std::string(std::strerror(errno)));
    }

    std::vector<CpuSet> sets;
    for (int cpu = 0; cpu < CPU_SETSIZE; cpu++) {
        if (!CPU_ISSET(cpu, &allowed)) continue;
        const uint32_t logical = static_cast<uint32_t>(cpu);
        sets.push_back({
            static_cast<unsigned long>(cpu),
            read_topology_value(cpu, "physical_package_id", 0),
            logical,
            read_topology_value(cpu, "core_id", logical),
            0
        });
    }
    return sets;
}

std::vector<CpuSet> one_per_core(const std::vector<CpuSet>& sets) {
    std::set<std::pair<uint32_t, uint32_t>> used;
    std::vector<CpuSet> selected;
    for (const CpuSet& cpu : sets) {
        if (used.insert({ cpu.group, cpu.core_index }).second) {
            selected.push_back(cpu);
        }
    }
    return selected;
}

std::string trimmed_value(const std::string& line) {
    const size_t colon = line.find(':');
    if (colon == std::string::npos) return {};
    const size_t begin = line.find_first_not_of(" \t", colon + 1);
    if (begin == std::string::npos) return {};
    const size_t end = line.find_last_not_of(" \t\r\n");
    return line.substr(begin, end - begin + 1);
}

} // namespace

std::string cpu_name() {
    std::ifstream in("/proc/cpuinfo");
    std::string line;
    while (std::getline(in, line)) {
        if (line.starts_with("model name") || line.starts_with("Hardware")) {
            const std::string name = trimmed_value(line);
            if (!name.empty()) return name;
        }
    }
    return "unknown Linux CPU";
}

CpuSelection select_cpu_sets(const std::string& mode, int threads) {
    if (threads <= 0) {
        throw std::invalid_argument("Benchmark thread count must be positive.");
    }

    CpuSelection result;
    result.mode = mode;
    result.requested_threads = threads;
    // sched_setaffinity will change the result of subsequent sched_getaffinity, so the initial set is cached.
    static const std::vector<CpuSet> available = discover_cpu_sets();
    result.available = available;
    if (result.available.empty()) {
        throw std::runtime_error("Linux affinity mask does not contain any CPUs.");
    }

    std::vector<CpuSet> candidates;
    if (mode == "all_logical") {
        candidates = result.available;
    }
    else if (mode == "physical_cores") {
        candidates = one_per_core(result.available);
    }
    else if (mode == "performance_cores" || mode == "efficiency_cores") {
        throw std::runtime_error(
            "Linux/WSL does not expose a reliable performance/efficiency core class; "
            "use all_logical or physical_cores.");
    }
    else {
        throw std::invalid_argument("Unknown benchmark CPU mode: " + mode);
    }

    if (static_cast<size_t>(threads) > candidates.size()) {
        throw std::runtime_error(
            "Requested benchmark threads exceed the selected Linux CPU group.");
    }
    result.selected.assign(candidates.begin(), candidates.begin() + threads);

    cpu_set_t selected;
    CPU_ZERO(&selected);
    for (const CpuSet& cpu : result.selected) {
        CPU_SET(static_cast<int>(cpu.id), &selected);
    }
    if (sched_setaffinity(0, sizeof(selected), &selected) != 0) {
        throw std::runtime_error(
            "Unable to apply Linux CPU affinity: " + std::string(std::strerror(errno)));
    }
    return result;
}

} // namespace benchmark
