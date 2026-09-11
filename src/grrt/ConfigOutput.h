#pragma once

#include <iosfwd>

#include "src/grrt/Signatures.h"
#include "src/physics/fluid/FrameSequence.h"

namespace grrt {

// Write four types of model configurations in which GRRT results are shared, pathless, and cannot be replaced by other fields.
void write_model_config(
    std::ostream& out,
    const fluid::FrameSequence& sequence,
    const Signatures& signatures);

} // namespace grrt
