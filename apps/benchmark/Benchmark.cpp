#include "apps/RunConfig.h"

#if COPORTSL_APP == COPORTSL_BENCHMARK

#include <array>
#include <algorithm>
#include <chrono>
#include <charconv>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

#include <omp.h>

#include "Timing.h"
#include "src/physics/Model.h"
#include "src/grrt/ConfigFields.h"
#include "src/grrt/ConfigOutput.h"
#include "src/grrt/Signatures.h"
#include "src/grrt/fast/FastTransfer.h"
#include "src/physics/fluid/FluidBackend.h"
#include "src/physics/fluid/GridLocations.h"
#include "src/support/RunDirectory.h"
#include "src/grrt/RayGeometry.h"
#include "src/physics/fluid/FrameCache.h"
#include "src/physics/fluid/FrameSequence.h"
#include "src/grrt/slow/SlowTransfer.h"
#include "src/grrt/slow/AnalysisStore.h"
#include "src/grrt/slow/TimeOrigin.h"

namespace {

std::string core_mode_name(BenchmarkConfig::CoreMode mode) {
    using BenchmarkConfig::CoreMode;
    switch (mode) {
    case CoreMode::AllLogical: return "all_logical";
    case CoreMode::PhysicalCores: return "physical_cores";
    case CoreMode::PerformanceCores: return "performance_cores";
    case CoreMode::EfficiencyCores: return "efficiency_cores";
    }
    return "unknown";
}

template <typename T, size_t N>
void write_list(std::ostream& out, const std::array<T, N>& values) {
    for (size_t i = 0; i < values.size(); i++) {
        if (i > 0) out << ",";
        out << values[i];
    }
}

template <typename T>
void write_list(std::ostream& out, const std::vector<T>& values) {
    for (size_t i = 0; i < values.size(); i++) {
        if (i > 0) out << ",";
        out << values[i];
    }
}

void write_region_keys(
    std::ostream& out,
    const slow_light::regions::RegionSelection& selection) {

    for (size_t i = 0; i < selection.keys.size(); i++) {
        if (i > 0) out << ",";
        out << selection.keys[i];
    }
}

void write_config_fields(
    std::ostream& out,
    const fluid::FrameSequence& sequence,
    const grrt::Signatures& signatures,
    const slow_light::analysis::AnalysisResult& analysis,
    const slow_light::analysis::StoredWindow& window,
    const std::vector<int>& core_counts) {

    out << std::setprecision(17) << std::boolalpha;
    out << "Config::TASK=benchmark\n";
    grrt::write_model_config(out, sequence, signatures);
    out << "analysis_signature=" << signatures.analysis << "\n";
    grrt::visit_analysis_fields(grrt::ConfigFieldWriter{out});
    out << "SlowLight::REGION=" << BenchmarkConfig::REGION.name << "\n"
        << "SlowLight::REGION_HASH="
        << slow_light::regions::definition_hash(BenchmarkConfig::REGION) << "\n";
    grrt::visit_time_origin_fields(grrt::ConfigFieldWriter{out});
    out << "SlowLight::REGION_KEYS=";
    write_region_keys(out, analysis.suggested_regions);
    out << "\n"
        << "SlowLight::WINDOW=" << window.name << "\n"
        << "SlowLight::LEFT=" << window.left << "\n"
        << "SlowLight::RIGHT=" << window.right << "\n"
        << "Benchmark::CPU_NAME=" << benchmark::cpu_name() << "\n"
        << "BenchmarkConfig::NT0=" << BenchmarkConfig::NT0 << "\n"
        << "BenchmarkConfig::NT1=" << BenchmarkConfig::NT1 << "\n"
        << "BenchmarkConfig::DNT=" << BenchmarkConfig::DNT << "\n"
        << "BenchmarkConfig::REPEATS=" << BenchmarkConfig::REPEATS << "\n"
        << "BenchmarkConfig::WARMUP_FRAMES="
        << BenchmarkConfig::WARMUP_FRAMES << "\n"
        << "BenchmarkConfig::RUN_FAST_LIGHT="
        << BenchmarkConfig::RUN_FAST_LIGHT << "\n"
        << "BenchmarkConfig::RUN_SLOW_LIGHT="
        << BenchmarkConfig::RUN_SLOW_LIGHT << "\n"
        << "BenchmarkConfig::NPIX_LIST=";
    write_list(out, BenchmarkConfig::NPIX_LIST);
    out << "\nBenchmarkConfig::CORE_MODE="
        << core_mode_name(BenchmarkConfig::CORE_MODES.front());
    out << "\nBenchmarkConfig::CORE_COUNTS=";
    write_list(out, core_counts);
    out << "\n";
}

std::string benchmark_config_text(
    const fluid::FrameSequence& sequence,
    const grrt::Signatures& signatures,
    const slow_light::analysis::AnalysisResult& analysis,
    const slow_light::analysis::StoredWindow& window,
    const std::vector<int>& core_counts) {

    std::ostringstream out;
    write_config_fields(
        out, sequence, signatures, analysis, window, core_counts);
    return out.str();
}

void write_config(
    const run_io::RunDirectory& run,
    const std::string& text) {

    const std::filesystem::path path = run.path / "config.txt";
    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error("Cannot write benchmark config: " + path.string());
    }
    out << text;
    if (!out) {
        throw std::runtime_error("Cannot write benchmark config: " + path.string());
    }
}

