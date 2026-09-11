#include "Region.h"

#include <algorithm>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>

namespace slow_light::regions {

size_t RegionPartition::region_count() const noexcept {
    return regions.size();
}

size_t RegionPartition::sample_count() const noexcept {
    return sample_regions.size();
}

size_t SampleMask::size() const noexcept {
    return selected.size();
}

bool SampleMask::operator[](size_t index) const noexcept {
    return selected[index] != 0;
}

RegionPartition build_partition(
    size_t sample_count,
    const PositionAt& position_at,
    const RegionDefinition& definition) {

    if (definition.name.empty()) {
        throw std::invalid_argument("Region definition name must not be empty.");
    }
    if (definition.signature.empty()) {
        throw std::invalid_argument(
            "Region definition '" + definition.name + "' has no signature.");
    }
    if (definition.regions.empty()) {
        throw std::invalid_argument(
            "Region definition '" + definition.name + "' contains no regions.");
    }
    if (!definition.locate) {
        throw std::invalid_argument(
            "Region definition '" + definition.name + "' has no locator.");
    }
    if (!position_at) {
        throw std::invalid_argument(
            "Region partition '" + definition.name + "' has no position extractor.");
    }

    RegionPartition partition;
    partition.name = definition.name;
    partition.definition_hash = definition_hash(definition);
    partition.regions = definition.regions;
    partition.sample_regions.reserve(sample_count);
    for (size_t i = 0; i < sample_count; i++) {
        const std::optional<RegionId> region = definition.locate(position_at(i));
        if (!region.has_value()) {
            throw std::runtime_error(
                "Region partition '" + definition.name +
                "' does not cover sample " + std::to_string(i) + ".");
        }
        if (*region >= definition.regions.size()) {
            throw std::runtime_error(
                "Region partition '" + definition.name + "' returned region " +
                std::to_string(*region) + " for sample " + std::to_string(i) +
                ", but region_count=" +
                std::to_string(definition.regions.size()) + ".");
        }
        partition.sample_regions.push_back(*region);
    }
    return partition;
}

SampleMask select_regions(
    const RegionPartition& partition,
    const RegionSelection& selection) {

    validate_partition(partition, partition.sample_count(), "Region selection");
    const std::vector<RegionId> resolved = resolve_regions(partition, selection);
    std::vector<uint8_t> selected_regions(partition.region_count(), 0);
    for (RegionId region : resolved) {
        selected_regions[region] = 1;
    }

    SampleMask mask;
    mask.name = selection.name;
    mask.selected.resize(partition.sample_count());
    for (size_t i = 0; i < partition.sample_count(); i++) {
        const RegionId region = partition.sample_regions[i];
        if (region >= partition.region_count()) {
            throw std::runtime_error(
                "Region partition '" + partition.name + "' contains invalid region " +
                std::to_string(region) + " at sample " + std::to_string(i) + ".");
        }
        mask.selected[i] = selected_regions[region];
    }
    validate_mask(mask, partition.sample_count(), selection.name);
    return mask;
}

std::vector<SampleMask> select_region_sets(
    const RegionPartition& partition,
    std::span<const RegionSelection> selections) {

    if (selections.empty()) {
        throw std::invalid_argument(
            "At least one named region selection is required.");
    }
    std::unordered_set<std::string> names;
    std::vector<SampleMask> masks;
    masks.reserve(selections.size());
    for (const RegionSelection& selection : selections) {
        if (!names.insert(selection.name).second) {
            throw std::invalid_argument(
                "Duplicate region selection name '" + selection.name + "'.");
        }
        masks.push_back(select_regions(partition, selection));
    }
    return masks;
}

std::vector<RegionId> resolve_regions(
    const RegionPartition& partition,
    const RegionSelection& selection) {

    validate_partition(partition, partition.sample_count(), "Region selection");
    if (selection.name.empty()) {
        throw std::invalid_argument("Region selection name must not be empty.");
    }
    if (selection.keys.empty()) {
        throw std::invalid_argument(
            "Region selection '" + selection.name + "' contains no region keys.");
    }

    std::unordered_map<std::string, RegionId> ids;
    for (size_t i = 0; i < partition.regions.size(); i++) {
        ids.emplace(partition.regions[i].key, static_cast<RegionId>(i));
    }

    std::vector<RegionId> resolved;
    std::unordered_set<RegionId> used;
    resolved.reserve(selection.keys.size());
    for (const std::string& key : selection.keys) {
        const auto item = ids.find(key);
        if (item == ids.end()) {
            throw std::out_of_range(
                "Region selection '" + selection.name + "' contains unknown key '" +
                key + "' for partition '" + partition.name + "'.");
        }
        if (!used.insert(item->second).second) {
            throw std::invalid_argument(
                "Region selection '" + selection.name +
                "' contains duplicate key '" + key + "'.");
        }
        resolved.push_back(item->second);
    }
    return resolved;
}

std::string definition_hash(const RegionDefinition& definition) {
    constexpr uint64_t offset = 14695981039346656037ull;
    constexpr uint64_t prime = 1099511628211ull;
    uint64_t hash = offset;
    const auto add = [&hash](std::string_view text) {
        for (unsigned char value : text) {
            hash ^= value;
            hash *= prime;
        }
        hash ^= 0xff;
        hash *= prime;
    };
    add(definition.name);
    add(definition.signature);
    for (const RegionInfo& region : definition.regions) {
        add(region.key);
        add(region.label);
    }
    std::ostringstream text;
    text << std::hex << std::setfill('0') << std::setw(16) << hash;
    return text.str();
}

void validate_partition(
    const RegionPartition& partition,
    size_t expected_size,
    std::string_view object_name) {

    if (partition.region_count() == 0) {
        throw std::invalid_argument(
            std::string(object_name) + " partition contains no regions.");
    }
    if (partition.definition_hash.empty()) {
        throw std::invalid_argument(
            std::string(object_name) + " partition has no definition hash.");
    }
    std::unordered_set<std::string> keys;
    for (const RegionInfo& region : partition.regions) {
        if (region.key.empty()) {
            throw std::invalid_argument(
                std::string(object_name) + " partition contains an empty region key.");
        }
        if (!keys.insert(region.key).second) {
            throw std::invalid_argument(
                std::string(object_name) + " partition contains duplicate key '" +
                region.key + "'.");
        }
    }
    if (partition.sample_count() != expected_size) {
        throw std::invalid_argument(
            std::string(object_name) + " partition sample_count=" +
            std::to_string(partition.sample_count()) + ", expected=" +
            std::to_string(expected_size) + ".");
    }
    for (size_t i = 0; i < partition.sample_count(); i++) {
        if (partition.sample_regions[i] >= partition.region_count()) {
            throw std::out_of_range(
                std::string(object_name) + " partition contains region " +
                std::to_string(partition.sample_regions[i]) + " at sample " +
                std::to_string(i) + ", but region_count=" +
                std::to_string(partition.region_count()) + ".");
        }
    }
}

void validate_mask(
    const SampleMask& mask,
    size_t expected_size,
    std::string_view object_name,
    bool require_selected) {

    if (mask.size() != expected_size) {
        throw std::invalid_argument(
            std::string(object_name) + " mask length=" + std::to_string(mask.size()) +
            ", expected=" + std::to_string(expected_size) + ".");
    }
    const auto invalid = std::find_if(
        mask.selected.begin(), mask.selected.end(),
        [](uint8_t value) { return value > 1; });
    if (invalid != mask.selected.end()) {
        throw std::invalid_argument(
            std::string(object_name) + " mask contains non-boolean value " +
            std::to_string(*invalid) + " at sample " +
            std::to_string(invalid - mask.selected.begin()) + ".");
    }
    if (require_selected &&
        std::none_of(mask.selected.begin(), mask.selected.end(),
            [](uint8_t value) { return value != 0; })) {
        throw std::invalid_argument(
            std::string(object_name) + " mask selects no samples.");
    }
}

} // namespace slow_light::regions
