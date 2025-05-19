#pragma once
#include <vector>
#include <string>
#include <nlohmann/json.hpp>

namespace Ethereum {
struct ABIFunction {
    std::string name;
    std::vector<std::string> inputs;
    bool is_payable;
};

class ABI {
public:
    static std::vector<ABIFunction> parse(const std::string& json_abi);
};
} // namespace Ethereum
