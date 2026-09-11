#pragma once

#include <span>

#include "../Region.h"

namespace slow_light::regions {

RegionDefinition make_shells(std::span<const double> edges);

} // namespace slow_light::regions

namespace slow_light::regions::shell {

const RegionDefinition& source();

} // namespace slow_light::regions::shell
