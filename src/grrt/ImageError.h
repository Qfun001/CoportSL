#pragma once

#include <array>
#include <span>

namespace grrt {

using StokesPixel = std::array<double, 4>;

std::array<double, 4> image_error(
    std::span<const StokesPixel> image,
    std::span<const StokesPixel> reference);

} // namespace grrt
