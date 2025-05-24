#include "blockchain_healthcheck.h"
#include <chrono>
#include <ethereum/client.h>
#include <libweb3jsonrpc/AccountHolder.h>
#include <boost/algorithm/string.hpp>
#include <range/v3/view.hpp>

namespace fs = std::filesystem;
using namespace std::chrono_literals;
using namespace ranges;

// Конфигурация по умолчанию
constexpr auto HEALTHCHECK_INTERVAL = 15s;
constexpr auto MAX_BLOCK_LAG = 50;
constexpr auto RPC_TIMEOUT = 5s;

BlockchainHealthCheck::BlockchainHealthCheck(
    EthereumClient& client,
    const fs::path& config_path
) : client_(client), config_(loadConfig(config_path)) {
    initMetrics();
    startBackgroundChecker();
}

HealthReport BlockchainHealthCheck::runFullCheck() {
    HealthReport report;
    report.timestamp = std::chrono::system_clock::now();
    
    // 1. Проверка синхронизации блоков
    auto [localBlock, networkBlock] = checkBlockSync();
    report.metrics["block_diff"] = networkBlock - localBlock;
    
    // 2. Проверка подключения к пирам
    auto peerStats = checkPeerConnections();
    report.metrics["active_peers"] = peerStats.active;
    
    // 3. Проверка RPC-методов
    auto rpcStatus = checkRpcAvailability();
    report.metrics["rpc_errors"] = rpcStatus.error_count;
    
    // 4. Проверка дискового пространства
    auto diskStatus = checkDiskSpace();
    report.metrics["disk_free_gb"] = diskStatus.free_gb;
    
    // Агрегация статуса
    report.overall_ok = !(localBlock == 0 || 
                         peerStats.active < config_.min_peers ||
                         diskStatus.critical);
    
    return report;
}

BlockSyncResult BlockchainHealthCheck::checkBlockSync() {
    try {
        auto localBlock = client_.eth_blockNumber();
        auto networkBlock = fetchNetworkBlock();
        
        prom_metrics_.block_diff->Set(networkBlock - localBlock);
        
        if (networkBlock - localBlock > MAX_BLOCK_LAG) {
            alerts_.emit(Alert{
                .type = "block_sync_lag",
                .severity = AlertSeverity::Warning,
                .details = {
                    {"local", localBlock},
                    {"network", networkBlock}
                }
            });
        }
        
        return {localBlock, networkBlock};
    } catch (const std::exception& e) {
        prom_metrics_.health_status->Set(0);
        throw HealthCheckError("Block sync check failed: " + std::string(e.what()));
    }
}

PeerStats BlockchainHealthCheck::checkPeerConnections() {
    auto peers = client_.admin_peers();
    PeerStats stats{
        .total = peers.size(),
        .active = count_if(peers, [](const PeerInfo& p) {
            return p.isActive && 
                   p.protocolVersion == ETH_PROTOCOL_VERSION;
        })
    };
    
    prom_metrics_.peer_count->Set(stats.active);
    
    if (stats.active < config_.min_peers) {
        alerts_.emit(Alert{
            .type = "low_peer_count",
            .severity = AlertSeverity::Critical,
            .details = {{"count", stats.active}}
        });
    }
    
    return stats;
}

RpcStatus BlockchainHealthCheck::checkRpcAvailability() {
    const vector<string> methods = {
        "eth_blockNumber", 
        "eth_getBalance",
        "net_version"
    };
    
    RpcStatus status;
    auto executor = client_.getExecutor();
    
    for (const auto& method : methods) {
        try {
            Json::Value request;
            request["jsonrpc"] = "2.0";
            request["method"] = method;
            request["id"] = 1;
            
            auto response = executor->execute(
                request, 
                RPC_TIMEOUT
            );
            
            if (response["error"].isObject()) {
                status.error_count++;
            }
        } catch (...) {
            status.error_count++;
        }
    }
    
    prom_metrics_.rpc_errors->Set(status.error_count);
    return status;
}

DiskSpaceStatus BlockchainHealthCheck::checkDiskSpace() {
    fs::space_info chaindata = fs::space(config_.chaindata_path);
    double free_gb = static_cast<double>(chaindata.free) / (1 << 30);
    
    prom_metrics_.disk_space->Set(free_gb);
    
    DiskSpaceStatus status{
        .free_gb = free_gb,
        .critical = free_gb < config_.min_disk_gb
    };
    
    if (status.critical) {
        alerts_.emit(Alert{
            .type = "low_disk_space",
            .severity = AlertSeverity::Critical,
            .details = {{"free_gb", free_gb}}
        });
    }
    
    return status;
}

void BlockchainHealthCheck::startBackgroundChecker() {
    checker_thread_ = std::thread([this]() {
        while (!shutdown_flag_.load()) {
            auto report = runFullCheck();
            last_report_ = report;
            
            if (!report.overall_ok) {
                handleCriticalStatus(report);
            }
            
            std::this_thread::sleep_for(HEALTHCHECK_INTERVAL);
        }
    });
}

void BlockchainHealthCheck::handleCriticalStatus(const HealthReport& report) {
    // 1. Эскалация через AlertManager
    alerts_.emit(Alert{
        .type = "node_unhealthy",
        .severity = AlertSeverity::Critical,
        .details = {
            {"block_diff", report.metrics.at("block_diff")},
            {"rpc_errors", report.metrics.at("rpc_errors")}
        }
    });
    
    // 2. Ротация логов при нехватке места
    if (report.metrics.at("disk_free_gb") < 5.0) {
        rotateLogs();
    }
    
    // 3. Переподключение к пирам
    if (report.metrics.at("active_peers") < 3) {
        client_.admin_addPeer(config_.bootstrap_nodes);
    }
}

Config BlockchainHealthCheck::loadConfig(const fs::path& path) {
    // Парсинг YAML/JSON конфига
    Config config;
    
    try {
        auto config_file = YAML::LoadFile(path);
        config.min_peers = config_file["min_peers"].as<int>();
        config.min_disk_gb = config_file["min_disk_gb"].as<double>();
        config.chaindata_path = config_file["chaindata_path"].as<string>();
        
        for (const auto& node : config_file["bootstrap_nodes"]) {
            config.bootstrap_nodes.push_back(node.as<string>());
        }
    } catch (const std::exception& e) {
        throw ConfigError("Failed to load config: " + std::string(e.what()));
    }
    
    return config;
}

void BlockchainHealthCheck::initMetrics() {
    auto& registry = prometheus::Registry::Default();
    
    prom_metrics_.health_status = &prometheus::BuildGauge()
        .Name("node_health_status")
        .Help("Overall node health (1=healthy)")
        .Register(registry)
        .Add({});
    
    prom_metrics_.block_diff = &prometheus::BuildGauge()
        .Name("block_sync_diff")
        .Help("Blocks behind network")
        .Register(registry)
        .Add({});
    
    // ... инициализация остальных метрик
}
