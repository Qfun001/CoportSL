#pragma once

#include <span>

#include "../Region.h"

namespace slow_light::regions {

RegionDefinition make_jet_shells(
    double jet_half_angle,
    std::span<const double> jet_edges,
    std::span<const double> non_jet_edges);

} // namespace slow_light::regions

namespace slow_light::regions::jet_shell {

const RegionDefinition& source();

} // namespace slow_light::regions::jet_shell
