#include "apps/benchmark/Timing.h"

#include <algorithm>
#include <cstring>
#include <set>
#include <stdexcept>
#include <vector>

#define NOMINMAX
#include <Windows.h>
#include <intrin.h>

namespace benchmark {

namespace {

std::vector<CpuSet> discover_cpu_sets() {
    ULONG length = 0;
    if (GetSystemCpuSetInformation(nullptr, 0, &length, GetCurrentProcess(), 0) ||
        GetLastError() != ERROR_INSUFFICIENT_BUFFER) {
        throw std::runtime_error("Unable to query Windows CPU set information size.");
    }

    std::vector<unsigned char> buffer(length);
    if (!GetSystemCpuSetInformation(
        reinterpret_cast<PSYSTEM_CPU_SET_INFORMATION>(buffer.data()),
        length,
        &length,
        GetCurrentProcess(),
        0)) {
        throw std::runtime_error("Unable to query Windows CPU set information.");
    }

    std::vector<CpuSet> sets;
    ULONG offset = 0;
    while (offset < length) {
        const auto* info = reinterpret_cast<const SYSTEM_CPU_SET_INFORMATION*>(
            buffer.data() + offset);
        if (info->Type == CpuSetInformation) {
            const auto& cpu = info->CpuSet;
            sets.push_back({
                cpu.Id,
                cpu.Group,
                cpu.LogicalProcessorIndex,
                cpu.CoreIndex,
                cpu.EfficiencyClass
            });
        }
        offset += info->Size;
    }
    std::sort(sets.begin(), sets.end(), [](const CpuSet& a, const CpuSet& b) {
        if (a.efficiency_class != b.efficiency_class) {
            return a.efficiency_class > b.efficiency_class;
        }
        if (a.group != b.group) return a.group < b.group;
        return a.logical_index < b.logical_index;
    });
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

} // namespace

std::string cpu_name() {
    int data[4] = {};
    char name[49] = {};
    for (int leaf = 0; leaf < 3; leaf++) {
        __cpuid(data, 0x80000002 + leaf);
        std::memcpy(name + leaf * 16, data, 16);
    }
    return std::string(name);
}

CpuSelection select_cpu_sets(const std::string& mode, int threads) {
    if (threads <= 0) {
        throw std::invalid_argument("Benchmark thread count must be positive.");
    }

    CpuSelection result;
    result.mode = mode;
    result.requested_threads = threads;
    result.available = discover_cpu_sets();
    if (result.available.empty()) {
        throw std::runtime_error("Windows did not report any CPU sets.");
    }

    std::vector<CpuSet> candidates;
    if (mode == "all_logical") {
        candidates = result.available;
    }
    else if (mode == "physical_cores" ||
        mode == "performance_cores" || mode == "efficiency_cores") {
        candidates = one_per_core(result.available);
        if (mode == "performance_cores" || mode == "efficiency_cores") {
            const auto classes = std::minmax_element(
                candidates.begin(),
                candidates.end(),
                [](const CpuSet& a, const CpuSet& b) {
                    return a.efficiency_class < b.efficiency_class;
                });
            const uint32_t target = mode == "performance_cores" ?
                classes.second->efficiency_class : classes.first->efficiency_class;
            std::erase_if(candidates, [target](const CpuSet& cpu) {
                return cpu.efficiency_class != target;
            });
        }
    }
    else {
        throw std::invalid_argument("Unknown benchmark CPU mode: " + mode);
    }

    if (static_cast<size_t>(threads) > candidates.size()) {
        throw std::runtime_error(
            "Requested benchmark threads exceed the selected CPU-set group.");
    }
    result.selected.assign(candidates.begin(), candidates.begin() + threads);
    std::vector<ULONG> ids;
    ids.reserve(result.selected.size());
    for (const CpuSet& cpu : result.selected) ids.push_back(cpu.id);
    if (!SetProcessDefaultCpuSets(
        GetCurrentProcess(), ids.data(), static_cast<ULONG>(ids.size()))) {
        throw std::runtime_error("Unable to apply the requested Windows CPU sets.");
    }
    return result;
}

} // namespace benchmark
