#include "ImageError.h"

#include <cmath>
#include <stdexcept>
#include <string>

namespace grrt {

namespace {

void require_finite_stokes(
    std::span<const StokesPixel> image,
    const char* role) {

    constexpr std::array<const char*, 4> names = {"I", "Q", "U", "V"};
    for (size_t pixel = 0; pixel < image.size(); pixel++) {
        for (size_t stokes = 0; stokes < names.size(); stokes++) {
            if (!std::isfinite(image[pixel][stokes])) {
                throw std::domain_error(
                    std::string("Image error ") + role +
                    " has non-finite Stokes " + names[stokes] +
                    " at pixel " + std::to_string(pixel) + ".");
            }
        }
    }
}

} // namespace

std::array<double, 4> image_error(
    std::span<const StokesPixel> image,
    std::span<const StokesPixel> reference) {

    if (image.empty() || image.size() != reference.size()) {
        throw std::invalid_argument(
            "Image error requires non-empty Stokes images with equal sizes.");
    }
    require_finite_stokes(reference, "reference");
    require_finite_stokes(image, "comparison image");
    double denominator = 0.0;
    for (const StokesPixel& pixel : reference) {
        denominator += std::abs(pixel[0]);
    }
    if (!(denominator > 0.0) || !std::isfinite(denominator)) {
        throw std::domain_error(
            "Image error is undefined for zero or non-finite reference Stokes I.");
    }
    std::array<double, 4> result = {};
    for (size_t pixel = 0; pixel < image.size(); pixel++) {
        for (size_t stokes = 0; stokes < result.size(); stokes++) {
            result[stokes] +=
                std::abs(image[pixel][stokes] - reference[pixel][stokes]);
        }
    }
    for (double& value : result) {
        value /= denominator;
        if (!std::isfinite(value)) {
            throw std::domain_error("Image error result is non-finite.");
        }
    }
    return result;
}

} // namespace grrt
