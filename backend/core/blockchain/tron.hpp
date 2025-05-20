#pragma once
#include <string>
#include <vector>
#include <memory>
#include "crypto/base58.hpp"  
#include "utils/hex.hpp"      // Утилиты для hex-конвертации
#include <nlohmann/json.hpp>  // JSON-парсинг

namespace Tron {

// Конфигурация ноды (можно переопределить)
struct NodeConfig {
    std::string rpc_url = "https://api.trongrid.io/jsonrpc";
    uint32_t timeout_ms = 5000;  // Таймаут запросов
};

// Транзакция в Tron (упрощенная модель)
struct Transaction {
    std::string tx_id;          // Хэш транзакции
    std::string from;           // Отправитель (Base58)
    std::string to;             // Получатель (Base58)
    int64_t amount_sun;         // Сумма в SUN (1 TRX = 1_000_000 SUN)
    int64_t fee_sun;            // Комиссия
    std::string contract_data;  // Данные вызова контракта 
};

// Класс для работы с блокчейном Tron
class NodeClient {
public:
    explicit NodeClient(const NodeConfig& config = {});
    
    // Основные методы
    Transaction get_transaction(const std::string& tx_hash);
    std::string call_contract(const std::string& contract_address, const std::string& data);
    
    // Утилиты
    static bool validate_address(const std::string& address);

private:
    std::string post_rpc(const std::string& method, const nlohmann::json& params);
    NodeConfig config_;
};

} // namespace Tron

#include "tron.hpp"
#include <curl/curl.h>
#include <openssl/sha256.h>
#include <stdexcept>

namespace Tron {

NodeClient::NodeClient(const NodeConfig& config) : config_(config) {}

// RPC-запрос к Tron-ноде
std::string NodeClient::post_rpc(const std::string& method, const nlohmann::json& params) {
    CURL* curl = curl_easy_init();
    std::string response;
    nlohmann::json payload = {
        {"jsonrpc", "2.0"},
        {"method", method},
        {"params", params},
        {"id", 1}
    };

    if (curl) {
        curl_easy_setopt(curl, CURLOPT_URL, config_.rpc_url.c_str());
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, payload.dump().c_str());
        curl_easy_setopt(curl, CURLOPT_TIMEOUT_MS, config_.timeout_ms);
        // ... настройка headers и callback
        
        CURLcode res = curl_easy_perform(curl);
        if (res != CURLE_OK) {
            curl_easy_cleanup(curl);
            throw std::runtime_error("RPC request failed: " + std::string(curl_easy_strerror(res)));
        }
        curl_easy_cleanup(curl);
    }
    return response;
}

// Получение транзакции по хэшу
Transaction NodeClient::get_transaction(const std::string& tx_hash) {
    auto response = nlohmann::json::parse(post_rpc("eth_getTransactionByHash", {{"hash", tx_hash}}));
    
    if (response["error"].is_object()) {
        throw std::runtime_error("Tron RPC error: " + response["error"]["message"].get<std::string>());
    }

    const auto& result = response["result"];
    return Transaction{
        .tx_id = tx_hash,
        .from = Base58::encode_check(Hex::to_bytes(result["from"].get<std::string>())),
        .to = Base58::encode_check(Hex::to_bytes(result["to"].get<std::string>())),
        .amount_sun = std::stoll(result["value"].get<std::string>(), nullptr, 16),
        .fee_sun = std::stoll(result["fee"].get<std::string>(), nullptr, 16),
        .contract_data = result["input"].get<std::string>()
    };
}

// Валидация Tron-адреса
bool NodeClient::validate_address(const std::string& address) {
    try {
        auto decoded = Base58::decode_check(address);
        return decoded.size() == 21 && decoded[0] == 0x41;  // 0x41 — префикс Tron
    } catch (...) {
        return false;
    }
}

} // namespace Tron
