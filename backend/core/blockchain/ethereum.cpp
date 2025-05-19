#include "ethereum.hpp"
#include <curl/curl.h>
#include <iostream>
#include <regex>

namespace Ethereum {

// Callback для CURL
static size_t WriteCallback(void* contents, size_t size, size_t nmemb, std::string* output) {
    size_t total_size = size * nmemb;
    output->append((char*)contents, total_size);
    return total_size;
}

Client::Client(const std::string& node_url) : node_url_(node_url) {}

json Client::call_rpc(const std::string& method, const json& params) {
    CURL* curl = curl_easy_init();
    std::string response;

    json payload = {
        {"jsonrpc", "2.0"},
        {"method", method},
        {"params", params},
        {"id", 1}
    };

    if (curl) {
        struct curl_slist* headers = nullptr;
        headers = curl_slist_append(headers, "Content-Type: application/json");
        
        curl_easy_setopt(curl, CURLOPT_URL, node_url_.c_str());
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, payload.dump().c_str());
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, timeout_sec_);
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);

        CURLcode res = curl_easy_perform(curl);
        if (res != CURLE_OK) {
            throw std::runtime_error("CURL error: " + std::string(curl_easy_strerror(res)));
        }
        curl_easy_cleanup(curl);
    }

    return json::parse(response);
}

std::string Client::get_code(const std::string& address) {
    if (!is_valid_address(address)) {
        throw std::invalid_argument("Invalid Ethereum address");
    }

    json response = call_rpc("eth_getCode", {address, "latest"});
    return response["result"].get<std::string>();
}

Transaction Client::get_transaction(const std::string& tx_hash) {
    json response = call_rpc("eth_getTransactionByHash", {tx_hash});
    
    if (response["result"].is_null()) {
        throw std::runtime_error("Transaction not found");
    }

    return Transaction{
        .hash = tx_hash,
        .from = response["result"]["from"],
        .to = response["result"]["to"],
        .value = std::stoull(response["result"]["value"].get<std::string>(), nullptr, 16),
        .gas = std::stoull(response["result"]["gas"].get<std::string>(), nullptr, 16)
    };
}

bool Client::is_valid_address(const std::string& address) {
    std::regex eth_addr_regex("^0x[a-fA-F0-9]{40}$");
    return std::regex_match(address, eth_addr_regex);
}

} // namespace Ethereum
