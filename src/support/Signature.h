#pragma once

#include <cstdint>
#include <filesystem>
#include <string>
#include <string_view>

#include "Sha256.h"

namespace support {

// Use field name, type and length as boundaries to generate cross-platform stable standardized signatures.
class Signature {
public:
    void add_bool(std::string_view name, bool value);
    void add_int64(std::string_view name, int64_t value);
    void add_uint64(std::string_view name, uint64_t value);
    void add_double(std::string_view name, double value);
    void add_string(std::string_view name, std::string_view value);
    void add_file(std::string_view name, const std::filesystem::path& path);

    std::string hex_digest() const;

private:
    void begin_field(
        std::string_view name,
        std::string_view type,
        uint64_t payload_size);
    void add_u64(uint64_t value);

    Sha256 hash_;
};

} // namespace support
