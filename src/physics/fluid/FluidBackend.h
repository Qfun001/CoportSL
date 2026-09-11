#pragma once

#include <concepts>
#include <filesystem>
#include <vector>

#include "apps/RunConfig.h"
#include "bhac/BhacBackend.h"
#include "src/support/Signature.h"

namespace fluid {

template <int Id>
struct BackendFor;

template <>
struct BackendFor<Config::BHAC> {
    using type = bhac::Backend;
};

using Backend = typename BackendFor<Config::FLUID_BACKEND>::type;

// The new backend must discover the snapshot within its own boundaries and define path-independent numeric input identities.
template <typename Type>
concept InputBackend = requires(
    const std::filesystem::path& path,
    const FrameInfo& frame,
    support::Signature& signature) {

    { Type::discover_frames(path) } -> std::same_as<std::vector<FrameInfo>>;
    Type::add_input_identity(signature, path, frame);
};

static_assert(InputBackend<Backend>);

} // namespace fluid
