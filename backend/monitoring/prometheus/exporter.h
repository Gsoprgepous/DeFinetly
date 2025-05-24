#pragma once
#include <prometheus/registry.h>
#include <prometheus/counter.h>
#include <prometheus/gauge.h>
#include <atomic>
#include <memory>

class PrometheusExporter {
public:
    PrometheusExporter(const std::string& listen_address);
    
    // Метрики блокчейна
    void incrementBlockCounter(const std::string& chain);
    void setGasPriceGauge(const std::string& chain, double price);
    void setValidatorHealth(const std::string& validator, double health);

    void startServer();

private:
    std::shared_ptr<prometheus::Registry> registry;
    std::unique_ptr<prometheus::Exposer> exposer;
    
    // Метрики
    prometheus::Family<prometheus::Counter>& block_counter;
    prometheus::Family<prometheus::Gauge>& gas_price_gauge;
    prometheus::Family<prometheus::Gauge>& health_gauge;
};
