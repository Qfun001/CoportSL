#include "RegionDefinition.h"

#include <stdexcept>

#include "definitions/JetShell.h"
#include "definitions/Shell.h"

namespace slow_light::regions {

const RegionDefinition& definition(Partition partition) {
    switch (partition) {
    case Partition::Shell:
        return shell::source();
    case Partition::JetShell:
        return jet_shell::source();
    }

    throw std::invalid_argument("Unknown region partition.");
}

} // namespace slow_light::regions
