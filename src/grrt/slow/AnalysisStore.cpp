#include "AnalysisStore.h"

#include <array>
#include <cmath>
#include <fstream>
#include <set>
#include <stdexcept>

#include "apps/RunConfig.h"

#if COPORTSL_APP != COPORTSL_FLUX
#include "src/grrt/ConfigCompatibility.h"
#include "src/grrt/ConfigFields.h"
#endif

namespace slow_light::analysis {
#if COPORTSL_APP != COPORTSL_FLUX
namespace {

enum class CompatibilityKind {
    Invalid,
    Exact,
    Approximate
};

struct ExpectationWriter {
    std::vector<grrt::ConfigFieldExpectation>& fields;

    void operator()(std::string_view name, int64_t value) const {
        fields.push_back({
            std::string(name),
            std::to_string(value),
            grrt::ConfigValueKind::Integer
        });
    }

    void operator()(std::string_view name, double value) const {
        fields.push_back({
            std::string(name),
            grrt::config_double(value),
            grrt::ConfigValueKind::Floating
        });
    }

    void operator()(std::string_view name, std::string_view value) const {
        fields.push_back({
            std::string(name),
            std::string(value),
            grrt::ConfigValueKind::Text
        });
    }

    void operator()(std::string_view name, grrt::NamedInt value) const {
        (*this)(name, value.name);
    }

