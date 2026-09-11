#pragma once

#include <cstddef>

#include "src/grrt/SampleTransfer.h"

namespace medium {

// A complete query obtained by parsing the medium at a single ray sample point. Fast emission_time
// Fixed for the entire image; Slow provides different times for different sample points on the same ray.
struct Query {
    const grrt::TransferSample& sample;
    size_t sample_index = 0;
    double observer_frequency = 0.0;
    double emission_time = 0.0;
};

class Sampler {
public:
    virtual ~Sampler() = default;

    // Returning false indicates that the sampling point is not within the medium definition domain.
    virtual bool sample(
        const Query& query,
        TransferCoefficients& result) const = 0;
};

} // namespace medium
