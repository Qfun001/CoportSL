#include "Runtime.h"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <functional>
#include <initializer_list>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <unordered_set>
#include <vector>

#include "apps/RunConfig.h"
#include "NumberExpression.h"
#include "src/physics/Constants.h"
#include "third_party/nlohmann/json.hpp"

namespace runtime_config {
namespace {

using Json = nlohmann::json;
std::filesystem::path cancel_file;

double number_value(const Json& value, std::string_view name) {
    double result = 0.0;
    try {
        if (value.is_number()) result = value.get<double>();
        else if (value.is_string()) {
            result = evaluate_number_expression(value.get_ref<const std::string&>());
        }
        else {
            throw std::invalid_argument("expected a number or expression string");
        }
    }
    catch (const std::exception& error) {
        throw std::invalid_argument(
            "Invalid numeric configuration field " + std::string(name) +
            ": " + error.what());
    }
    if (!std::isfinite(result)) {
        throw std::invalid_argument(
            "Invalid numeric configuration field " + std::string(name) +
            ": result must be finite.");
    }
    return result;
}

int integer_value(const Json& value, std::string_view name) {
    const double numeric = number_value(value, name);
    if (std::trunc(numeric) != numeric ||
        numeric < static_cast<double>(std::numeric_limits<int>::min()) ||
        numeric > static_cast<double>(std::numeric_limits<int>::max())) {
        throw std::invalid_argument(
            "Invalid integer configuration field " + std::string(name) + ".");
    }
    return static_cast<int>(numeric);
}

template <typename T>
void assign(const Json& object, const char* key, T& target) {
    if (const auto it = object.find(key); it != object.end()) {
        if constexpr (std::is_same_v<T, double>) {
            target = number_value(*it, key);
        }
        else if constexpr (std::is_same_v<T, int>) {
            target = integer_value(*it, key);
        }
        else if constexpr (std::is_same_v<T, std::vector<double>>) {
            if (!it->is_array()) {
                throw std::invalid_argument(
                    std::string(key) + " must be an array.");
            }
            target.clear();
            target.reserve(it->size());
            for (size_t index = 0; index < it->size(); index++) {
                target.push_back(number_value(
                    (*it)[index], std::string(key) + "[" +
                    std::to_string(index) + "]"));
            }
        }
        else if constexpr (std::is_same_v<T, std::vector<int>>) {
            if (!it->is_array()) {
                throw std::invalid_argument(
                    std::string(key) + " must be an array.");
            }
            target.clear();
            target.reserve(it->size());
            for (size_t index = 0; index < it->size(); index++) {
                target.push_back(integer_value(
                    (*it)[index], std::string(key) + "[" +
                    std::to_string(index) + "]"));
            }
        }
        else {
            target = it->get<T>();
        }
    }
}

void assign_path(
    const Json& object,
    const char* key,
    std::filesystem::path& target) {

    if (const auto it = object.find(key); it != object.end()) {
        const std::string text = it->get<std::string>();
        const std::u8string utf8(
            reinterpret_cast<const char8_t*>(text.data()), text.size());
        target = std::filesystem::path(utf8);
    }
}

const Json& group(const Json& root, const char* name) {
    static const Json empty = Json::object();
    const auto it = root.find(name);
    if (it == root.end()) return empty;
    if (!it->is_object()) {
        throw std::invalid_argument(
            std::string("Configuration group must be an object: ") + name);
    }
    return *it;
}

void reject_unknown_keys(
    const Json& object,
    const std::string& path,
    std::initializer_list<std::string_view> allowed) {

    if (!object.is_object()) {
        throw std::invalid_argument(
            path.empty() ? "Configuration root must be an object." :
            "Configuration group must be an object: " + path);
    }
    for (const auto& [key, value] : object.items()) {
        (void)value;
        const bool known = std::any_of(
            allowed.begin(), allowed.end(),
            [&key](std::string_view candidate) { return candidate == key; });
        if (!known) {
            throw std::invalid_argument(
                "Unknown configuration field: " +
                (path.empty() ? key : path + "." + key));
        }
    }
}

std::string electron_name(int value) {
    if (value == Config::THERMAL) return "thermal";
    if (value == Config::POWER_LAW) return "powerlaw";
    if (value == Config::BEAM) return "beam";
    if (value == Config::LOSS_CONE) return "losscone";
    throw std::invalid_argument("Unsupported model.electron value.");
}

int parse_electron(const std::string& value) {
    if (value == "thermal") return Config::THERMAL;
    if (value == "powerlaw") return Config::POWER_LAW;
    if (value == "beam") return Config::BEAM;
    if (value == "losscone") return Config::LOSS_CONE;
    throw std::invalid_argument(
        "model.electron must be thermal, powerlaw, beam or losscone.");
}

std::optional<double> grid_hslope(const std::filesystem::path& path) {
    if (path.empty() || !std::filesystem::is_regular_file(path)) {
        return std::nullopt;
    }
    std::ifstream input(path);
    std::string key;
    std::string equals;
    double value = 0.0;
    while (input >> key >> equals >> value) {
        if (key == "hslope" || key == "hslop") {
            if (!std::isfinite(value)) {
                throw std::invalid_argument(
                    "grid_mks.in hslope must be finite.");
            }
            return value;
        }
    }
    throw std::invalid_argument(
        "grid_mks.in does not contain a readable hslope value.");
}

#if COPORTSL_APP != COPORTSL_FLUX
slow_light::regions::Partition parse_partition(const std::string& value) {
    if (value == "shell") return slow_light::regions::Partition::Shell;
    if (value == "jet_shell") return slow_light::regions::Partition::JetShell;
    throw std::invalid_argument(
        "partition must be shell or jet_shell.");
}

std::string partition_name(slow_light::regions::Partition value) {
    if (value == slow_light::regions::Partition::Shell) return "shell";
    if (value == slow_light::regions::Partition::JetShell) return "jet_shell";
    throw std::invalid_argument("Unsupported region partition.");
}
#endif

#if COPORTSL_APP == COPORTSL_GRRT
std::vector<slow_light::regions::RegionSelection> default_region_sets(
    slow_light::regions::Partition partition) {

    using slow_light::regions::Partition;
    if (partition == Partition::Shell) {
        return {
            {"r20", {"region_000"}},
            {"r30", {"region_000", "region_001"}},
            {"r50", {"region_000", "region_001", "region_002"}},
            {"r80", {
                "region_000", "region_001", "region_002", "region_003"}},
            {"r100", {
                "region_000", "region_001", "region_002", "region_003",
                "region_004"}},
            {"r200", {
                "region_000", "region_001", "region_002", "region_003",
                "region_004", "region_005"}}
        };
    }
    return {
        {"Omega1", {
            "north_000", "south_000",
            "non_jet_000", "non_jet_001", "non_jet_002"}},
        {"Omega2", {
            "north_000", "south_000", "south_001",
            "non_jet_000", "non_jet_001", "non_jet_002"}},
        {"Omega3", {
            "north_000",
            "south_000", "south_001", "south_002", "south_003",
            "non_jet_000", "non_jet_001", "non_jet_002"}},
        {"Omega4", {
            "north_000",
            "south_000", "south_001", "south_002", "south_003",
            "south_004", "south_005",
            "non_jet_000", "non_jet_001", "non_jet_002"}},
        {"Omega5", {
            "north_000", "north_001",
            "south_000", "south_001", "south_002", "south_003",
            "south_004", "south_005",
            "non_jet_000", "non_jet_001", "non_jet_002",
            "non_jet_003", "non_jet_004"}},
        {"Omega6", {
            "north_000", "north_001", "north_002", "north_003",
            "south_000", "south_001", "south_002", "south_003",
            "south_004", "south_005",
            "non_jet_000", "non_jet_001", "non_jet_002",
            "non_jet_003", "non_jet_004"}},
        {"Omega7", {
            "north_000", "north_001", "north_002", "north_003",
            "north_004", "north_005",
            "south_000", "south_001", "south_002", "south_003",
            "south_004", "south_005",
            "non_jet_000", "non_jet_001", "non_jet_002",
            "non_jet_003", "non_jet_004", "non_jet_005"}}
    };
}

std::string default_manual_set(
    slow_light::regions::Partition partition) {

    return partition == slow_light::regions::Partition::JetShell
        ? "Omega1" : "r50";
}

std::vector<slow_light::regions::RegionSelection> parse_region_sets(
    const Json& value) {

    if (!value.is_array() || value.empty()) {
        throw std::invalid_argument(
            "slow.region_sets must be a non-empty array.");
    }
    std::vector<slow_light::regions::RegionSelection> result;
    result.reserve(value.size());
    for (const Json& item : value) {
        if (!item.is_object()) {
            throw std::invalid_argument(
                "Each slow.region_sets item must be an object.");
        }
        reject_unknown_keys(item, "slow.region_sets[]", {"name", "keys"});
        result.push_back({
            item.at("name").get<std::string>(),
            item.at("keys").get<std::vector<std::string>>()
        });
    }
    return result;
}

template <typename Definition>
void validate_region_sets(
    const Definition& definition,
    const std::vector<slow_light::regions::RegionSelection>& selections) {

    if (selections.empty()) {
        throw std::invalid_argument(
            "At least one slow.region_sets item is required.");
    }
    std::unordered_set<std::string> valid_keys;
    for (const auto& region : definition.regions) {
        valid_keys.insert(region.key);
    }
    std::unordered_set<std::string> names;
    for (const auto& selection : selections) {
        if (selection.name.empty() || !names.insert(selection.name).second) {
            throw std::invalid_argument(
                "slow.region_sets names must be non-empty and unique.");
        }
        constexpr std::string_view allowed =
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-";
        if (selection.name.find_first_not_of(allowed) != std::string::npos) {
            throw std::invalid_argument(
                "slow.region_sets name '" + selection.name +
                "' must contain only letters, digits, underscores, or hyphens.");
        }
        if (selection.keys.empty()) {
            throw std::invalid_argument(
                "slow.region_sets item '" + selection.name +
                "' must contain at least one key.");
        }
        std::unordered_set<std::string> keys;
        for (const std::string& key : selection.keys) {
            if (!valid_keys.contains(key)) {
                throw std::invalid_argument(
                    "slow.region_sets item '" + selection.name +
                    "' contains unknown key '" + key + "'.");
            }
            if (!keys.insert(key).second) {
                throw std::invalid_argument(
                    "slow.region_sets item '" + selection.name +
                    "' contains duplicate key '" + key + "'.");
            }
        }
    }
}
#endif

#if COPORTSL_APP == COPORTSL_BENCHMARK
BenchmarkConfig::CoreMode parse_core_mode(const std::string& value) {
    using BenchmarkConfig::CoreMode;
    if (value == "all_logical") return CoreMode::AllLogical;
    if (value == "physical_cores") return CoreMode::PhysicalCores;
    if (value == "performance_cores") return CoreMode::PerformanceCores;
    if (value == "efficiency_cores") return CoreMode::EfficiencyCores;
    throw std::invalid_argument(
        "benchmark.core_modes contains an unsupported value.");
}

std::string core_mode_name(BenchmarkConfig::CoreMode value) {
    using BenchmarkConfig::CoreMode;
    if (value == CoreMode::AllLogical) return "all_logical";
    if (value == CoreMode::PhysicalCores) return "physical_cores";
    if (value == CoreMode::PerformanceCores) return "performance_cores";
    if (value == CoreMode::EfficiencyCores) return "efficiency_cores";
    throw std::invalid_argument("Unsupported benchmark core mode.");
}
#endif

Json common_json() {
    return {
        {"schema_version", 1},
        {"kind", std::string(Application::NAME)},
        {"paths", {
            {"data", Config::DATA.generic_string()},
            {"grid", Config::GRID.generic_string()}
        }},
        {"camera", {
            {"npix", Config::NPIX},
            {"fov_rad", Config::FOV},
#if COPORTSL_APP == COPORTSL_FLUX
            {"frequencies_hz", Config::NU},
#else
            {"nu_hz", Config::NU},
#endif
            {"observer_t", Config::OBS_T},
            {"observer_r_rg", Config::OBS_R},
            {"observer_theta_rad", Config::OBS_TH},
            {"observer_phi_rad", Config::OBS_PH}
        }},
        {"model", {
            {"metric", "mksbhac"},
            {"fluid_backend", "bhac"},
            {"electron", electron_name(Config::ELECTRON)},
            {"mbh_msun", Config::MBH},
            {"spin", Config::SPIN},
            {"hs", Config::HS},
            {"mdot_msun_per_year", Config::MDOT},
            {"mdot_sim", Config::MDOT_SIM},
            {"r_low", Config::R_LOW},
            {"r_high", Config::R_HIGH},
            {"beta0", Config::BETA0},
            {"sigma_max", Config::SIGMA_MAX},
            {"thetae_emit", Config::THETAE_EMIT},
            {"ne_emit_cm3", Config::NE_EMIT},
            {"pol_limit", Config::POL_LIMIT},
            {"p_min", Config::P_MIN},
            {"p_max", Config::P_MAX},
            {"gamma_ratio", Config::GAMMA_RATIO},
            {"beam_angle_rad", Config::BEAM_ANGLE},
            {"beam_width", Config::BEAM_WIDTH},
            {"r_source_rg", Config::R_SOURCE}
        }},
        {"ray", {
            {"atol", Config::RAY_ATOL},
            {"rtol", Config::RAY_RTOL},
            {"hmin", Config::RAY_HMIN},
            {"lmax", Config::RAY_LMAX},
            {"h0", Config::RAY_H0},
            {"cell_fraction", Config::RAY_CELL},
            {"horizon_factor", Config::RAY_HORIZON}
        }}
    };
}

#if COPORTSL_APP == COPORTSL_BENCHMARK
bool fixed_value_matches(
    const Json& supplied,
    const Json& expected,
    const std::string& path) {

    if (expected.is_number_float()) {
        return number_value(supplied, path) == expected.get<double>();
    }
    if (expected.is_number_integer() || expected.is_number_unsigned()) {
        return integer_value(supplied, path) == expected.get<int>();
    }
    if (expected.is_array()) {
        if (!supplied.is_array() || supplied.size() != expected.size()) {
            return false;
        }
        for (size_t index = 0; index < expected.size(); index++) {
            if (!fixed_value_matches(
                supplied[index], expected[index],
                path + "[" + std::to_string(index) + "]")) {
                return false;
            }
        }
        return true;
    }
    return supplied == expected;
}

void require_fixed_field(
    const Json& supplied,
    const Json& expected,
    const std::string& section,
    const std::string& key) {

    if (!fixed_value_matches(
        supplied.at(key), expected.at(key), section + "." + key)) {
        throw std::invalid_argument(
            "Benchmark fixes field: " + section + "." + key);
    }
}

void validate_benchmark_fixed_fields(const Json& root) {
    const Json reference = common_json();
    const std::unordered_set<std::string> adaptable_model = {
        "electron", "spin", "mdot_sim", "r_low", "r_high", "beta0",
        "p_min", "p_max", "gamma_ratio", "beam_angle_rad", "beam_width"
    };
    const Json& camera = group(root, "camera");
    for (const auto& [key, _value] : camera.items()) {
        require_fixed_field(camera, reference.at("camera"), "camera", key);
    }
    const Json& ray = group(root, "ray");
    for (const auto& [key, _value] : ray.items()) {
        require_fixed_field(ray, reference.at("ray"), "ray", key);
    }
    const Json& model = group(root, "model");
    for (const auto& [key, _value] : model.items()) {
        if (!adaptable_model.contains(key)) {
            require_fixed_field(model, reference.at("model"), "model", key);
        }
    }
    const Json& analysis = group(root, "analysis");
    const Json expected_analysis = {
        {"sample_dt_rg_over_c", Analysis::SAMPLE_DT},
        {"region_tolerances", {
            {"jI", Analysis::REGION_TOLERANCES.jI},
            {"jP", Analysis::REGION_TOLERANCES.jP},
            {"aI", Analysis::REGION_TOLERANCES.aI},
            {"aP", Analysis::REGION_TOLERANCES.aP},
            {"rhoV", Analysis::REGION_TOLERANCES.rhoV},
            {"rhoC", Analysis::REGION_TOLERANCES.rhoC}
        }}
    };
    for (const auto& [key, _value] : analysis.items()) {
        require_fixed_field(analysis, expected_analysis, "analysis", key);
    }
    const Json& benchmark = group(root, "benchmark");
    for (const auto& [key, expected] : {
        std::pair{"partition", partition_name(BenchmarkConfig::PARTITION)},
        std::pair{"window", BenchmarkConfig::WINDOW}}) {
        const auto supplied = benchmark.find(key);
        if (supplied == benchmark.end() || *supplied != expected) {
            throw std::invalid_argument(
                "Benchmark fixes field: benchmark." +
                std::string(key));
        }
    }
}
#endif

void load_common(const Json& root) {
    reject_unknown_keys(root, "", {
        "schema_version", "job_id", "kind", "paths", "camera", "model", "ray",
#if COPORTSL_APP == COPORTSL_GRRT
        "grrt", "analysis", "slow", "region_error"
#elif COPORTSL_APP == COPORTSL_FLUX
        "flux"
#else
        "analysis", "benchmark"
#endif
    });
    const int version = root.value("schema_version", 1);
    if (version != 1) {
        throw std::invalid_argument("schema_version must be 1.");
    }
#if COPORTSL_APP == COPORTSL_BENCHMARK
    validate_benchmark_fixed_fields(root);
#endif
    const std::string kind = root.value("kind", std::string(Application::NAME));
    if (kind != Application::NAME) {
        throw std::invalid_argument(
            "Configuration kind does not match this worker.");
    }

    const Json& paths = group(root, "paths");
#if COPORTSL_APP == COPORTSL_FLUX
    reject_unknown_keys(paths, "paths", {"data", "grid", "cancel_file"});
#else
    reject_unknown_keys(paths, "paths", {"data", "grid", "output", "cancel_file"});
#endif
    assign_path(paths, "data", Config::DATA);
    assign_path(paths, "grid", Config::GRID);
    assign_path(paths, "cancel_file", cancel_file);
#if COPORTSL_APP != COPORTSL_FLUX
    assign_path(paths, "output", Config::OUTPUT);
#endif

    const Json& camera = group(root, "camera");
#if COPORTSL_APP == COPORTSL_FLUX
    reject_unknown_keys(camera, "camera", {
        "npix", "fov_rad", "frequencies_hz", "observer_t", "observer_r_rg",
        "observer_theta_rad", "observer_phi_rad"});
#else
    reject_unknown_keys(camera, "camera", {
        "npix", "fov_rad", "nu_hz", "observer_t", "observer_r_rg",
        "observer_theta_rad", "observer_phi_rad"});
#endif
    assign(camera, "npix", Config::NPIX);
    assign(camera, "fov_rad", Config::FOV);
#if COPORTSL_APP == COPORTSL_FLUX
    assign(camera, "frequencies_hz", Config::NU);
#else
    assign(camera, "nu_hz", Config::NU);
#endif
    assign(camera, "observer_t", Config::OBS_T);
    assign(camera, "observer_r_rg", Config::OBS_R);
    assign(camera, "observer_theta_rad", Config::OBS_TH);
    assign(camera, "observer_phi_rad", Config::OBS_PH);

    const Json& model = group(root, "model");
    reject_unknown_keys(model, "model", {
        "metric", "fluid_backend", "electron", "mbh_msun", "spin", "hs",
        "mdot_msun_per_year", "mdot_sim", "r_low", "r_high", "beta0",
        "sigma_max", "thetae_emit", "ne_emit_cm3", "pol_limit", "p_min",
        "p_max", "gamma_ratio", "beam_angle_rad", "beam_width", "r_source_rg"});
    if (const auto it = model.find("metric"); it != model.end() &&
        it->get<std::string>() != "mksbhac") {
        throw std::invalid_argument("model.metric currently supports only mksbhac.");
    }
    if (const auto it = model.find("fluid_backend"); it != model.end() &&
        it->get<std::string>() != "bhac") {
        throw std::invalid_argument(
            "model.fluid_backend currently supports only bhac.");
    }
    if (const auto it = model.find("electron"); it != model.end()) {
        Config::ELECTRON = parse_electron(it->get<std::string>());
    }
    assign(model, "mbh_msun", Config::MBH);
    assign(model, "spin", Config::SPIN);
    assign(model, "hs", Config::HS);
    assign(model, "mdot_msun_per_year", Config::MDOT);
    assign(model, "mdot_sim", Config::MDOT_SIM);
    assign(model, "r_low", Config::R_LOW);
    assign(model, "r_high", Config::R_HIGH);
    assign(model, "beta0", Config::BETA0);
    assign(model, "sigma_max", Config::SIGMA_MAX);
    assign(model, "thetae_emit", Config::THETAE_EMIT);
    assign(model, "ne_emit_cm3", Config::NE_EMIT);
    assign(model, "pol_limit", Config::POL_LIMIT);
    assign(model, "p_min", Config::P_MIN);
    assign(model, "p_max", Config::P_MAX);
    assign(model, "gamma_ratio", Config::GAMMA_RATIO);
    assign(model, "beam_angle_rad", Config::BEAM_ANGLE);
    assign(model, "beam_width", Config::BEAM_WIDTH);
    assign(model, "r_source_rg", Config::R_SOURCE);

    const Json& ray = group(root, "ray");
    reject_unknown_keys(ray, "ray", {
        "atol", "rtol", "hmin", "lmax", "h0", "cell_fraction",
        "horizon_factor"});
    assign(ray, "atol", Config::RAY_ATOL);
    assign(ray, "rtol", Config::RAY_RTOL);
    assign(ray, "hmin", Config::RAY_HMIN);
    assign(ray, "lmax", Config::RAY_LMAX);
    assign(ray, "h0", Config::RAY_H0);
    assign(ray, "cell_fraction", Config::RAY_CELL);
    assign(ray, "horizon_factor", Config::RAY_HORIZON);

    // The MKSBHAC polar angle map must use the same hslope as the static mesh. from old work
    // model.hs is still readable to maintain format compatibility, but is overwritten by the grid as long as it exists.
    if (const auto value = grid_hslope(Config::GRID)) {
        Config::HS = *value;
    }

    Config::OBS = {
        Config::OBS_T,
        std::log(Config::OBS_R),
        Config::OBS_TH,
        Config::OBS_PH
    };
    Constants::refresh_units();
}

void require_positive(double value, const char* name) {
    if (!std::isfinite(value) || value <= 0.0) {
        throw std::invalid_argument(std::string(name) + " must be positive.");
    }
}

void require_nonnegative(double value, const char* name) {
    if (!std::isfinite(value) || value < 0.0) {
        throw std::invalid_argument(
            std::string(name) + " must be finite and non-negative.");
    }
}

void require_finite(double value, const char* name) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(std::string(name) + " must be finite.");
    }
}

} // namespace