    void operator()(
        std::string_view name,
        grrt::OutputOnlyString value) const {
        (*this)(name, value.value);
    }
};

bool valid_stored_hashes(const grrt::ConfigValues& values) {
    const auto model = values.find("model_signature");
    const auto analysis = values.find("analysis_signature");
    return model != values.end() && analysis != values.end() &&
        grrt::is_sha256(model->second) && grrt::is_sha256(analysis->second);
}

CompatibilityKind analysis_compatibility(
    const std::filesystem::path& config,
    const fluid::FrameSequence& sequence,
    const grrt::Signatures& signatures,
    const regions::RegionDefinition& definition) {

    grrt::ConfigValues values;
    if (!grrt::read_config_values(config, values) ||
        !valid_stored_hashes(values)) {
        return CompatibilityKind::Invalid;
    }
    const auto task = values.find("Config::TASK");
    if (task == values.end() || task->second != "analysis") {
        return CompatibilityKind::Invalid;
    }

    std::vector<grrt::ConfigFieldExpectation> model_fields;
    model_fields.push_back({
        "input_signature",
        signatures.input,
        grrt::ConfigValueKind::Sha256
    });
    grrt::visit_model_fields(sequence, ExpectationWriter{model_fields});
    const grrt::ConfigComparison model =
        grrt::compare_config_values(values, model_fields);
    if (!model.compatible) return CompatibilityKind::Invalid;

    std::vector<grrt::ConfigFieldExpectation> analysis_fields;
    grrt::visit_analysis_fields(ExpectationWriter{analysis_fields});
    analysis_fields.push_back({
        "SlowLight::REGION",
        definition.name,
        grrt::ConfigValueKind::Text
    });
    analysis_fields.push_back({
        "SlowLight::REGION_HASH",
        regions::definition_hash(definition),
        grrt::ConfigValueKind::Text
    });
    grrt::visit_time_origin_fields(ExpectationWriter{analysis_fields});
    const grrt::ConfigComparison analysis =
        grrt::compare_config_values(values, analysis_fields);
    if (!analysis.compatible) return CompatibilityKind::Invalid;

    const bool model_hash_exact =
        values.at("model_signature") == signatures.model;
    const bool analysis_hash_exact =
        values.at("analysis_signature") == signatures.analysis;
    const bool model_values_exact = model.approximate_fields.empty();
    const bool analysis_values_exact = analysis.approximate_fields.empty();

    if (model_hash_exact != model_values_exact) {
        return CompatibilityKind::Invalid;
    }
    if (analysis_hash_exact) {
        return model_hash_exact && analysis_values_exact ?
            CompatibilityKind::Exact : CompatibilityKind::Invalid;
    }
    if (model_hash_exact && analysis_values_exact) {
        return CompatibilityKind::Invalid;
    }
    return CompatibilityKind::Approximate;
}

} // namespace
#endif

std::vector<std::filesystem::path> required_files(
    const regions::RegionDefinition& definition) {

    std::vector<std::filesystem::path> files = {
        "regions/index.csv",
        "suggest/regions.txt",
        "suggest/time_span.csv",
        "suggest/windows.csv"
    };
    for (const auto& info : definition.regions) {
        const std::filesystem::path directory =
            std::filesystem::path("regions") / info.key;
        files.push_back(directory / "contribution.csv");
        files.push_back(directory / "offset_histogram.csv");
        files.push_back(directory / "time_span.csv");
    }
    return files;
}

regions::RegionSelection read_suggestion(
    const run_io::RunDirectory& run,
    const regions::RegionDefinition& definition) {

    regions::RegionSelection selection;
    selection.name = "suggest";
    std::ifstream input(run.path / "suggest" / "regions.txt");
    std::string key;
    while (std::getline(input, key)) {
        if (!key.empty()) selection.keys.push_back(key);
    }
    if (selection.keys.empty()) {
        throw std::runtime_error(
            "Compatible analysis has no suggested region keys.");
    }
    std::set<std::string> valid;
    for (const auto& info : definition.regions) {
        valid.insert(info.key);
    }
    for (const std::string& selected : selection.keys) {
        if (!valid.contains(selected)) {
            throw std::runtime_error(
                "Compatible analysis contains unknown region key '" +
                selected + "'.");
        }
    }
    return selection;
}

StoredWindow read_window(
    const run_io::RunDirectory& run,
    std::string_view name) {

    std::ifstream input(run.path / "suggest" / "windows.csv");
    std::string line;
    if (!std::getline(input, line) || line != "window,left,right") {
        throw std::runtime_error(
            "Compatible analysis has an invalid windows.csv header.");
    }
    while (std::getline(input, line)) {
        const size_t first = line.find(',');
        const size_t second =
            first == std::string::npos ? std::string::npos :
            line.find(',', first + 1);
        if (first == std::string::npos || second == std::string::npos ||
            line.find(',', second + 1) != std::string::npos) {
            throw std::runtime_error(
                "Compatible analysis contains an invalid window row.");
        }
        if (std::string_view(line).substr(0, first) != name) continue;
        const double left = std::stod(line.substr(first + 1, second - first - 1));
        const double right = std::stod(line.substr(second + 1));
        if (!std::isfinite(left) || !std::isfinite(right) || left > right) {
            throw std::runtime_error(
                "Compatible analysis contains an invalid selected window.");
        }
        return {std::string(name), left, right};
    }
    throw std::runtime_error(
        "Compatible analysis does not contain window '" +
        std::string(name) + "'.");
}

std::optional<AnalysisResult> find_stored_analysis(
    const std::filesystem::path& root,
    std::string_view model_signature,
    std::string_view analysis_signature,
    const regions::RegionDefinition& definition) {

    const auto run = run_io::find_latest_complete_run(
        root,
        std::array{
            std::pair<std::string_view, std::string_view>{
                "model_signature", model_signature},
            std::pair<std::string_view, std::string_view>{
                "analysis_signature", analysis_signature}
        },
        required_files(definition));
    if (!run.has_value()) return std::nullopt;
    return AnalysisResult{
        *run,
        read_suggestion(*run, definition),
        std::string(model_signature),
        std::string(analysis_signature),
        true
    };
}

#if COPORTSL_APP != COPORTSL_FLUX
std::optional<AnalysisResult> find_compatible_stored_analysis(
    const std::filesystem::path& root,
    const fluid::FrameSequence& sequence,
    const grrt::Signatures& signatures,
    const regions::RegionDefinition& definition) {

    const std::vector<std::filesystem::path> files = required_files(definition);
    for (const CompatibilityKind kind : {
        CompatibilityKind::Exact,
        CompatibilityKind::Approximate
    }) {
        const auto run = run_io::find_latest_complete_run_if(
            root,
            [&](const std::filesystem::path& config) {
                return analysis_compatibility(
                    config, sequence, signatures, definition) == kind;
            },
            files);
        if (run.has_value()) {
            return AnalysisResult{
                *run,
                read_suggestion(*run, definition),
                signatures.model,
                signatures.analysis,
                true
            };
        }
    }
    return std::nullopt;
}
#endif

} // namespace slow_light::analysis
