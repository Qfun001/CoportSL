#include "Signatures.h"

#include <cstdint>
#include <string>

#include "ConfigFields.h"
#include "src/grrt/slow/regions/Region.h"
#include "src/physics/fluid/FluidBackend.h"
#include "src/support/Signature.h"

namespace grrt {
namespace {

struct SignatureFieldWriter {
    support::Signature& signature;

    void operator()(std::string_view name, int64_t value) const {
        signature.add_int64(name, value);
    }

    void operator()(std::string_view name, double value) const {
        signature.add_double(name, value);
    }

    void operator()(std::string_view name, std::string_view value) const {
        signature.add_string(name, value);
    }

    void operator()(std::string_view name, NamedInt value) const {
        signature.add_int64(name, value.value);
    }

    void operator()(std::string_view, OutputOnlyString) const {
    }
};

void add_analysis_parameters(support::Signature& signature) {
    visit_analysis_fields(SignatureFieldWriter{signature});

    const auto& definition = SlowLight::REGION;
    signature.add_string("Region::name", definition.name);
    signature.add_string("Region::signature", definition.signature);
    signature.add_uint64(
        "Region::count", static_cast<uint64_t>(definition.regions.size()));
    for (size_t index = 0; index < definition.regions.size(); index++) {
        const std::string prefix = "Region::" + std::to_string(index);
        signature.add_string(prefix + "::key", definition.regions[index].key);
        signature.add_string(prefix + "::label", definition.regions[index].label);
    }
    visit_time_origin_fields(SignatureFieldWriter{signature});
}

} // namespace

Signatures make_signatures(const fluid::FrameSequence& sequence) {
    return make_signatures(sequence, Config::GRID);
}

Signatures make_signatures(
    const fluid::FrameSequence& sequence,
    const std::filesystem::path& grid_file) {

    Signatures result;
    support::Signature input;
    fluid::Backend::add_input_identity(
        input, grid_file, sequence.first());
    // Data frame number range participates in input identity: the same physical data on overlapping frames
    // It only changes with the data range and is a data identity rather than a run selection.
    input.add_int64("Input::NT0", sequence.first().index);
    input.add_int64("Input::NT1", sequence.last().index);
    result.input = input.hex_digest();

    support::Signature model;
    visit_model_fields(sequence, SignatureFieldWriter{model});
    model.add_string("input_signature", result.input);

    result.model = model.hex_digest();

    support::Signature analysis;
    analysis.add_string("model_signature", result.model);
    add_analysis_parameters(analysis);
    result.analysis = analysis.hex_digest();
    return result;
}

} // namespace grrt
