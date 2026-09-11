#include "Sha256.h"

#include <algorithm>
#include <array>
#include <fstream>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <vector>

namespace support {
namespace {

constexpr std::array<uint32_t, 64> round_constants = {
    0x428a2f98u, 0x71374491u, 0xb5c0fbcfu, 0xe9b5dba5u,
    0x3956c25bu, 0x59f111f1u, 0x923f82a4u, 0xab1c5ed5u,
    0xd807aa98u, 0x12835b01u, 0x243185beu, 0x550c7dc3u,
    0x72be5d74u, 0x80deb1feu, 0x9bdc06a7u, 0xc19bf174u,
    0xe49b69c1u, 0xefbe4786u, 0x0fc19dc6u, 0x240ca1ccu,
    0x2de92c6fu, 0x4a7484aau, 0x5cb0a9dcu, 0x76f988dau,
    0x983e5152u, 0xa831c66du, 0xb00327c8u, 0xbf597fc7u,
    0xc6e00bf3u, 0xd5a79147u, 0x06ca6351u, 0x14292967u,
    0x27b70a85u, 0x2e1b2138u, 0x4d2c6dfcu, 0x53380d13u,
    0x650a7354u, 0x766a0abbu, 0x81c2c92eu, 0x92722c85u,
    0xa2bfe8a1u, 0xa81a664bu, 0xc24b8b70u, 0xc76c51a3u,
    0xd192e819u, 0xd6990624u, 0xf40e3585u, 0x106aa070u,
    0x19a4c116u, 0x1e376c08u, 0x2748774cu, 0x34b0bcb5u,
    0x391c0cb3u, 0x4ed8aa4au, 0x5b9cca4fu, 0x682e6ff3u,
    0x748f82eeu, 0x78a5636fu, 0x84c87814u, 0x8cc70208u,
    0x90befffau, 0xa4506cebu, 0xbef9a3f7u, 0xc67178f2u
};

uint32_t rotate_right(uint32_t value, unsigned count) {
    return (value >> count) | (value << (32u - count));
}

uint32_t read_u32(const std::byte* data) {
    return
        (static_cast<uint32_t>(data[0]) << 24u) |
        (static_cast<uint32_t>(data[1]) << 16u) |
        (static_cast<uint32_t>(data[2]) << 8u) |
        static_cast<uint32_t>(data[3]);
}

void write_u32(std::byte* data, uint32_t value) {
    data[0] = static_cast<std::byte>(value >> 24u);
    data[1] = static_cast<std::byte>(value >> 16u);
    data[2] = static_cast<std::byte>(value >> 8u);
    data[3] = static_cast<std::byte>(value);
}

} // namespace

Sha256::Sha256()
    : state_{
        0x6a09e667u,
        0xbb67ae85u,
        0x3c6ef372u,
        0xa54ff53au,
        0x510e527fu,
        0x9b05688cu,
        0x1f83d9abu,
        0x5be0cd19u
    } {}

void Sha256::update(std::span<const std::byte> bytes) {
    if (bytes.size() > std::numeric_limits<uint64_t>::max() - byte_count_) {
        throw std::length_error("SHA-256 input is too large.");
    }
    byte_count_ += static_cast<uint64_t>(bytes.size());

    size_t offset = 0;
    if (buffer_size_ != 0) {
        const size_t count = std::min(buffer_.size() - buffer_size_, bytes.size());
        std::copy_n(bytes.data(), count, buffer_.data() + buffer_size_);
        buffer_size_ += count;
        offset += count;
        if (buffer_size_ == buffer_.size()) {
            transform(buffer_.data());
            buffer_size_ = 0;
        }
    }
    while (offset + buffer_.size() <= bytes.size()) {
        transform(bytes.data() + offset);
        offset += buffer_.size();
    }
    const size_t remaining = bytes.size() - offset;
    if (remaining != 0) {
        std::copy_n(bytes.data() + offset, remaining, buffer_.data());
        buffer_size_ = remaining;
    }
}

void Sha256::update(std::string_view text) {
    update(std::as_bytes(std::span{text.data(), text.size()}));
}

void Sha256::update_file(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw std::runtime_error(
            "Cannot open file for SHA-256: " + path.string());
    }

    std::vector<char> block(1024 * 1024);
    while (input) {
        input.read(block.data(), static_cast<std::streamsize>(block.size()));
        const std::streamsize count = input.gcount();
        if (count > 0) {
            update(std::as_bytes(std::span{
                block.data(), static_cast<size_t>(count)}));
        }
    }
    if (!input.eof()) {
        throw std::runtime_error(
            "Failed while reading file for SHA-256: " + path.string());
    }
}

std::array<std::byte, 32> Sha256::digest() const {
    return Sha256(*this).finish();
}

std::string Sha256::hex_digest() const {
    const auto bytes = digest();
    std::ostringstream text;
    text << std::hex << std::setfill('0');
    for (std::byte value : bytes) {
        text << std::setw(2) << static_cast<unsigned>(value);
    }
    return text.str();
}

void Sha256::transform(const std::byte* block) {
    std::array<uint32_t, 64> words = {};
    for (size_t i = 0; i < 16; i++) {
        words[i] = read_u32(block + 4 * i);
    }
    for (size_t i = 16; i < words.size(); i++) {
        const uint32_t s0 =
            rotate_right(words[i - 15], 7) ^
            rotate_right(words[i - 15], 18) ^
            (words[i - 15] >> 3u);
        const uint32_t s1 =
            rotate_right(words[i - 2], 17) ^
            rotate_right(words[i - 2], 19) ^
            (words[i - 2] >> 10u);
        words[i] = words[i - 16] + s0 + words[i - 7] + s1;
    }

    uint32_t a = state_[0];
    uint32_t b = state_[1];
    uint32_t c = state_[2];
    uint32_t d = state_[3];
    uint32_t e = state_[4];
    uint32_t f = state_[5];
    uint32_t g = state_[6];
    uint32_t h = state_[7];
    for (size_t i = 0; i < words.size(); i++) {
        const uint32_t sum1 =
            rotate_right(e, 6) ^ rotate_right(e, 11) ^ rotate_right(e, 25);
        const uint32_t choose = (e & f) ^ (~e & g);
        const uint32_t first = h + sum1 + choose + round_constants[i] + words[i];
        const uint32_t sum0 =
            rotate_right(a, 2) ^ rotate_right(a, 13) ^ rotate_right(a, 22);
        const uint32_t majority = (a & b) ^ (a & c) ^ (b & c);
        const uint32_t second = sum0 + majority;
        h = g;
        g = f;
        f = e;
        e = d + first;
        d = c;
        c = b;
        b = a;
        a = first + second;
    }

    state_[0] += a;
    state_[1] += b;
    state_[2] += c;
    state_[3] += d;
    state_[4] += e;
    state_[5] += f;
    state_[6] += g;
    state_[7] += h;
}

std::array<std::byte, 32> Sha256::finish() {
    const uint64_t bit_count = byte_count_ * 8u;
    const std::byte marker = std::byte{0x80};
    update(std::span{&marker, size_t{1}});
    const std::byte zero = std::byte{0};
    while (buffer_size_ != 56) {
        update(std::span{&zero, size_t{1}});
    }
    std::array<std::byte, 8> length = {};
    for (size_t i = 0; i < length.size(); i++) {
        length[length.size() - 1 - i] =
            static_cast<std::byte>(bit_count >> (8u * i));
    }
    update(length);

    std::array<std::byte, 32> result = {};
    for (size_t i = 0; i < state_.size(); i++) {
        write_u32(result.data() + 4 * i, state_[i]);
    }
    return result;
}

} // namespace support
