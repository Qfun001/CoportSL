#pragma once

#include <cstdint>
#include <filesystem>
#include <functional>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace run_io {

struct RunDirectory {
    uint64_t number = 0;
    std::string name;
    std::filesystem::path path;
};

// A running directory is exclusively occupied during the holding period; the lock is released by the operating system when the process exits abnormally.
class RunLock {
public:
    RunLock() = default;
    RunLock(const RunLock&) = delete;
    RunLock& operator=(const RunLock&) = delete;
    RunLock(RunLock&& other) noexcept;
    RunLock& operator=(RunLock&& other) noexcept;
    ~RunLock();

private:
#ifdef _WIN32
    explicit RunLock(void* handle) noexcept;
    void* handle_ = nullptr;
#else
    explicit RunLock(int descriptor) noexcept;
    int descriptor_ = -1;
#endif

    friend std::optional<RunLock> try_lock_run(const RunDirectory& run);
};

std::string run_name(uint64_t number);

RunDirectory allocate_run_directory(const std::filesystem::path& category);

RunDirectory resolve_run_directory(
    const std::filesystem::path& category,
    std::string_view name);

// Write the path header of status.txt (data/grid/output each has one line, analysis is optional),
// And keep existing status records.
void write_run_paths(
    const RunDirectory& run,
    const std::filesystem::path& data,
    const std::filesystem::path& grid,
    const std::filesystem::path& output,
    const std::filesystem::path& analysis = {});

// Append a running status record; nt0/nt1 is -1, indicating an unknown range.
void write_run_status(
    const RunDirectory& run,
    std::string_view status,
    int64_t nt0 = -1,
    int64_t nt1 = -1);

std::optional<RunLock> try_lock_run(const RunDirectory& run);

std::optional<RunDirectory> find_latest_run(
    const std::filesystem::path& category,
    std::span<const std::string_view> statuses,
    std::span<const std::pair<std::string_view, std::string_view>> config_values);

// Finds the latest results for identity matches; does not look at status and CSV integrity.
std::optional<RunDirectory> find_latest_matching_run(
    const std::filesystem::path& category,
    std::span<const std::pair<std::string_view, std::string_view>> config_values);

std::optional<RunDirectory> find_latest_complete_run(
    const std::filesystem::path& category,
    std::string_view config_key,
    std::string_view config_value,
    const std::vector<std::filesystem::path>& required_files = {},
    uint64_t expected_rows = 0,
    uint64_t expected_columns = 0);

std::optional<RunDirectory> find_latest_complete_run(
    const std::filesystem::path& category,
    std::span<const std::pair<std::string_view, std::string_view>> config_values,
    const std::vector<std::filesystem::path>& required_files = {},
    uint64_t expected_rows = 0,
    uint64_t expected_columns = 0);

std::optional<RunDirectory> find_latest_complete_run_if(
    const std::filesystem::path& category,
    const std::function<bool(const std::filesystem::path&)>& config_predicate,
    const std::vector<std::filesystem::path>& required_files = {},
    uint64_t expected_rows = 0,
    uint64_t expected_columns = 0);

} // namespace run_io
