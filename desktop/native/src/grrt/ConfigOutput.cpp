#include "src/grrt/ConfigOutput.h"

#include "apps/RunConfig.h"

#if COPORTSL_APP != COPORTSL_FLUX

#include <cstdint>
#include <iomanip>

#include "ConfigFields.h"

namespace grrt {

void write_model_config(
    std::ostream& out,
    const fluid::FrameSequence& sequence,
    const Signatures& signatures) {

    out << std::setprecision(17)
        << "input_signature=" << signatures.input << "\n"
        << "model_signature=" << signatures.model << "\n";
    visit_model_fields(sequence, ConfigFieldWriter{out});
    // The input frame range does not participate in the model signature, and is only written as pure information for Python to press.
    // t(n) = T0 + (n - NT0) * DT reconstruction timeline.
    out << "Input::NT0=" << static_cast<int64_t>(sequence.first().index) << "\n"
        << "Input::NT1=" << static_cast<int64_t>(sequence.last().index) << "\n";
}

} // namespace grrt

#endif
