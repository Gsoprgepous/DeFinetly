#include "exporter.h"
#include <chrono>
#include <thread>

PrometheusExporter::PrometheusExporter(const std::string& listen_address) 
    : registry(std::make_shared<prometheus::Registry>()),
      exposer(std::make_unique<prometheus::Exposer>(listen_address)),
      block_counter(prometheus::BuildCounter()
          .Name("blockchain_blocks_total")
          .Help("Total mined blocks")
          .Register(*registry)),
      gas_price_gauge(prometheus::BuildGauge()
          .Name("blockchain_gas_price")
          .Help("Current gas price in Gwei")
          .Register(*registry)),
      health_gauge(prometheus::BuildGauge()
          .Name("validator_health_score")
          .Help("Validator health (0-1)")
          .Register(*registry)) {
    
    exposer->RegisterCollectable(registry);
}

void PrometheusExporter::incrementBlockCounter(const std::string& chain) {
    block_counter.Add({{"chain", chain}}).Increment();
}

void PrometheusExporter::setGasPriceGauge(const std::string& chain, double price) {
    gas_price_gauge.Add({{"chain", chain}}).Set(price);
}

void PrometheusExporter::startServer() {
    while (true) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }
}
