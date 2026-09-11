#include "FrameCache.h"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>

namespace fluid {
namespace {

size_t closest_frame(const std::vector<double>& times, double target) {
    auto upper = std::lower_bound(times.begin(), times.end(), target);
    if (upper == times.begin()) return 0;
    if (upper == times.end()) return times.size() - 1;
    const size_t hi = static_cast<size_t>(upper - times.begin());
    const size_t lo = hi - 1;
    return target - times[lo] <= times[hi] - target ? lo : hi;
}

} // namespace

size_t FrameCache::bytes() const {
    size_t result = base_frame_.bytes();
    for (const auto& slot : frame_slots_) {
        result += slot.bytes();
    }
    return result;
}

size_t FrameCache::frame_count() const noexcept {
    return times_.size();
}

double FrameCache::base_time() const noexcept {
    return base_time_;
}

FrameCache FrameCache::load(
    const FrameSequence& sequence,
    const FrameInfo& first_base,
    double time_offset_min,
    double time_offset_max) {

    if (!std::isfinite(time_offset_min) || !std::isfinite(time_offset_max) ||
        time_offset_min > time_offset_max) {
        throw std::invalid_argument(
            "Slow-light time offsets must be finite and ordered.");
    }
    const std::vector<FrameInfo>& all = sequence.frames;
    const double first_base_time = first_base.time;
    const double raw_begin = first_base_time + time_offset_min;
    const double raw_end = first_base_time + time_offset_max;
    const double scale = std::max({
        1.0, std::abs(raw_begin), std::abs(raw_end),
        std::abs(sequence.first().time), std::abs(sequence.last().time)});
    const double tolerance = 1.0e-10 * scale;
    if (raw_begin < sequence.first().time - tolerance ||
        raw_end > sequence.last().time + tolerance) {
        throw std::runtime_error(
            "Slow-light frame cache window is outside the validated input timeline.");
    }
    const double requested_begin = std::max(
        raw_begin, sequence.first().time);
    const double requested_end = std::min(
        raw_end, sequence.last().time);

    FrameCache cache;
    cache.base_time_ = first_base_time;
    cache.time_offset_min_ = time_offset_min;
    cache.time_offset_max_ = time_offset_max;
    cache.requested_begin_ = requested_begin;
    cache.requested_end_ = requested_end;

    auto first_after_begin = std::lower_bound(
        all.begin(), all.end(), cache.requested_begin_,
        [](const FrameInfo& frame, double time) {
            return frame.time < time;
        });
    size_t begin = static_cast<size_t>(first_after_begin - all.begin());
    if (begin > 0) begin--;

    auto first_at_or_after_end = std::lower_bound(
        all.begin(), all.end(), cache.requested_end_,
        [](const FrameInfo& frame, double time) {
            return frame.time < time;
        });
    size_t end = first_at_or_after_end == all.end() ?
        all.size() - 1 :
        static_cast<size_t>(first_at_or_after_end - all.begin());
    if (end + 1 < all.size() && all[end].time < cache.requested_end_) end++;
    if (end < begin) {
        throw std::runtime_error(
            "No GRMHD frames overlap the requested window.");
    }

    const size_t frame_count = end - begin + 1;
    cache.times_.reserve(frame_count);
    cache.slots_.reserve(frame_count);
    const size_t slot_count = frame_count + 2;
    cache.frame_slots_.resize(slot_count);
    cache.free_slots_.reserve(2);
    for (size_t slot = frame_count; slot < slot_count; slot++) {
        cache.free_slots_.push_back(slot);
    }
    for (size_t index = 0; index < frame_count; index++) {
        const FrameInfo& info = all[begin + index];
        cache.frame_slots_[index] = Backend::load_frame(info.path);
        const auto& frame = cache.frame_slots_[index];
        cache.max_float_absolute_error_ = std::max(
            cache.max_float_absolute_error_,
            frame.max_float_absolute_error);
        cache.max_float_relative_error_ = std::max(
            cache.max_float_relative_error_,
            frame.max_float_relative_error);
        cache.times_.push_back(info.time);
        cache.slots_.push_back(index);
        std::cout << "Slow-light frame loaded: " << info.path.filename()
            << " time=" << info.time << "\n";
    }

    cache.pending_paths_.reserve(all.size());
    cache.pending_times_.reserve(all.size());
    for (const auto& info : all) {
        cache.pending_paths_.push_back(info.path);
        cache.pending_times_.push_back(info.time);
    }
    cache.base_frame_index_ = closest_frame(
        cache.pending_times_, first_base_time);
    cache.base_frame_ = Backend::load_frame(
        cache.pending_paths_[cache.base_frame_index_]);
    cache.max_float_absolute_error_ = std::max(
        cache.max_float_absolute_error_,
        cache.base_frame_.max_float_absolute_error);
    cache.max_float_relative_error_ = std::max(
        cache.max_float_relative_error_,
        cache.base_frame_.max_float_relative_error);
    cache.next_frame_ = end + 1;
    cache.available_begin_ = cache.times_.front();
    cache.available_end_ = cache.times_.back();
    cache.advance(first_base_time);
    const double memory_gib = static_cast<double>(cache.bytes()) /
        (1024.0 * 1024.0 * 1024.0);
    std::cout << "Slow-light frame cache: frames=" << cache.times_.size()
        << " base_time=" << cache.base_time_
        << " requested_begin=" << cache.requested_begin_
        << " requested_end=" << cache.requested_end_
        << " available=[" << cache.available_begin_
        << "," << cache.available_end_ << "]"
        << " memory=" << memory_gib << " GiB"
        << " max_float_absolute_error="
        << cache.max_float_absolute_error_
        << " max_float_relative_error="
        << cache.max_float_relative_error_ << "\n";
    return cache;
}

void FrameCache::advance(double base_time) {
    if (base_time < base_time_) {
        throw std::invalid_argument(
            "Slow-light frame cache cannot move backward in time.");
    }

    base_time_ = base_time;
    requested_begin_ = base_time + time_offset_min_;
    requested_end_ = base_time + time_offset_max_;

    while (times_.size() > 1 && times_[1] <= requested_begin_) {
        free_slots_.push_back(slots_.front());
        times_.erase(times_.begin());
        slots_.erase(slots_.begin());
    }

    while (next_frame_ < pending_times_.size() &&
        (pending_times_[next_frame_] <= requested_end_ ||
            times_.back() < requested_end_)) {
        size_t slot = 0;
        if (free_slots_.empty()) {
            // One side of a non-uniform timeline may be denser than the other; as the window moves forward,
            // The number of new frames is not necessarily equal to the number of frames just released.
            slot = frame_slots_.size();
            frame_slots_.emplace_back();
        }
        else {
            slot = free_slots_.back();
            free_slots_.pop_back();
        }
        frame_slots_[slot] = Backend::load_frame(
            pending_paths_[next_frame_]);
        const auto& frame = frame_slots_[slot];
        max_float_absolute_error_ = std::max(
            max_float_absolute_error_,
            frame.max_float_absolute_error);
        max_float_relative_error_ = std::max(
            max_float_relative_error_,
            frame.max_float_relative_error);
        times_.push_back(pending_times_[next_frame_]);
        slots_.push_back(slot);
        std::cout << "Slow-light frame advanced: "
            << pending_paths_[next_frame_].filename()
            << " time=" << pending_times_[next_frame_] << "\n";
        next_frame_++;
    }

    available_begin_ = times_.front();
    available_end_ = times_.back();
    if (available_end_ < requested_end_) {
        throw std::runtime_error(
            "GRMHD data do not cover the requested slow-light future window.");
    }
    const size_t base_frame_index =
        closest_frame(pending_times_, base_time);
    if (base_frame_index != base_frame_index_) {
        base_frame_ = Backend::load_frame(
            pending_paths_[base_frame_index]);
        base_frame_index_ = base_frame_index;
        max_float_absolute_error_ = std::max(
            max_float_absolute_error_,
            base_frame_.max_float_absolute_error);
        max_float_relative_error_ = std::max(
            max_float_relative_error_,
            base_frame_.max_float_relative_error);
        std::cout << "Slow-light base frame advanced: "
            << pending_paths_[base_frame_index].filename()
            << " time=" << pending_times_[base_frame_index] << "\n";
    }
}

bool FrameCache::sample(
    double time,
    bool fixed_frame,
    const std::array<double, 4>& x,
    const Backend::Location& location,
    State& state,
    const std::array<std::array<double, 4>, 4>& gdown,
    const std::array<std::array<double, 4>, 4>& gup) const {

    if (fixed_frame) {
        return Backend::sample_frame(
            base_frame_,
            x,
            location,
            state,
            gdown,
            gup);
    }

    auto upper = std::lower_bound(times_.begin(), times_.end(), time);
    size_t hi = 0;
    size_t lo = 0;
    if (upper == times_.begin()) {
        hi = lo = 0;
    }
    else if (upper == times_.end()) {
        hi = lo = times_.size() - 1;
    }
    else {
        hi = static_cast<size_t>(upper - times_.begin());
        lo = hi - 1;
    }

    if (lo == hi) {
        return Backend::sample_frame(
            frame_slots_[slots_[lo]],
            x,
            location,
            state,
            gdown,
            gup);
    }
    const double weight =
        (time - times_[lo]) / (times_[hi] - times_[lo]);
    return Backend::sample_frames(
        frame_slots_[slots_[lo]],
        frame_slots_[slots_[hi]],
        weight,
        x,
        location,
        state,
        gdown,
        gup);
}

} // namespace fluid
