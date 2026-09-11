#include "NumberExpression.h"

#include <charconv>
#include <cmath>
#include <cstddef>
#include <numbers>
#include <stdexcept>
#include <string>

namespace runtime_config {
namespace {

class Parser {
public:
    explicit Parser(std::string_view source) : source_(source) {
        if (source_.empty()) {
            fail("expression is empty");
        }
        if (source_.size() > 128) {
            fail("expression is longer than 128 characters");
        }
    }

    double parse() {
        const double value = expression();
        space();
        if (position_ != source_.size()) {
            fail("unexpected character");
        }
        if (!std::isfinite(value)) {
            fail("result is not a finite real number");
        }
        return value;
    }

private:
    double expression() {
        double value = term();
        while (true) {
            space();
            if (take('+')) value += term();
            else if (take('-')) value -= term();
            else return finite(value);
        }
    }

    double term() {
        double value = unary();
        while (true) {
            space();
            if (take('*')) value *= unary();
            else if (take('/')) {
                const double divisor = unary();
                if (divisor == 0.0) fail("division by zero");
                value /= divisor;
            }
            else return finite(value);
        }
    }

    double unary() {
        space();
        if (take('+')) return unary();
        if (take('-')) return finite(-unary());
        return primary();
    }

    double primary() {
        space();
        if (take('(')) {
            if (++depth_ > 16) fail("parentheses are nested too deeply");
            const double value = expression();
            space();
            if (!take(')')) fail("missing closing parenthesis");
            depth_--;
            return value;
        }
        if (source_.substr(position_, 2) == "pi") {
            position_ += 2;
            return std::numbers::pi;
        }
        return number();
    }

    double number() {
        space();
        const char* begin = source_.data() + position_;
        const char* end = source_.data() + source_.size();
        double value = 0.0;
        const auto [next, error] = std::from_chars(
            begin, end, value, std::chars_format::general);
        if (error != std::errc{} || next == begin) {
            fail("expected a number, pi, or parenthesized expression");
        }
        position_ += static_cast<size_t>(next - begin);
        return finite(value);
    }

    bool take(char expected) {
        if (position_ < source_.size() && source_[position_] == expected) {
            position_++;
            return true;
        }
        return false;
    }

    void space() {
        while (position_ < source_.size()) {
            const char value = source_[position_];
            if (value != ' ' && value != '\t' && value != '\r' && value != '\n') {
                break;
            }
            position_++;
        }
    }

    double finite(double value) {
        if (!std::isfinite(value)) {
            fail("intermediate result is not finite");
        }
        return value;
    }

    [[noreturn]] void fail(const char* reason) const {
        throw std::invalid_argument(
            "Invalid number expression at position " +
            std::to_string(position_) + ": " + reason + ".");
    }

    std::string_view source_;
    size_t position_ = 0;
    size_t depth_ = 0;
};

} // namespace

double evaluate_number_expression(std::string_view expression) {
    return Parser(expression).parse();
}

} // namespace runtime_config
