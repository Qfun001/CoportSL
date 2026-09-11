#include "apps/RunConfig.h"

#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#include "src/config/Runtime.h"
#include "src/support/Event.h"

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
    try {
        std::vector<std::string> arguments;
        arguments.reserve(static_cast<size_t>(argc));
        arguments.emplace_back(argv[0]);
        for (int i = 1; i < argc; i++) {
            const std::string_view argument = argv[i];
            if (argument == "--config") {
                if (i + 1 >= argc) {
                    throw std::invalid_argument(
                        "--config requires a JSON path.");
                }
                runtime_config::load(argv[++i]);
                continue;
            }
            arguments.emplace_back(argument);
        }

        if (arguments.size() == 2 && arguments[1] == "--show-app") {
            std::cout << Application::NAME << "\n";
            return 0;
        }
        if (arguments.size() == 2 &&
            arguments[1] == "--dump-default-config") {
            std::cout << runtime_config::defaults_json() << "\n";
            return 0;
        }
        if (arguments.size() == 2 && arguments[1] == "--capabilities") {
            std::cout << runtime_config::capabilities_json() << "\n";
            return 0;
        }
        if (arguments.size() == 3 &&
            arguments[1] == "--validate-config") {
            runtime_config::load(arguments[2]);
            std::cout << "Configuration valid\n";
#if COPORTSL_APP != COPORTSL_FLUX
            std::cout << "output_root="
                << Config::OUTPUT.generic_string() << "\n"
                << "analysis_output="
                << (Config::OUTPUT / "analysis").generic_string() << "\n";
#endif
#if COPORTSL_APP == COPORTSL_BENCHMARK
            std::cout << "benchmark_output="
                << (Config::OUTPUT / "benchmark").generic_string() << "\n";
#endif
            return 0;
        }

        std::vector<char*> worker_argv;
        worker_argv.reserve(arguments.size());
        for (std::string& argument : arguments) {
            worker_argv.push_back(argument.data());
        }

#if COPORTSL_APP == COPORTSL_GRRT
        runtime_config::throw_if_cancelled();
        if (arguments.size() == 2 && arguments[1] == "--inspect-input") {
            return grrt_app::inspect_input();
        }
        if (arguments.size() != 1) {
            std::cerr << "Unsupported GRRT option: " << arguments[1] << "\n";
            return 2;
        }
        return grrt_app::run();
#elif COPORTSL_APP == COPORTSL_FLUX
        runtime_config::throw_if_cancelled();
        if (arguments.size() != 1) {
            std::cerr << "Unsupported Flux option: " << arguments[1] << "\n";
            return 2;
        }
        return flux_app::run();
#else
        runtime_config::throw_if_cancelled();
        return benchmark_app::run(
            static_cast<int>(worker_argv.size()), worker_argv.data());
#endif
    }
    catch (const std::exception& error) {
        std::cerr << "Configuration error: " << error.what() << "\n";
        event::error(error.what());
        return 2;
    }
}
