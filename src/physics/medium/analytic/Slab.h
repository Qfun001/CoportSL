#pragma once

#include "src/physics/medium/Coefficients.h"
#include "src/physics/medium/Medium.h"

namespace medium::analytic {

// An analytic medium with constant coefficients that is finite along one spatial coordinate axis and infinite in other directions.
class Slab final : public Sampler {
public:
    Slab(
        int axis,
        double minimum,
        double maximum,
        const NamedCoefficients& coefficients);

    bool sample(
        const Query& query,
        TransferCoefficients& result) const override;

private:
    int axis_ = 1;
    double minimum_ = 0.0;
    double maximum_ = 0.0;
    TransferCoefficients coefficients_ = {};
};

} // namespace medium::analytic
