#pragma once
#include <nlohmann/json.hpp>
#include <vector>
#include <functional>
#include <cpprest/ws_client.h>

using json = nlohmann::json;
using AlertHandler = std::function<void(const json& alert)>;

class AlertManager {
public:
    AlertManager(const std::string& config_path);
    
    void subscribe(const std::string& alert_type, AlertHandler handler);
    void startMonitoring();
    
private:
    void loadRules();
    void watchWebSocket();

    std::unordered_map<std::string, std::vector<AlertHandler>> handlers;
    std::vector<json> rules;
    web::websockets::client::websocket_callback_client ws_client;
};
