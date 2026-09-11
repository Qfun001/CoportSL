#include "RunConfig.h"

#include <iostream>
#include <string_view>

#if COPORTSL_APP == COPORTSL_GRRT
namespace grrt_app {
int inspect_input();
int run();
}
#elif COPORTSL_APP == COPORTSL_FLUX
namespace flux_app {
int run();
}
#elif COPORTSL_APP == COPORTSL_BENCHMARK
namespace benchmark_app {
int run(int argc, char** argv);
}
#endif

int main(int argc, char** argv) {
    if (argc == 2 && std::string_view(argv[1]) == "--show-app") {
        std::cout << Application::NAME << "\n";
        return 0;
    }
#if COPORTSL_APP == COPORTSL_GRRT
    if (argc == 2 && std::string_view(argv[1]) == "--inspect-input") {
        return grrt_app::inspect_input();
    }
    if (argc != 1) {
        std::cerr << "Unsupported GRRT option: " << argv[1] << "\n";
        return 2;
    }
    return grrt_app::run();
#elif COPORTSL_APP == COPORTSL_FLUX
    if (argc != 1) {
        std::cerr << "Unsupported Flux option: " << argv[1] << "\n";
        return 2;
    }
    return flux_app::run();
#else
    return benchmark_app::run(argc, argv);
#endif
}
