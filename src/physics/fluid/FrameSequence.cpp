#include "FrameSequence.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>

namespace fluid {
namespace {

constexpr double relative_tolerance = 1.0e-10;

bool close(double lhs, double rhs) {
    const double scale = std::max({1.0, std::abs(lhs), std::abs(rhs)});
    return std::abs(lhs - rhs) <= relative_tolerance * scale;
}

std::string frame_name(const FrameInfo& frame) {
    std::ostringstream text;
    text << "frame " << frame.index << " at time " << frame.time;
    return text.str();
}

} // namespace

const FrameInfo& FrameSequence::first() const {
    if (frames.empty()) {
        throw std::logic_error("FrameSequence has no first frame.");
    }
    return frames.front();
}

const FrameInfo& FrameSequence::last() const {
    if (frames.empty()) {
        throw std::logic_error("FrameSequence has no last frame.");
    }
    return frames.back();
}

FrameSequence make_frame_sequence(std::vector<FrameInfo> frames) {
    if (frames.size() < 2) {
        throw std::invalid_argument(
            "A GRMHD frame sequence requires at least two snapshots.");
    }

    std::sort(frames.begin(), frames.end(), [](const FrameInfo& lhs, const FrameInfo& rhs) {
        return lhs.index < rhs.index;
    });

    for (const FrameInfo& frame : frames) {
        if (!std::isfinite(frame.time)) {
            throw std::invalid_argument(
                "GRMHD " + frame_name(frame) + " has a non-finite time.");
        }
    }

    double min_interval = std::numeric_limits<double>::infinity();
    for (size_t i = 1; i < frames.size(); i++) {
        const int64_t previous = frames[i - 1].index;
        const int64_t current = frames[i].index;
        if (current == previous) {
            throw std::invalid_argument(
                "GRMHD frame index " + std::to_string(current) + " is duplicated.");
        }
        if (current < previous) {
            throw std::invalid_argument(
                "GRMHD frame indices must increase after sorting.");
        }
        if (!(frames[i].time > frames[i - 1].time)) {
            throw std::invalid_argument(
                "GRMHD times must increase with frame number: " +
                frame_name(frames[i - 1]) + ", then " + frame_name(frames[i]) + ".");
        }
        min_interval = std::min(
            min_interval, frames[i].time - frames[i - 1].time);
    }

    const double interval_count = static_cast<double>(frames.size() - 1);
    const double mean_interval =
        (frames.back().time - frames.front().time) / interval_count;
    if (!(min_interval > 0.0) || !std::isfinite(min_interval) ||
        !(mean_interval > 0.0) || !std::isfinite(mean_interval)) {
        throw std::invalid_argument(
            "GRMHD frame interval must be finite and positive.");
    }
    bool uniform = true;
    for (size_t i = 1; i < frames.size(); i++) {
        const double interval = frames[i].time - frames[i - 1].time;
        uniform = uniform && close(interval, mean_interval);
    }

    return FrameSequence{
        std::move(frames),
        uniform ? mean_interval : min_interval,
        uniform
    };
}

std::vector<FrameInfo> sample_frames(
    const FrameSequence& sequence,
    double sample_dt) {

    if (sequence.frames.size() < 2 || !(sequence.dt > 0.0)) {
        throw std::invalid_argument("Cannot sample an invalid FrameSequence.");
    }
    if (!(sample_dt > 0.0) || !std::isfinite(sample_dt)) {
        throw std::invalid_argument(
            "Analysis sample interval must be finite and positive.");
    }

    std::vector<FrameInfo> result;
    if (sequence.uniform) {
        const double ratio = sample_dt / sequence.dt;
        if (ratio > static_cast<double>(std::numeric_limits<int64_t>::max())) {
            throw std::invalid_argument(
                "Analysis sample interval is too large for the input timeline.");
        }
        const int64_t rounded = std::llround(ratio);
        if (rounded < 1 || !close(ratio, static_cast<double>(rounded))) {
            std::ostringstream message;
            message.precision(17);
            message << "Analysis sample interval " << sample_dt
                << " is not a positive integer multiple of input dt "
                << sequence.dt << ".";
            throw std::invalid_argument(message.str());
        }

        const size_t step = static_cast<size_t>(rounded);
        result.reserve(sequence.frames.size() / step + 2);
        for (size_t i = 0; i < sequence.frames.size(); i += step) {
            result.push_back(sequence.frames[i]);
        }
    }
    else {
        result.reserve(sequence.frames.size());
        result.push_back(sequence.first());
        double target = sequence.first().time + sample_dt;
        for (size_t i = 1; i + 1 < sequence.frames.size(); i++) {
            const FrameInfo& frame = sequence.frames[i];
            if (frame.time < target && !close(frame.time, target)) continue;
            result.push_back(frame);
            do {
                target += sample_dt;
            } while (std::isfinite(target) &&
                (target < frame.time || close(target, frame.time)));
            if (!std::isfinite(target)) break;
        }
    }
    if (result.back().index != sequence.last().index) {
        result.push_back(sequence.last());
    }
    return result;
}

std::vector<FrameInfo> sample_frames_by_step(
    const FrameSequence& sequence,
    size_t frame_step) {

    if (sequence.frames.empty()) {
        throw std::invalid_argument("Cannot sample an empty FrameSequence.");
    }
    if (frame_step == 0) {
        throw std::invalid_argument("Frame sample step must be positive.");
    }
    std::vector<FrameInfo> result;
    result.reserve(sequence.frames.size() / frame_step + 1);
    for (size_t index = 0; index < sequence.frames.size(); index += frame_step) {
        result.push_back(sequence.frames[index]);
    }
    return result;
}

std::vector<FrameInfo> select_frame_range(
    std::span<const FrameInfo> available,
    int frame_start,
    int frame_end) {

    if (available.empty()) {
        throw std::invalid_argument(
            "Cannot select output from an empty frame sequence.");
    }
    const int first = frame_start < 0 ? available.front().index : frame_start;
    const int last = frame_end < 0 ? available.back().index : frame_end;
    if (first > last) {
        throw std::invalid_argument(
            "Output frame start must not exceed output frame end.");
    }
    std::vector<FrameInfo> selected;
    for (const FrameInfo& frame : available) {
        if (frame.index >= first && frame.index <= last) {
            selected.push_back(frame);
        }
    }
    if (selected.empty() || selected.front().index != first ||
        selected.back().index != last) {
        throw std::invalid_argument(
            "Output frame range must lie inside the available sequence.");
    }
    return selected;
}

std::vector<FrameInfo> safe_base_frames(
    const FrameSequence& sequence,
    double window_left,
    double window_right) {

    if (sequence.frames.size() < 2 || !(sequence.dt > 0.0)) {
        throw std::invalid_argument(
            "Cannot select slow-light base frames from an invalid FrameSequence.");
    }
    if (!std::isfinite(window_left) || !std::isfinite(window_right) ||
        window_left > window_right) {
        throw std::invalid_argument(
            "Slow-light window endpoints must be finite and ordered.");
    }

    const double first_time = sequence.first().time;
    const double last_time = sequence.last().time;
    const double scale = std::max({
        1.0,
        std::abs(first_time),
        std::abs(last_time),
        std::abs(window_left),
        std::abs(window_right)
    });
    const double tolerance = relative_tolerance * scale;

    std::vector<FrameInfo> result;
    for (const FrameInfo& frame : sequence.frames) {
        if (frame.time + window_left >= first_time - tolerance &&
            frame.time + window_right <= last_time + tolerance) {
            result.push_back(frame);
        }
    }
    return result;
}

} // namespace fluid
