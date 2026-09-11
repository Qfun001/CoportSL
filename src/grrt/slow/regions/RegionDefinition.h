#pragma once

#include "Region.h"

namespace slow_light::regions {

enum class Partition {
    Shell,
    JetShell
};

const RegionDefinition& definition(Partition partition);

} // namespace slow_light::regions
