#include "RunDirectory.h"

#include <algorithm>
#include <charconv>
#include <fstream>
#include <iomanip>
#include <limits>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <system_error>
#include <vector>

#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#else
#include <cerrno>
#include <fcntl.h>
#include <sys/file.h>
#include <unistd.h>
#endif

namespace run_io {
namespace {

uint64_t parse_run_name(std::string_view name) {
    constexpr std::string_view prefix = "output";
    if (!name.starts_with(prefix) || name.size() <= prefix.size()) return 0;

    uint64_t number = 0;
    const char* begin = name.data() + prefix.size();
    const char* end = name.data() + name.size();
    const auto [position, error] = std::from_chars(begin, end, number);
    if (error != std::errc{} || position != end || number == 0) return 0;
    return run_name(number) == name ? number : 0;
}

bool config_matches(
    const std::filesystem::path& path,
    std::string_view key,
    std::string_view expected) {

    std::ifstream input(path);
    if (!input) return false;
    const std::string prefix = std::string(key) + "=";
    std::string line;
    while (std::getline(input, line)) {
        if (line.starts_with(prefix)) {
            return std::string_view(line).substr(prefix.size()) == expected;
        }
    }
    return false;
}

std::vector<RunDirectory> find_runs(const std::filesystem::path& category) {
    std::vector<RunDirectory> runs;
    if (!std::filesystem::is_directory(category)) return runs;
    for (const auto& entry : std::filesystem::directory_iterator(category)) {
        if (!entry.is_directory()) continue;
        const std::string name = entry.path().filename().string();
        const uint64_t number = parse_run_name(name);
        if (number != 0) runs.push_back({number, name, entry.path()});
    }
    std::sort(runs.begin(), runs.end(), [](const RunDirectory& lhs, const RunDirectory& rhs) {
        return lhs.number > rhs.number;
    });
    return runs;
}

bool config_matches(
    const RunDirectory& run,
    std::span<const std::pair<std::string_view, std::string_view>> values) {

    return std::all_of(values.begin(), values.end(), [&run](const auto& item) {
        return config_matches(run.path / "config.txt", item.first, item.second);
    });
}

bool is_path_block_line(std::string_view line) {
    return line.starts_with("data=") || line.starts_with("grid=") ||
        line.starts_with("output=") || line.starts_with("analysis=");
}

// Read the status field of the last status record in status.txt, skipping the initial path block.
std::string read_run_status(const std::filesystem::path& path) {
    std::ifstream input(path);
    std::string line;
    std::string status;
    while (std::getline(input, line)) {
        if (is_path_block_line(line)) continue;
        const size_t space = line.find(' ');
        status = space == std::string::npos ? line : line.substr(0, space);
    }
    return status;
}

// Scan the CSV to see if the number of rows and columns match; skip the check if the corresponding dimension is 0.
bool csv_dimensions_match(
    const std::filesystem::path& path,
    uint64_t expected_rows,
    uint64_t expected_columns) {

    std::ifstream input(path);
    if (!input) return false;
    std::string line;
    uint64_t rows = 0;
    while (std::getline(input, line)) {
        if (line.empty()) continue;
        rows++;
        if (expected_columns != 0) {
            const uint64_t columns = static_cast<uint64_t>(
                std::count(line.begin(), line.end(), ',') + 1);
            if (columns != expected_columns) return false;
        }
    }
    if (expected_rows != 0 && rows != expected_rows) return false;
    return true;
}

bool files_complete(
    const run_io::RunDirectory& run,
    const std::vector<std::filesystem::path>& required_files,
    uint64_t expected_rows,
    uint64_t expected_columns) {

    for (const std::filesystem::path& file : required_files) {
        const std::filesystem::path path = run.path / file;
        std::error_code error;
        if (!std::filesystem::is_regular_file(path, error) || error) {
            return false;
        }
        if ((expected_rows != 0 || expected_columns != 0) &&
            !csv_dimensions_match(path, expected_rows, expected_columns)) {
            return false;
        }
    }
    return true;
}

} // namespace

#ifdef _WIN32

RunLock::RunLock(void* handle) noexcept : handle_(handle) {}

RunLock::RunLock(RunLock&& other) noexcept : handle_(other.handle_) {
    other.handle_ = nullptr;
}

RunLock& RunLock::operator=(RunLock&& other) noexcept {
    if (this == &other) return *this;
    if (handle_ != nullptr) CloseHandle(static_cast<HANDLE>(handle_));
    handle_ = other.handle_;
    other.handle_ = nullptr;
    return *this;
}

RunLock::~RunLock() {
    if (handle_ != nullptr) CloseHandle(static_cast<HANDLE>(handle_));
}

#else

RunLock::RunLock(int descriptor) noexcept : descriptor_(descriptor) {}

RunLock::RunLock(RunLock&& other) noexcept : descriptor_(other.descriptor_) {
    other.descriptor_ = -1;
}

RunLock& RunLock::operator=(RunLock&& other) noexcept {
    if (this == &other) return *this;
    if (descriptor_ >= 0) close(descriptor_);
    descriptor_ = other.descriptor_;
    other.descriptor_ = -1;
    return *this;
}

RunLock::~RunLock() {
    if (descriptor_ >= 0) close(descriptor_);
}

#endif

std::string run_name(uint64_t number) {
    if (number == 0) {
        throw std::invalid_argument("Run number must be positive.");
    }
    std::ostringstream name;
    name << "output" << std::setw(4) << std::setfill('0') << number;
    return name.str();
}

RunDirectory allocate_run_directory(const std::filesystem::path& category) {
    std::filesystem::create_directories(category);

    uint64_t maximum = 0;
    for (const auto& entry : std::filesystem::directory_iterator(category)) {
        if (!entry.is_directory()) continue;
        maximum = std::max(maximum, parse_run_name(entry.path().filename().string()));
    }

    if (maximum == std::numeric_limits<uint64_t>::max()) {
        throw std::overflow_error("Run directory number is exhausted: " + category.string());
    }

    for (uint64_t number = maximum + 1; number != 0; number++) {
        RunDirectory run{ number, run_name(number), category / run_name(number) };
        std::error_code error;
        if (std::filesystem::create_directory(run.path, error)) {
            write_run_status(run, "running");
            return run;
        }
        if (error) {
            throw std::filesystem::filesystem_error(
                "Cannot create run directory", run.path, error);
        }
    }
    throw std::overflow_error("Run directory number is exhausted: " + category.string());
}

RunDirectory resolve_run_directory(
    const std::filesystem::path& category,
    std::string_view name) {

    const uint64_t number = parse_run_name(name);
    if (number == 0) {
        throw std::invalid_argument(
            "Invalid run name '" + std::string(name) +
            "'; expected outputNNNN with a positive canonical number.");
    }
    RunDirectory run{ number, std::string(name), category / name };
    if (!std::filesystem::is_directory(run.path)) {
        throw std::runtime_error("Run directory does not exist: " + run.path.string());
    }
    return run;
}

void write_run_paths(
    const RunDirectory& run,
    const std::filesystem::path& data,
    const std::filesystem::path& grid,
    const std::filesystem::path& output,
    const std::filesystem::path& analysis) {

    // Keep existing status records and put the path header at the front of the file.
    std::vector<std::string> records;
    {
        std::ifstream input(run.path / "status.txt");
        std::string line;
        while (std::getline(input, line)) {
            if (is_path_block_line(line) || line.empty()) continue;
            records.push_back(line);
        }
    }
    std::ofstream out(run.path / "status.txt", std::ios::trunc);
    if (!out) {
        throw std::runtime_error("Cannot write run paths: " + run.path.string());
    }
    out << "data=" << data.generic_string() << "\n"
        << "grid=" << grid.generic_string() << "\n"
        << "output=" << output.generic_string() << "\n";
    if (!analysis.empty()) {
        out << "analysis=" << analysis.generic_string() << "\n";
    }
    for (const std::string& record : records) {
        out << record << "\n";
    }
}

void write_run_status(
    const RunDirectory& run,
    std::string_view status,
    int64_t nt0,
    int64_t nt1) {

    std::ofstream out(run.path / "status.txt", std::ios::app);
    if (!out) {
        throw std::runtime_error("Cannot write run status: " + run.path.string());
    }
    out << status;
    if (nt0 >= 0 && nt1 >= 0) {
        out << " nt0=" << nt0 << " nt1=" << nt1;
    }
    out << "\n";
    if (!out) {
        throw std::runtime_error("Cannot write run status: " + run.path.string());
    }
}

std::optional<RunLock> try_lock_run(const RunDirectory& run) {
    const std::filesystem::path path = run.path / ".run.lock";
#ifdef _WIN32
    const HANDLE handle = CreateFileW(
        path.c_str(),
        GENERIC_READ | GENERIC_WRITE,
        0,
        nullptr,
        OPEN_ALWAYS,
        FILE_ATTRIBUTE_NORMAL,
        nullptr);
    if (handle == INVALID_HANDLE_VALUE) {
        const DWORD error = GetLastError();
        if (error == ERROR_SHARING_VIOLATION || error == ERROR_LOCK_VIOLATION) {
            return std::nullopt;
        }
        throw std::filesystem::filesystem_error(
            "Cannot acquire run lock",
            path,
            std::error_code(static_cast<int>(error), std::system_category()));
    }
    return RunLock{static_cast<void*>(handle)};
#else
    const int descriptor = open(path.c_str(), O_RDWR | O_CREAT, 0666);
    if (descriptor < 0) {
        throw std::filesystem::filesystem_error(
            "Cannot open run lock",
            path,
            std::error_code(errno, std::generic_category()));
    }
    if (flock(descriptor, LOCK_EX | LOCK_NB) != 0) {
        const int error = errno;
        close(descriptor);
        if (error == EWOULDBLOCK || error == EAGAIN) return std::nullopt;
        throw std::filesystem::filesystem_error(
            "Cannot acquire run lock",
            path,
            std::error_code(error, std::generic_category()));
    }
    return RunLock{descriptor};
#endif
}

std::optional<RunDirectory> find_latest_run(
    const std::filesystem::path& category,
    std::span<const std::string_view> statuses,
    std::span<const std::pair<std::string_view, std::string_view>> config_values) {

    for (const RunDirectory& run : find_runs(category)) {
        const std::string status = read_run_status(run.path / "status.txt");
        if (std::find(statuses.begin(), statuses.end(), status) == statuses.end()) {
            continue;
        }
        if (config_matches(run, config_values)) return run;
    }
    return std::nullopt;
}

std::optional<RunDirectory> find_latest_run_if(
    const std::filesystem::path& category,
    std::span<const std::string_view> statuses,
    const std::function<bool(const std::filesystem::path&)>& config_predicate) {

    for (const RunDirectory& run : find_runs(category)) {
        const std::string status = read_run_status(run.path / "status.txt");
        if (std::find(statuses.begin(), statuses.end(), status) == statuses.end()) {
            continue;
        }
        if (config_predicate(run.path / "config.txt")) return run;
    }
    return std::nullopt;
}

std::optional<RunDirectory> find_latest_complete_run(
    const std::filesystem::path& category,
    std::string_view config_key,
    std::string_view config_value,
    const std::vector<std::filesystem::path>& required_files,
    uint64_t expected_rows,
    uint64_t expected_columns) {

    const std::pair<std::string_view, std::string_view> config_values[] = {
        {config_key, config_value}
    };
    return find_latest_complete_run(
        category,
        config_values,
        required_files,
        expected_rows,
        expected_columns);
}

std::optional<RunDirectory> find_latest_complete_run(
    const std::filesystem::path& category,
    std::span<const std::pair<std::string_view, std::string_view>> config_values,
    const std::vector<std::filesystem::path>& required_files,
    uint64_t expected_rows,
    uint64_t expected_columns) {

    for (const RunDirectory& run : find_runs(category)) {
        if (!config_matches(run, config_values)) continue;
        if (files_complete(run, required_files, expected_rows, expected_columns)) {
            return run;
        }
    }
    return std::nullopt;
}

std::optional<RunDirectory> find_latest_complete_run_if(
    const std::filesystem::path& category,
    const std::function<bool(const std::filesystem::path&)>& config_predicate,
    const std::vector<std::filesystem::path>& required_files,
    uint64_t expected_rows,
    uint64_t expected_columns) {

    for (const RunDirectory& run : find_runs(category)) {
        if (!config_predicate(run.path / "config.txt")) continue;
        if (files_complete(run, required_files, expected_rows, expected_columns)) {
            return run;
        }
    }
    return std::nullopt;
}

std::optional<RunDirectory> find_latest_matching_run(
    const std::filesystem::path& category,
    std::span<const std::pair<std::string_view, std::string_view>> config_values) {

    for (const RunDirectory& run : find_runs(category)) {
        if (config_matches(run, config_values)) return run;
    }
    return std::nullopt;
}

std::optional<RunDirectory> find_latest_matching_run_if(
    const std::filesystem::path& category,
    const std::function<bool(const std::filesystem::path&)>& config_predicate) {

    for (const RunDirectory& run : find_runs(category)) {
        if (config_predicate(run.path / "config.txt")) return run;
    }
    return std::nullopt;
}

} // namespace run_io
