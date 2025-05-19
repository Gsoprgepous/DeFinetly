#pragma once
#include <string>
#include <vector>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

namespace Ethereum {

struct Transaction {
    std::string hash;
    std::string from;
    std::string to;
    uint64_t value;
    uint64_t gas;
};

class Client {
public:
    Client(const std::string& node_url);
    
    // Основные методы
    std::string get_code(const std::string& address);
    Transaction get_transaction(const std::string& tx_hash);
    json call_rpc(const std::string& method, const json& params);
    
    // Утилиты
    static bool is_valid_address(const std::string& address);

private:
    std::string node_url_;
    size_t timeout_sec_ = 5;
};

} // namespace Ethereum