bool benchmark_summary_complete(
    const std::filesystem::path& path,
    const std::vector<int>& core_counts) {

    std::ifstream input(path);
    std::string line;
    if (!std::getline(input, line)) return false;
    constexpr std::string_view header =
        "light,npix,cores,grid_points,samples,grid_bytes,frame_bytes,"
        "frame_update_mean_s,frame_update_std_s,"
        "transfer_mean_s,transfer_std_s";
    if (line != header) return false;

    std::vector<std::tuple<std::string, int, int>> found;
    while (std::getline(input, line)) {
        if (line.empty() || std::count(line.begin(), line.end(), ',') != 10) {
            return false;
        }
        std::istringstream row(line);
        std::string light;
        std::string npix_text;
        std::string cores_text;
        if (!std::getline(row, light, ',') ||
            !std::getline(row, npix_text, ',') ||
            !std::getline(row, cores_text, ',')) {
            return false;
        }
        int npix = 0;
        const auto [npix_end, npix_error] = std::from_chars(
            npix_text.data(), npix_text.data() + npix_text.size(), npix);
        int cores = 0;
        const auto [cores_end, cores_error] = std::from_chars(
            cores_text.data(), cores_text.data() + cores_text.size(), cores);
        if (npix_error != std::errc{} ||
            npix_end != npix_text.data() + npix_text.size() ||
            cores_error != std::errc{} ||
            cores_end != cores_text.data() + cores_text.size()) {
            return false;
        }
        std::string value;
        while (std::getline(row, value, ',')) {
            char* end = nullptr;
            const double parsed = std::strtod(value.c_str(), &end);
            if (end != value.c_str() + value.size() || !std::isfinite(parsed)) {
                return false;
            }
        }
        const auto key = std::tuple{light, npix, cores};
        if (std::find(found.begin(), found.end(), key) != found.end()) {
            return false;
        }
        found.push_back(key);
    }
    for (int npix : BenchmarkConfig::NPIX_LIST) {
        for (int cores : core_counts) {
            if constexpr (BenchmarkConfig::RUN_FAST_LIGHT) {
                if (std::find(found.begin(), found.end(),
                    std::tuple{std::string("fast"), npix, cores}) == found.end()) {
                    return false;
                }
            }
            if constexpr (BenchmarkConfig::RUN_SLOW_LIGHT) {
                if (std::find(found.begin(), found.end(),
                    std::tuple{std::string("slow"), npix, cores}) == found.end()) {
                    return false;
                }
            }
        }
    }
    const size_t lights =
        static_cast<size_t>(BenchmarkConfig::RUN_FAST_LIGHT) +
        static_cast<size_t>(BenchmarkConfig::RUN_SLOW_LIGHT);
    return found.size() ==
        BenchmarkConfig::NPIX_LIST.size() * core_counts.size() * lights;
}

