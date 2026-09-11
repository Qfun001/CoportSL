#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <span>
#include <string>
#include <string_view>

namespace support {

class Sha256 {
public:
    Sha256();

    void update(std::span<const std::byte> bytes);
    void update(std::string_view text);
    void update_file(const std::filesystem::path& path);

    std::array<std::byte, 32> digest() const;
    std::string hex_digest() const;

private:
    void transform(const std::byte* block);
    std::array<std::byte, 32> finish();

    std::array<uint32_t, 8> state_;
    std::array<std::byte, 64> buffer_ = {};
    size_t buffer_size_ = 0;
    uint64_t byte_count_ = 0;
};

} // namespace support