void load(const std::filesystem::path& path) {
    std::ifstream input(path);
    if (!input) {
        throw std::runtime_error("Cannot open configuration: " + path.string());
    }
    Json root;
    input >> root;
    load_common(root);

#if COPORTSL_APP == COPORTSL_GRRT
    const Json& grrt = group(root, "grrt");
    reject_unknown_keys(grrt, "grrt", {
        "task", "postprocess", "frame_start", "frame_end"});
    if (const auto it = grrt.find("task"); it != grrt.end()) {
        const std::string task = it->get<std::string>();
        if (task == "analysis") Config::TASK = Config::Task::Analysis;
        else if (task == "fast") Config::TASK = Config::Task::Fast;
        else if (task == "slow") Config::TASK = Config::Task::Slow;
        else if (task == "region_error") Config::TASK = Config::Task::RegionError;
        else throw std::invalid_argument("Unsupported grrt.task value.");
    }
    assign(grrt, "postprocess", Postprocess::RUN);
    assign(grrt, "frame_start", Config::FRAME_START);
    assign(grrt, "frame_end", Config::FRAME_END);
    const Json& analysis = group(root, "analysis");
    reject_unknown_keys(analysis, "analysis", {
        "sample_dt_rg_over_c", "region_tolerances"});
    assign(analysis, "sample_dt_rg_over_c", Analysis::SAMPLE_DT);
    const Json& tolerances = group(analysis, "region_tolerances");
    reject_unknown_keys(tolerances, "analysis.region_tolerances", {
        "jI", "jP", "aI", "aP", "rhoV", "rhoC"});
    assign(tolerances, "jI", Analysis::REGION_TOLERANCES.jI);
    assign(tolerances, "jP", Analysis::REGION_TOLERANCES.jP);
    assign(tolerances, "aI", Analysis::REGION_TOLERANCES.aI);
    assign(tolerances, "aP", Analysis::REGION_TOLERANCES.aP);
    assign(tolerances, "rhoV", Analysis::REGION_TOLERANCES.rhoV);
    assign(tolerances, "rhoC", Analysis::REGION_TOLERANCES.rhoC);
    const Json& slow = group(root, "slow");
    reject_unknown_keys(slow, "slow", {
        "partition", "region_sets", "region_mode", "window", "manual_set"});
    if (const auto it = slow.find("partition"); it != slow.end()) {
        SlowLight::PARTITION = parse_partition(it->get<std::string>());
        SlowLight::REGION =
            slow_light::regions::definition(SlowLight::PARTITION);
        SlowLight::REGION_SETS = default_region_sets(SlowLight::PARTITION);
        SlowLight::MANUAL_SET = default_manual_set(SlowLight::PARTITION);
    }
    if (const auto it = slow.find("region_sets"); it != slow.end()) {
        SlowLight::REGION_SETS = parse_region_sets(*it);
    }
    if (const auto it = slow.find("region_mode"); it != slow.end()) {
        const std::string mode = it->get<std::string>();
        if (mode == "suggest") SlowLight::REGION_MODE = SlowLight::RegionMode::Suggest;
        else if (mode == "manual") SlowLight::REGION_MODE = SlowLight::RegionMode::Manual;
        else throw std::invalid_argument("slow.region_mode must be suggest or manual.");
    }
    if (const auto it = slow.find("window"); it != slow.end()) {
        const std::string window = it->get<std::string>();
        if (window == "p90") SlowLight::WINDOW = SlowLight::Window::P90;
        else if (window == "p95") SlowLight::WINDOW = SlowLight::Window::P95;
        else if (window == "p99") SlowLight::WINDOW = SlowLight::Window::P99;
        else if (window == "p99.9") SlowLight::WINDOW = SlowLight::Window::P99_9;
        else if (window == "full") SlowLight::WINDOW = SlowLight::Window::Full;
        else throw std::invalid_argument("Unsupported slow.window value.");
    }
    assign(slow, "manual_set", SlowLight::MANUAL_SET);
    const Json& region_error = group(root, "region_error");
    reject_unknown_keys(region_error, "region_error", {"frame_step"});
    assign(region_error, "frame_step", RegionError::FRAME_STEP);
#elif COPORTSL_APP == COPORTSL_FLUX
    const Json& flux = group(root, "flux");
    reject_unknown_keys(flux, "flux", {
        "frame_start", "frame_end", "frame_step", "target_flux_jy", "distance_pc"});
    assign(flux, "frame_start", Config::NT0);
    assign(flux, "frame_end", Config::NT1);
    assign(flux, "frame_step", Config::DNT);
    assign(flux, "target_flux_jy", Config::TARGET_FLUX_JY);
    assign(flux, "distance_pc", Config::DISTANCE_PC);
#else
    const Json& analysis = group(root, "analysis");
    reject_unknown_keys(analysis, "analysis", {
        "sample_dt_rg_over_c", "region_tolerances"});
    assign(analysis, "sample_dt_rg_over_c", Analysis::SAMPLE_DT);
    const Json& tolerances = group(analysis, "region_tolerances");
    reject_unknown_keys(tolerances, "analysis.region_tolerances", {
        "jI", "jP", "aI", "aP", "rhoV", "rhoC"});
    assign(tolerances, "jI", Analysis::REGION_TOLERANCES.jI);
    assign(tolerances, "jP", Analysis::REGION_TOLERANCES.jP);
    assign(tolerances, "aI", Analysis::REGION_TOLERANCES.aI);
    assign(tolerances, "aP", Analysis::REGION_TOLERANCES.aP);
    assign(tolerances, "rhoV", Analysis::REGION_TOLERANCES.rhoV);
    assign(tolerances, "rhoC", Analysis::REGION_TOLERANCES.rhoC);
    const Json& benchmark = group(root, "benchmark");
    reject_unknown_keys(benchmark, "benchmark", {
        "frame_start", "frame_end", "frame_step", "npix_list",
        "core_counts",
        "repeats", "warmup_frames", "run_fast", "run_slow", "partition",
        "window", "core_modes"});
    assign(benchmark, "frame_start", BenchmarkConfig::NT0);
    assign(benchmark, "frame_end", BenchmarkConfig::NT1);
    assign(benchmark, "frame_step", BenchmarkConfig::DNT);
    assign(benchmark, "npix_list", BenchmarkConfig::NPIX_LIST);
    assign(benchmark, "core_counts", BenchmarkConfig::CORE_COUNTS);
    assign(benchmark, "repeats", BenchmarkConfig::REPEATS);
    assign(benchmark, "warmup_frames", BenchmarkConfig::WARMUP_FRAMES);
    assign(benchmark, "run_fast", BenchmarkConfig::RUN_FAST_LIGHT);
    assign(benchmark, "run_slow", BenchmarkConfig::RUN_SLOW_LIGHT);
    if (const auto it = benchmark.find("partition"); it != benchmark.end()) {
        BenchmarkConfig::PARTITION =
            parse_partition(it->get<std::string>());
        BenchmarkConfig::REGION =
            slow_light::regions::definition(BenchmarkConfig::PARTITION);
    }
    assign(benchmark, "window", BenchmarkConfig::WINDOW);
    if (const auto it = benchmark.find("core_modes"); it != benchmark.end()) {
        if (!it->is_array() || it->empty()) {
            throw std::invalid_argument(
                "benchmark.core_modes must be a non-empty array.");
        }
        BenchmarkConfig::CORE_MODES.clear();
        for (const std::string& value :
            it->get<std::vector<std::string>>()) {
            BenchmarkConfig::CORE_MODES.push_back(parse_core_mode(value));
        }
    }
#endif
    validate();
}

