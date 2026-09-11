#include "apps/RunConfig.h"

#if COPORTSL_APP != COPORTSL_FLUX

#include "AnalysisOutput.h"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>

#include "src/grrt/ConfigFields.h"
#include "src/grrt/ConfigOutput.h"

namespace slow_light::analysis::output {
namespace {

std::string csv_text(const std::string& value) {
    std::string escaped;
    escaped.reserve(value.size() + 2);
    escaped.push_back('"');
    for (char character : value) {
        if (character == '"') escaped.push_back('"');
        escaped.push_back(character);
    }
    escaped.push_back('"');
    return escaped;
}

void write_region_index(
    const std::filesystem::path& root,
    const regions::RegionPartition& partition) {

    std::vector<uint64_t> sample_counts(partition.region_count(), 0);
    for (regions::RegionId region : partition.sample_regions) {
        sample_counts[region]++;
    }

    std::ofstream index(root / "index.csv");
    if (!index) {
        throw std::runtime_error("Cannot write region index.");
    }
    index << "key,label,samples\n";
    for (size_t region = 0; region < partition.region_count(); region++) {
        index << partition.regions[region].key << ","
            << csv_text(partition.regions[region].label) << ","
            << sample_counts[region] << "\n";
    }
}

} // namespace

void write_config(
    const std::filesystem::path& directory,
    const fluid::FrameSequence& sequence,
    const grrt::Signatures& signatures) {

    std::ofstream out(directory / "config.txt");
    if (!out) {
        throw std::runtime_error("Cannot write analysis config.");
    }
    out << std::setprecision(17)
        << "Config::TASK=analysis\n";
    grrt::write_model_config(out, sequence, signatures);
    out
        << "analysis_signature=" << signatures.analysis << "\n";
    grrt::visit_analysis_fields(grrt::ConfigFieldWriter{out});
    out << "SlowLight::REGION=" << SlowLight::REGION.name << "\n"
        << "SlowLight::REGION_HASH="
        << regions::definition_hash(SlowLight::REGION) << "\n";
    grrt::visit_time_origin_fields(grrt::ConfigFieldWriter{out});
}

void write_contributions(
    const std::filesystem::path& directory,
    const regions::RegionPartition& partition,
    std::span<const ContributionFrame> frames) {

    const std::filesystem::path root = directory / "regions";
    std::filesystem::create_directories(root);
    write_region_index(root, partition);

    for (size_t region = 0; region < partition.region_count(); region++) {
        const std::filesystem::path region_directory =
            root / partition.regions[region].key;
        std::filesystem::create_directories(region_directory);
        std::ofstream out(region_directory / "contribution.csv");
        if (!out) {
            throw std::runtime_error(
                "Cannot write region contribution file.");
        }
        out << "frame,jI_abs,jP_abs,aI_abs,aP_abs,rhoV_abs,rhoC_abs\n";
        for (const ContributionFrame& frame : frames) {
            if (frame.regions.size() != partition.region_count()) {
                throw std::invalid_argument(
                    "Region contribution frame has the wrong region count.");
            }
            const auto& item = frame.regions[region];
            out << std::setprecision(17) << frame.frame
                << "," << item.jI_abs
                << "," << item.jP_abs
                << "," << item.aI_abs
                << "," << item.aP_abs
                << "," << item.rhoV_abs
                << "," << item.rhoC_abs << "\n";
        }
    }
}

void write_time_histogram(
    const std::vector<double>& offsets,
    double dt,
    const std::filesystem::path& file) {

    std::map<int64_t, uint64_t> bins;
    for (double offset : offsets) {
        bins[static_cast<int64_t>(std::floor(offset / dt))]++;
    }
    std::ofstream out(file);
    if (!out) {
        throw std::runtime_error("Cannot write time-offset histogram.");
    }
    out << "frame_offset,count\n";
    for (const auto& [offset, count] : bins) {
        out << offset << "," << count << "\n";
    }
}

void write_windows(
    const std::vector<CoverageWindow>& windows,
    const std::filesystem::path& file) {

    std::ofstream out(file);
    if (!out) {
        throw std::runtime_error("Cannot write slow-light windows.");
    }
    out << "window,left,right\n";
    for (const CoverageWindow& window : windows) {
        out << window.name << "," << std::setprecision(17)
            << window.left << "," << window.right << "\n";
    }
}

void write_time_span_map(
    const ray::RayGeometry& rays,
    const regions::SampleMask& slow_mask,
    const std::filesystem::path& file) {

    std::ofstream out(file);
    if (!out) {
        throw std::runtime_error("Cannot write slow-light time-span map.");
    }
    for (int row = 0; row < rays.npix; row++) {
        for (int col = 0; col < rays.npix; col++) {
            const int pixel = row * rays.npix + (rays.npix - 1 - col);
            const uint64_t begin = rays.ray_offset[static_cast<size_t>(pixel)];
            const uint64_t end =
                rays.ray_offset[static_cast<size_t>(pixel + 1)];
            double lo = std::numeric_limits<double>::infinity();
            double hi = -std::numeric_limits<double>::infinity();
            for (uint64_t sample_index = begin;
                sample_index < end; sample_index++) {
                const size_t index = static_cast<size_t>(sample_index);
                if (!slow_mask[index]) continue;
                const double offset =
                    static_cast<double>(rays.samples[index].dt);
                lo = std::min(lo, offset);
                hi = std::max(hi, offset);
            }
            const double span = std::isfinite(lo) ?
                hi - lo : std::numeric_limits<double>::quiet_NaN();
            out << std::setprecision(9) << span;
            if (col + 1 != rays.npix) out << ",";
        }
        out << "\n";
    }
}

void write_region_keys(
    const regions::RegionSelection& selection,
    const std::filesystem::path& file) {

    std::ofstream out(file);
    if (!out) {
        throw std::runtime_error("Cannot write suggested region keys.");
    }
    for (const std::string& key : selection.keys) {
        out << key << "\n";
    }
}

} // namespace slow_light::analysis::output

#endif