bool benchmark_result_matches(
    const std::filesystem::path& config,
    std::string_view expected_config,
    const std::vector<int>& core_counts) {

    std::ifstream input(config);
    if (!input) return false;
    const std::string actual{
        std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
    return actual == expected_config &&
        benchmark_summary_complete(
            config.parent_path() / "summary.csv", core_counts);
}

std::array<double, 4> checksum(const std::vector<std::array<double, 4>>& image) {
    std::array<double, 4> sum = {};
    for (const auto& pixel : image) {
        for (size_t s = 0; s < sum.size(); s++) sum[s] += pixel[s];
    }
    return sum;
}

void print_record(
    const std::string& light,
    int frame,
    const benchmark::TimingRecord& record,
    const std::array<double, 4>& sum) {

    std::cout << light << " frame=" << frame
        << " update=" << record.frame_update_s
        << " transfer=" << record.transfer_s
        << " total=" << record.frame_update_s + record.transfer_s
        << " stokes_i=" << sum[0] << "\n";
}

struct ScanCase {
    std::string mode;
    int cores = 0;
    benchmark::CpuSelection cpus;
    std::vector<benchmark::TimingRecord> fast_records;
    std::vector<benchmark::TimingRecord> slow_records;
};

struct PreparedGeometry {
    ray::RayGeometry rays;
    fluid::GridLocations sampling;
    slow_light::regions::SampleMask time_origin_mask;
    slow_light::regions::SampleMask slow_mask;
    double setup_s = 0.0;
};

benchmark::CpuSelection apply_cpu_case(const std::string& mode, int threads) {
    omp_set_dynamic(0);
    omp_set_num_threads(threads);
    benchmark::CpuSelection cpus = benchmark::select_cpu_sets(mode, threads);
    #pragma omp parallel
    {
        #pragma omp single
        cpus.actual_threads = omp_get_num_threads();
    }
    if (cpus.actual_threads != threads) {
        throw std::runtime_error(
            "OpenMP did not start the requested number of threads.");
    }
    return cpus;
}

std::vector<int> supported_core_counts() {
    std::vector<int> result;
    const std::string mode = core_mode_name(BenchmarkConfig::CORE_MODES.front());
    for (int cores : BenchmarkConfig::CORE_COUNTS) {
        try {
            static_cast<void>(apply_cpu_case(mode, cores));
            result.push_back(cores);
        }
        catch (const std::exception& error) {
            std::cerr << "Skip benchmark core count: mode=" << mode
                << " cores=" << cores
                << " reason=" << error.what() << "\n";
        }
    }
    if (result.empty()) {
        throw std::runtime_error(
            "No benchmark physical-core count is supported on this machine.");
    }
    return result;
}

std::vector<ScanCase> build_scan_cases(
    int npix,
    const std::vector<int>& core_counts) {

    std::vector<ScanCase> cases;
    const std::string mode = core_mode_name(BenchmarkConfig::CORE_MODES.front());
    for (int cores : core_counts) {
        ScanCase item;
        item.mode = mode;
        item.cores = cores;
        item.cpus = apply_cpu_case(mode, cores);
        std::cout << "Benchmark CPU case: " << benchmark::cpu_name()
            << " mode=" << item.cpus.mode
            << " cores=" << item.cpus.actual_threads
            << " npix=" << npix << "\n";
        cases.push_back(std::move(item));
    }
    return cases;
}

PreparedGeometry prepare_geometry(
    int npix,
    const slow_light::regions::RegionSelection& selection) {

    const auto begin = benchmark::Clock::now();
    PreparedGeometry prepared;
    prepared.rays = ray::build_ray_geometry(
        npix, Config::FOV, Config::OBS, fluid::Backend::probe_grid);
    prepared.sampling = fluid::locate_ray_samples(prepared.rays);
    if constexpr (BenchmarkConfig::RUN_SLOW_LIGHT) {
        const auto partition = slow_light::regions::build_partition(
            prepared.rays.samples, BenchmarkConfig::REGION);
        prepared.time_origin_mask = slow_light::time_origin::build_mask(
            prepared.rays.samples);
        prepared.slow_mask = slow_light::regions::select_regions(
            partition, selection);
    }
    prepared.setup_s = benchmark::seconds(begin, benchmark::Clock::now());
    std::cout << "Benchmark prepared geometry once: npix=" << npix
        << " rays=" << static_cast<uint64_t>(npix) * static_cast<uint64_t>(npix)
        << " samples=" << prepared.rays.samples.size()
        << " setup_s=" << prepared.setup_s << "\n";
    return prepared;
}

void write_scan_summaries(
    const run_io::RunDirectory& run,
    int npix,
    const fluid::GridStats& grid_stats,
    size_t frame_bytes,
    const std::vector<ScanCase>& cases) {

    for (const ScanCase& item : cases) {
        if constexpr (BenchmarkConfig::RUN_FAST_LIGHT) {
            benchmark::write_summary(
                run.path / "summary.csv", "fast", npix, item.cores,
                grid_stats.active_cells, grid_stats.resident_bytes,
                frame_bytes, item.fast_records);
        }
        if constexpr (BenchmarkConfig::RUN_SLOW_LIGHT) {
            benchmark::write_summary(
                run.path / "summary.csv", "slow", npix, item.cores,
                grid_stats.active_cells, grid_stats.resident_bytes,
                frame_bytes, item.slow_records);
        }
    }
}

void run_scan_for_resolution(
    const run_io::RunDirectory& run,
    const fluid::FrameSequence& sequence,
    const slow_light::regions::RegionSelection& selection,
    const slow_light::analysis::StoredWindow& window,
    const fluid::FrameInfo& first_frame,
    const fluid::GridStats& grid_stats,
    size_t frame_bytes,
    const std::vector<int>& core_counts,
    int npix) {

    const benchmark::CpuSelection preparation_cpus =
        apply_cpu_case("all_logical", 1);
    std::cout << "Benchmark shared preparation CPU: mode="
        << preparation_cpus.mode
        << " threads=" << preparation_cpus.actual_threads << "\n";
    PreparedGeometry prepared = prepare_geometry(npix, selection);
    std::vector<ScanCase> cases = build_scan_cases(npix, core_counts);
    const uint64_t rays_count =
        static_cast<uint64_t>(npix) * static_cast<uint64_t>(npix);

    if constexpr (BenchmarkConfig::RUN_SLOW_LIGHT) {
        const slow_light::TimeOffsetRange offsets = slow_light::time_offset_range(
            prepared.rays, prepared.time_origin_mask, prepared.slow_mask);
        std::cout << "Slow-light timing reference: time_origin="
            << slow_light::time_origin::NAME
            << " slow_region=" << selection.name
            << " origin_offset=" << offsets.origin_offset
            << " time_offset=[" << offsets.min_offset << "," << offsets.max_offset << "]"
            << " configured_window=[" << window.left
            << "," << window.right << "]\n";
    }

    for (int repeat = 1; repeat <= BenchmarkConfig::REPEATS; repeat++) {
        static_cast<void>(apply_cpu_case("all_logical", 1));
        std::optional<fluid::FrameCache> frames;
        if constexpr (BenchmarkConfig::RUN_SLOW_LIGHT) {
            frames.emplace(fluid::FrameCache::load(
                sequence, first_frame, window.left, window.right));
        }

        int index = 0;
        for (int nt = BenchmarkConfig::NT0; nt <= BenchmarkConfig::NT1;
            nt += BenchmarkConfig::DNT, index++) {
            static_cast<void>(apply_cpu_case("all_logical", 1));
            double fast_update_s = 0.0;
            double slow_update_s = 0.0;
            if constexpr (BenchmarkConfig::RUN_FAST_LIGHT) {
                const auto begin = benchmark::Clock::now();
                fluid::Backend::load_active_frame(
                    fluid::Backend::frame_path(Config::DATA, nt));
                fast_update_s = benchmark::seconds(begin, benchmark::Clock::now());
            }
            if (frames.has_value()) {
                const double base_time = fluid::Backend::frame_time(
                    fluid::Backend::frame_path(Config::DATA, nt));
                const auto begin = benchmark::Clock::now();
                frames->advance(base_time);
                slow_update_s = benchmark::seconds(begin, benchmark::Clock::now());
            }

            for (ScanCase& item : cases) {
                item.cpus = apply_cpu_case(item.mode, item.cores);
                if constexpr (BenchmarkConfig::RUN_FAST_LIGHT) {
                    benchmark::TimingRecord record;
                    record.rays = rays_count;
                    record.samples = prepared.rays.samples.size();
                    record.warmup = index < BenchmarkConfig::WARMUP_FRAMES;
                    std::vector<std::array<double, 4>> image;
                    const auto begin = benchmark::Clock::now();
                    fast_light::compute_image(
                        prepared.rays, prepared.sampling,
                        BenchmarkConfig::NU, image);
                    record.transfer_s = benchmark::seconds(
                        begin, benchmark::Clock::now());
                    record.frame_update_s = fast_update_s;
                    item.fast_records.push_back(record);
                    print_record("fast", nt, record, checksum(image));
                }
                if (frames.has_value()) {
                    benchmark::TimingRecord record;
                    record.rays = rays_count;
                    record.samples = prepared.rays.samples.size();
                    record.warmup = index < BenchmarkConfig::WARMUP_FRAMES;
                    std::vector<std::array<double, 4>> image;
                    const auto begin = benchmark::Clock::now();
                    const slow_light::TransferStats stats =
                        slow_light::compute_image(
                            prepared.rays, prepared.sampling, *frames,
                            BenchmarkConfig::NU, prepared.time_origin_mask,
                            prepared.slow_mask, window.left, window.right, image);
                    record.transfer_s = benchmark::seconds(
                        begin, benchmark::Clock::now());
                    record.frame_update_s = slow_update_s;
                    item.slow_records.push_back(record);
                    std::cout << "Slow-light timing samples: future="
                        << stats.future_samples
                        << " history_clamped=" << stats.clamped_samples
                        << " variable=" << stats.inner_samples
                        << " fixed=" << stats.outer_samples << "\n";
                    print_record("slow", nt, record, checksum(image));
                }
            }
        }
    }

    write_scan_summaries(
        run, npix, grid_stats, frame_bytes, cases);
}

int run_benchmark() {
    run_io::RunDirectory run;
    try {
        const fluid::FrameSequence sequence =
            fluid::discover_frame_sequence(Config::DATA);
        const auto first_item = std::find_if(
            sequence.frames.begin(), sequence.frames.end(),
            [](const fluid::FrameInfo& frame) {
                return frame.index == BenchmarkConfig::NT0;
            });
        if (first_item == sequence.frames.end()) {
            throw std::runtime_error(
                "Benchmark first frame is outside the discovered input timeline.");
        }
        const auto grid_begin = benchmark::Clock::now();
        fluid::Backend::initialize_grid(first_item->path, Config::GRID);
        const double grid_setup_s = benchmark::seconds(
            grid_begin, benchmark::Clock::now());
        const fluid::GridStats grid_stats = fluid::Backend::grid_stats();
        const size_t frame_bytes = fluid::Backend::load_frame(
            first_item->path).bytes();
        std::cout << "Benchmark initialized grid once: setup_s="
            << grid_setup_s << " resident_bytes="
            << grid_stats.resident_bytes
            << " frame_bytes=" << frame_bytes << "\n";
        const grrt::Signatures signatures = grrt::make_signatures(sequence);
        const auto analysis =
            slow_light::analysis::find_compatible_stored_analysis(
                Analysis::OUTPUT,
                sequence,
                signatures,
                BenchmarkConfig::REGION);
        if (!analysis.has_value()) {
            throw std::runtime_error(
                "Benchmark requires a complete Thermal 230 GHz Shell analysis "
                "with analysis_signature=" + signatures.analysis +
                " under " + Analysis::OUTPUT.string() + ".");
        }
        const auto window = slow_light::analysis::read_window(
            analysis->run, BenchmarkConfig::WINDOW);
        const std::vector<int> core_counts = supported_core_counts();
        const std::string expected_config = benchmark_config_text(
            sequence, signatures, *analysis, window, core_counts);
        if (const auto existing = run_io::find_latest_complete_run_if(
            BenchmarkConfig::OUTPUT,
            [&expected_config, &core_counts](const std::filesystem::path& config) {
                return benchmark_result_matches(
                    config, expected_config, core_counts);
            },
            {"summary.csv"})) {
            std::cout << "Reusing benchmark result: " << existing->path << "\n";
            return 0;
        }
        run = run_io::allocate_run_directory(BenchmarkConfig::OUTPUT);
        run_io::write_run_paths(
            run,
            Config::DATA,
            Config::GRID,
            Config::OUTPUT,
            std::filesystem::relative(analysis->run.path, run.path));
        write_config(run, expected_config);
        std::cout << "Benchmark analysis: path=" << analysis->run.path
            << " signature=" << analysis->analysis_signature
            << " region=" << analysis->suggested_regions.name
            << " window=" << window.name
            << " range=[" << window.left << "," << window.right << "]\n";
        for (int npix : BenchmarkConfig::NPIX_LIST) {
            run_scan_for_resolution(
                run,
                sequence,
                analysis->suggested_regions,
                window,
                *first_item,
                grid_stats,
                frame_bytes,
                core_counts,
                npix);
        }
        run_io::write_run_status(run, "complete");
    }
    catch (const std::exception& error) {
        if (!run.path.empty()) {
            try {
                run_io::write_run_status(run, "failed");
            }
            catch (...) {
            }
        }
        std::cerr << "Benchmark failed: " << error.what() << "\n";
        return 1;
    }
    return 0;
}

void print_usage(const char* executable) {
    std::cerr << "Usage: " << executable << " [--help | --check-cpu MODE]\n"
        << "  MODE is all_logical or physical_cores for portable CPU checks.\n"
        << "  Scan CORE_MODES, NPIX_LIST and CORE_COUNTS in apps/benchmark/BenchmarkConfig.h.\n";
}

int check_cpu_selection(const std::string& mode) {
    try {
        const benchmark::CpuSelection cpus = benchmark::select_cpu_sets(mode, 1);
        std::cout << "CPU selection: cpu=" << benchmark::cpu_name()
            << " mode=" << mode
            << " available=" << cpus.available.size()
            << " selected_count=" << cpus.selected.size()
            << " selected_ids=" << cpus.selected.front().id << "\n";
        return 0;
    }
    catch (const std::exception& error) {
        std::cerr << "CPU selection failed: " << error.what() << "\n";
        return 1;
    }
}

} // namespace

namespace benchmark_app {

int run(int argc, char** argv) {
    if (argc == 3 && std::string(argv[1]) == "--check-cpu") {
        return check_cpu_selection(argv[2]);
    }
    if (argc > 1 && (
        std::string(argv[1]) == "help" ||
        std::string(argv[1]) == "--help" ||
        std::string(argv[1]) == "-h")) {
        print_usage(argv[0]);
        return 0;
    }
    if (argc != 1) {
        print_usage(argv[0]);
        return 2;
    }
    return run_benchmark();
}

} // namespace benchmark_app

#endif