void validate() {
    if (Config::NPIX <= 0) {
        throw std::invalid_argument("camera.npix must be a positive integer.");
    }
    require_positive(Config::FOV, "camera.fov_rad");
#if COPORTSL_APP == COPORTSL_FLUX
    if (Config::NU.empty()) {
        throw std::invalid_argument("camera.frequencies_hz cannot be empty.");
    }
    for (double value : Config::NU) require_positive(value, "camera.frequencies_hz[]");
#else
    require_positive(Config::NU, "camera.nu_hz");
#endif
    require_positive(Config::OBS_R, "camera.observer_r_rg");
    require_finite(Config::OBS_T, "camera.observer_t");
    require_finite(Config::OBS_TH, "camera.observer_theta_rad");
    require_finite(Config::OBS_PH, "camera.observer_phi_rad");
    if (!std::isfinite(Config::SPIN) || std::abs(Config::SPIN) > 1.0) {
        throw std::invalid_argument("model.spin must lie in [-1, 1].");
    }
    require_positive(Config::MBH, "model.mbh_msun");
    require_positive(Config::MDOT, "model.mdot_msun_per_year");
    require_positive(Config::MDOT_SIM, "model.mdot_sim");
    require_nonnegative(Config::R_LOW, "model.r_low");
    require_nonnegative(Config::R_HIGH, "model.r_high");
    require_positive(Config::BETA0, "model.beta0");
    require_nonnegative(Config::SIGMA_MAX, "model.sigma_max");
    require_nonnegative(Config::THETAE_EMIT, "model.thetae_emit");
    require_nonnegative(Config::NE_EMIT, "model.ne_emit_cm3");
    if (!std::isfinite(Config::POL_LIMIT) ||
        Config::POL_LIMIT < 0.0 || Config::POL_LIMIT > 1.0) {
        throw std::invalid_argument("model.pol_limit must lie in [0, 1].");
    }
    if (!std::isfinite(Config::P_MIN) || !std::isfinite(Config::P_MAX) ||
        Config::P_MIN <= 2.0 || Config::P_MIN > Config::P_MAX) {
        throw std::invalid_argument(
            "model.p_min must be greater than 2 and no greater than model.p_max.");
    }
    if (!std::isfinite(Config::GAMMA_RATIO) || Config::GAMMA_RATIO <= 1.0) {
        throw std::invalid_argument("model.gamma_ratio must be greater than 1.");
    }
    if (!std::isfinite(Config::BEAM_ANGLE) || Config::BEAM_ANGLE < 0.0 ||
        Config::BEAM_ANGLE > std::numbers::pi) {
        throw std::invalid_argument("model.beam_angle_rad must lie in [0, pi].");
    }
    if ((Config::ELECTRON == Config::BEAM || Config::ELECTRON == Config::LOSS_CONE) &&
        (!std::isfinite(Config::BEAM_WIDTH) || Config::BEAM_WIDTH <= 0.0)) {
        throw std::invalid_argument(
            "model.beam_width must be positive for beam and losscone models.");
    }
    require_nonnegative(Config::R_SOURCE, "model.r_source_rg");
    require_positive(Config::RAY_ATOL, "ray.atol");
    require_positive(Config::RAY_RTOL, "ray.rtol");
    require_positive(Config::RAY_HMIN, "ray.hmin");
    require_positive(Config::RAY_LMAX, "ray.lmax");
    require_positive(Config::RAY_H0, "ray.h0");
    if (Config::RAY_HMIN > Config::RAY_H0) {
        throw std::invalid_argument("ray.hmin must be no greater than ray.h0.");
    }
    if (!std::isfinite(Config::RAY_CELL) ||
        Config::RAY_CELL <= 0.0 || Config::RAY_CELL > 1.0) {
        throw std::invalid_argument("ray.cell_fraction must lie in (0, 1].");
    }
    require_positive(Config::RAY_HORIZON, "ray.horizon_factor");
#if COPORTSL_APP == COPORTSL_GRRT
    if ((Config::FRAME_START < 0) != (Config::FRAME_END < 0) ||
        (Config::FRAME_START >= 0 && Config::FRAME_START > Config::FRAME_END)) {
        throw std::invalid_argument(
            "grrt.frame_start/frame_end must both be -1 or an ordered range.");
    }
    require_positive(Analysis::SAMPLE_DT, "analysis.sample_dt_rg_over_c");
    if (RegionError::FRAME_STEP <= 0) {
        throw std::invalid_argument("region_error.frame_step must be positive.");
    }
    validate_region_sets(SlowLight::REGION, SlowLight::REGION_SETS);
    if (SlowLight::REGION_MODE == SlowLight::RegionMode::Manual) {
        const auto selected = std::find_if(
            SlowLight::REGION_SETS.begin(),
            SlowLight::REGION_SETS.end(),
            [](const auto& item) {
                return item.name == SlowLight::MANUAL_SET;
            });
        if (selected == SlowLight::REGION_SETS.end()) {
            throw std::invalid_argument(
                "slow.manual_set must name an item in slow.region_sets.");
        }
    }
#elif COPORTSL_APP == COPORTSL_FLUX
    if (Config::NT0 > Config::NT1 || Config::DNT <= 0) {
        throw std::invalid_argument("flux frame range or step is invalid.");
    }
    require_positive(Config::TARGET_FLUX_JY, "flux.target_flux_jy");
    require_positive(Config::DISTANCE_PC, "flux.distance_pc");
#else
    require_positive(Analysis::SAMPLE_DT, "analysis.sample_dt_rg_over_c");
    if (BenchmarkConfig::NT0 > BenchmarkConfig::NT1 ||
        BenchmarkConfig::DNT <= 0 ||
        BenchmarkConfig::NPIX_LIST.empty() ||
        BenchmarkConfig::CORE_COUNTS.empty() ||
        BenchmarkConfig::REPEATS <= 0 || BenchmarkConfig::WARMUP_FRAMES < 0) {
        throw std::invalid_argument("benchmark scan configuration is invalid.");
    }
    const auto positive_increasing = [](const std::vector<int>& values) {
        return std::all_of(values.begin(), values.end(),
            [](int value) { return value > 0; }) &&
            std::adjacent_find(values.begin(), values.end(),
                std::greater_equal<int>()) == values.end();
    };
    if (!positive_increasing(BenchmarkConfig::NPIX_LIST)) {
        throw std::invalid_argument(
            "benchmark.npix_list must contain unique, increasing positive integers.");
    }
    if (!positive_increasing(BenchmarkConfig::CORE_COUNTS)) {
        throw std::invalid_argument(
            "benchmark.core_counts must contain unique, increasing positive integers.");
    }
    if (!BenchmarkConfig::RUN_FAST_LIGHT && !BenchmarkConfig::RUN_SLOW_LIGHT) {
        throw std::invalid_argument(
            "benchmark must enable run_fast or run_slow.");
    }
    if (BenchmarkConfig::WINDOW != "p90" && BenchmarkConfig::WINDOW != "p95" &&
        BenchmarkConfig::WINDOW != "p99" && BenchmarkConfig::WINDOW != "p99.9" &&
        BenchmarkConfig::WINDOW != "full") {
        throw std::invalid_argument("benchmark.window is unsupported.");
    }
    if (BenchmarkConfig::CORE_MODES.size() != 1 ||
        BenchmarkConfig::CORE_MODES.front() == BenchmarkConfig::CoreMode::AllLogical) {
        throw std::invalid_argument(
            "benchmark.core_modes must contain exactly one physical-core mode.");
    }
#endif
}

