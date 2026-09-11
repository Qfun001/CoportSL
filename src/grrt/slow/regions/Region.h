#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace slow_light::regions {

using RegionId = uint32_t;
using Position = std::array<double, 4>;
using PositionAt = std::function<Position(size_t)>;

struct RegionInfo {
    std::string key;
    std::string label;
};

struct RegionDefinition {
    std::string name;
    std::string signature;
    std::vector<RegionInfo> regions;
    std::function<std::optional<RegionId>(const Position&)> locate;
};

struct RegionSelection {
    std::string name;
    std::vector<std::string> keys;
};

struct RegionPartition {
    std::string name;
    std::string definition_hash;
    std::vector<RegionInfo> regions;
    std::vector<RegionId> sample_regions;

    size_t region_count() const noexcept;
    size_t sample_count() const noexcept;
};

struct SampleMask {
    std::string name;
    std::vector<uint8_t> selected;

    size_t size() const noexcept;
    bool operator[](size_t index) const noexcept;
};

RegionPartition build_partition(
    size_t sample_count,
    const PositionAt& position_at,
    const RegionDefinition& definition);

template <typename Sample>
RegionPartition build_partition(
    const std::vector<Sample>& samples,
    const RegionDefinition& definition) {

    return build_partition(
        samples.size(),
        [&samples](size_t index) {
            const Sample& sample = samples[index];
            return Position{ 0.0, sample.x[0], sample.x[1], sample.x[2] };
        },
        definition);
}

SampleMask select_regions(
    const RegionPartition& partition,
    const RegionSelection& selection);

// Verify that collection names are unique and resolve independently; there is no requirement that collections be nested or have a precedence order.
std::vector<SampleMask> select_region_sets(
    const RegionPartition& partition,
    std::span<const RegionSelection> selections);

std::vector<RegionId> resolve_regions(
    const RegionPartition& partition,
    const RegionSelection& selection);

std::string definition_hash(const RegionDefinition& definition);

void validate_partition(
    const RegionPartition& partition,
    size_t expected_size,
    std::string_view object_name);

void validate_mask(
    const SampleMask& mask,
    size_t expected_size,
    std::string_view object_name,
    bool require_selected = true);

} // namespace slow_light::regions
