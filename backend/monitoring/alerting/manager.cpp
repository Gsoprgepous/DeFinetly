#include "manager.h"
#include <fstream>

AlertManager::AlertManager(const std::string& config_path) {
    loadRules();
}

void AlertManager::subscribe(const std::string& alert_type, AlertHandler handler) {
    handlers[alert_type].push_back(handler);
}

void AlertManager::loadRules() {
    std::ifstream f("monitoring/alerting/rules/slashing.json");
    rules.push_back(json::parse(f));
}

void AlertManager::startMonitoring() {
    ws_client.connect(U("wss://alerts.example.com")).then([this]() {
        ws_client.set_message_handler([this](const web::websockets::client::websocket_incoming_message& msg) {
            auto alert = json::parse(msg.extract_string().get());
            for (const auto& handler : handlers[alert["type"]]) {
                handler(alert);
            }
        });
    });
}