std::string defaults_json() {
    Json root = common_json();
#if COPORTSL_APP == COPORTSL_GRRT
    root["paths"]["output"] = Config::OUTPUT.generic_string();
    root["grrt"] = {
        {"task", "analysis"},
        {"postprocess", Postprocess::RUN},
        {"frame_start", Config::FRAME_START},
        {"frame_end", Config::FRAME_END}
    };
    root["analysis"] = {
        {"sample_dt_rg_over_c", Analysis::SAMPLE_DT},
        {"region_tolerances", {
            {"jI", Analysis::REGION_TOLERANCES.jI},
            {"jP", Analysis::REGION_TOLERANCES.jP},
            {"aI", Analysis::REGION_TOLERANCES.aI},
            {"aP", Analysis::REGION_TOLERANCES.aP},
            {"rhoV", Analysis::REGION_TOLERANCES.rhoV},
            {"rhoC", Analysis::REGION_TOLERANCES.rhoC}
        }}
    };
    root["slow"] = {
        {"region_mode", "suggest"},
        {"window", "p99"},
        {"manual_set", SlowLight::MANUAL_SET},
        {"partition", partition_name(SlowLight::PARTITION)},
        {"region_sets", Json::array()}
    };
    for (const auto& item : SlowLight::REGION_SETS) {
        root["slow"]["region_sets"].push_back({
            {"name", item.name},
            {"keys", item.keys}
        });
    }
    root["region_error"] = {
        {"frame_step", RegionError::FRAME_STEP}
    };
#elif COPORTSL_APP == COPORTSL_FLUX
    root["flux"] = {
        {"frame_start", Config::NT0},
        {"frame_end", Config::NT1},
        {"frame_step", Config::DNT},
        {"target_flux_jy", Config::TARGET_FLUX_JY},
        {"distance_pc", Config::DISTANCE_PC}
    };
#else
    root["paths"]["output"] = Config::OUTPUT.generic_string();
    root["analysis"] = {
        {"sample_dt_rg_over_c", Analysis::SAMPLE_DT},
        {"region_tolerances", {
            {"jI", Analysis::REGION_TOLERANCES.jI},
            {"jP", Analysis::REGION_TOLERANCES.jP},
            {"aI", Analysis::REGION_TOLERANCES.aI},
            {"aP", Analysis::REGION_TOLERANCES.aP},
            {"rhoV", Analysis::REGION_TOLERANCES.rhoV},
            {"rhoC", Analysis::REGION_TOLERANCES.rhoC}
        }}
    };
    root["benchmark"] = {
        {"frame_start", BenchmarkConfig::NT0},
        {"frame_end", BenchmarkConfig::NT1},
        {"frame_step", BenchmarkConfig::DNT},
        {"npix_list", BenchmarkConfig::NPIX_LIST},
        {"core_counts", BenchmarkConfig::CORE_COUNTS},
        {"repeats", BenchmarkConfig::REPEATS},
        {"warmup_frames", BenchmarkConfig::WARMUP_FRAMES},
        {"run_fast", BenchmarkConfig::RUN_FAST_LIGHT},
        {"run_slow", BenchmarkConfig::RUN_SLOW_LIGHT},
        {"partition", partition_name(BenchmarkConfig::PARTITION)},
        {"window", BenchmarkConfig::WINDOW},
        {"core_modes", Json::array()}
    };
    for (const auto mode : BenchmarkConfig::CORE_MODES) {
        root["benchmark"]["core_modes"].push_back(core_mode_name(mode));
    }
#endif
    return root.dump(2);
}

