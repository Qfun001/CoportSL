#include "Timing.h"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <numeric>
#include <vector>

namespace benchmark {

namespace {

struct Stats {
    double mean = 0.0;
    double stdev = 0.0;
};

Stats summarize(const std::vector<double>& values) {
    if (values.empty()) return {};
    const double mean = std::accumulate(values.begin(), values.end(), 0.0) /
        static_cast<double>(values.size());
    if (values.size() == 1) return { mean, 0.0 };
    double variance = 0.0;
    for (double value : values) {
        const double delta = value - mean;
        variance += delta * delta;
    }
    variance /= static_cast<double>(values.size() - 1);
    return { mean, std::sqrt(variance) };
}

std::vector<double> measured_values(
    const std::vector<TimingRecord>& records,
    double TimingRecord::* member) {

    std::vector<double> values;
    for (const TimingRecord& record : records) {
        if (!record.warmup) values.push_back(record.*member);
    }
    return values;
}

} // namespace

double seconds(Clock::time_point begin, Clock::time_point end) {
    return std::chrono::duration<double>(end - begin).count();
}

void write_summary(
    const std::filesystem::path& file,
    const std::string& light,
    int npix,
    int cores,
    size_t grid_points,
    size_t grid_bytes,
    size_t frame_bytes,
    const std::vector<TimingRecord>& records) {

    const Stats update = summarize(measured_values(records, &TimingRecord::frame_update_s));
    const Stats transfer = summarize(measured_values(records, &TimingRecord::transfer_s));

    uint64_t samples = 0;
    if (!records.empty()) {
        samples = records.front().samples;
    }

    const bool write_header = !std::filesystem::exists(file);
    std::ofstream out(file, std::ios::app);
    if (write_header) {
        out << "light,npix,cores,grid_points,samples,grid_bytes,frame_bytes,"
            "frame_update_mean_s,frame_update_std_s,"
            "transfer_mean_s,transfer_std_s\n";
    }
    out << std::setprecision(17)
        << light << "," << npix << "," << cores << ","
        << grid_points << "," << samples << ","
        << grid_bytes << "," << frame_bytes << ","
        << update.mean << "," << update.stdev << ","
        << transfer.mean << "," << transfer.stdev << "\n";
}

} // namespace benchmark
