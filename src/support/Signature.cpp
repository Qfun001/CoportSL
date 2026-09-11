#include "Signature.h"

#include <array>
#include <bit>
#include <cmath>
#include <cstddef>
#include <span>
#include <stdexcept>

namespace support {

void Signature::add_bool(std::string_view name, bool value) {
    begin_field(name, "bool", 1);
    const std::byte byte = value ? std::byte{1} : std::byte{0};
    hash_.update(std::span{&byte, size_t{1}});
}

void Signature::add_int64(std::string_view name, int64_t value) {
    begin_field(name, "int64", sizeof(value));
    add_u64(std::bit_cast<uint64_t>(value));
}

void Signature::add_uint64(std::string_view name, uint64_t value) {
    begin_field(name, "uint64", sizeof(value));
    add_u64(value);
}

void Signature::add_double(std::string_view name, double value) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(
            "Signature floating-point field '" + std::string(name) +
            "' must be finite.");
    }
    if (value == 0.0) value = 0.0; // Unify the numerical identities of positive and negative zero.
    begin_field(name, "float64", sizeof(value));
    add_u64(std::bit_cast<uint64_t>(value));
}

void Signature::add_string(std::string_view name, std::string_view value) {
    begin_field(name, "string", static_cast<uint64_t>(value.size()));
    hash_.update(value);
}

void Signature::add_file(
    std::string_view name,
    const std::filesystem::path& path) {

    std::error_code error;
    const uintmax_t size = std::filesystem::file_size(path, error);
    if (error) {
        throw std::runtime_error(
            "Cannot inspect signature file '" + path.string() + "': " +
            error.message());
    }
    begin_field(name, "file", static_cast<uint64_t>(size));
    hash_.update_file(path);
}

std::string Signature::hex_digest() const {
    return hash_.hex_digest();
}

void Signature::begin_field(
    std::string_view name,
    std::string_view type,
    uint64_t payload_size) {

    add_u64(static_cast<uint64_t>(name.size()));
    hash_.update(name);
    add_u64(static_cast<uint64_t>(type.size()));
    hash_.update(type);
    add_u64(payload_size);
}

void Signature::add_u64(uint64_t value) {
    std::array<std::byte, 8> bytes = {};
    for (size_t i = 0; i < bytes.size(); i++) {
        bytes[bytes.size() - 1 - i] =
            static_cast<std::byte>(value >> (8u * i));
    }
    hash_.update(bytes);
}

} // namespace support