std::string capabilities_json() {
    Json result = {
        {"schema_version", 1},
        {"kind", std::string(Application::NAME)},
        {"fluid_backends", {"bhac"}},
        {"metrics", {"mksbhac"}},
        {"electron_models", {"thermal", "powerlaw", "beam", "losscone"}}
    };
#if COPORTSL_APP == COPORTSL_GRRT
    result["tasks"] = {"analysis", "fast", "slow", "region_error"};
    result["windows"] = {"p90", "p95", "p99", "p99.9", "full"};
    result["partitions"] = {"shell", "jet_shell"};
    Json definitions = Json::object();
    for (const auto& [name, partition] : {
        std::pair{"shell", slow_light::regions::Partition::Shell},
        std::pair{"jet_shell", slow_light::regions::Partition::JetShell}}) {
        Json regions = Json::array();
        for (const auto& item :
            slow_light::regions::definition(partition).regions) {
            regions.push_back({{"key", item.key}, {"label", item.label}});
        }
        definitions[name] = std::move(regions);
    }
    result["regions_by_partition"] = definitions;
    result["regions"] = definitions[partition_name(SlowLight::PARTITION)];
#elif COPORTSL_APP == COPORTSL_BENCHMARK
    result["partitions"] = {"shell", "jet_shell"};
    result["windows"] = {"p90", "p95", "p99", "p99.9", "full"};
    result["core_modes"] = {
        "physical_cores", "performance_cores", "efficiency_cores"};
#endif
    return result.dump(2);
}

bool cancellation_requested() {
    if (cancel_file.empty()) return false;
    std::error_code error;
    const bool exists = std::filesystem::exists(cancel_file, error);
    return !error && exists;
}

void throw_if_cancelled() {
    if (cancellation_requested()) {
        throw std::runtime_error("Task cancelled by user.");
    }
}

} // namespace runtime_config
