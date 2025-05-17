use crate::ffi::{Tx, CppSimulator};
use serde::{Serialize, Deserialize};
use std::collections::{HashMap, VecDeque};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Serialize, Deserialize, PartialEq)]
pub enum MevType {
    Frontrun,
    Sandwich,
    Arbitrage,
    Liquidation,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct MevAlert {
    pub mev_type: MevType,
    pub profit_eth: f64,
    pub risk_score: f8,
    pub timestamp: u64,
    pub metadata: serde_json::Value,
}

/// Пул ожидающих транзакций с TTL
struct PendingPool {
    txs: HashMap<String, VecDeque<(Tx, u64)>>, // address -> (tx, timestamp)
    ttl_seconds: u64,
}

impl PendingPool {
    fn new(ttl: u64) -> Self {
        Self {
            txs: HashMap::new(),
            ttl_seconds: ttl,
        }
    }

    /// Добавляет транзакцию в пул 
    fn push(&mut self, tx: Tx) {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();
        
        self.txs
            .entry(tx.to.clone())
            .or_default()
            .push_back((tx, timestamp));
        
        self.cleanup();
    }

    fn cleanup(&mut self) {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();

        for (_, txs) in self.txs.iter_mut() {
            while let Some((_, ts)) = txs.front() {
                if now - ts > self.ttl_seconds {
                    txs.pop_front();
                } else {
                    break;
                }
            }
        }
    }
}

/// Основной детектор MEV
pub struct MevDetector {
    simulator: UniquePtr<CppSimulator>,
    pending_pool: PendingPool,
    thresholds: MevThresholds,
}

#[derive(Debug)]
struct MevThresholds {
    min_profit_eth: f64,
    max_gas_price_gwei: f64,
}

impl MevDetector {
    pub fn new(
        simulator: UniquePtr<CppSimulator>,
        ttl_seconds: u64,
        thresholds: MevThresholds,
    ) -> Self {
        Self {
            simulator,
            pending_pool: PendingPool::new(ttl_seconds),
            thresholds,
        }
    }

    /// Анализирует транзакцию на все типы MEV
    pub fn analyze(&mut self, tx: Tx) -> Vec<MevAlert> {
        let mut alerts = Vec::new();

        if let Some(alert) = self.detect_frontrun(&tx) {
            alerts.push(alert);
        }

        alerts.extend(self.detect_sandwich(&tx));

        self.pending_pool.push(tx);

        alerts
    }

    fn detect_frontrun(&self, new_tx: &Tx) -> Option<MevAlert> {
        self.pending_pool.txs.get(&new_tx.to).and_then(|pending| {
            pending.iter().find_map(|(existing, _)| {
                if self.is_frontrun_candidate(existing, new_tx) {
                    let profit = unsafe {
                        ffi::simulate_profit(&self.simulator, existing, new_tx)
                    };

                    if profit >= self.thresholds.min_profit_eth {
                        Some(self.build_alert(
                            MevType::Frontrun,
                            profit,
                            json!({
                                "victim_tx": existing,
                                "attacker_tx": new_tx
                            }),
                        ))
                    } else {
                        None
                    }
                } else {
                    None
                }
            })
        })
    }

    fn detect_sandwich(&self, new_tx: &Tx) -> Vec<MevAlert> {
        let mut alerts = Vec::new();

        if let Some(pending) = self.pending_pool.txs.get(&new_tx.to) {
            for (i, (tx1, _)) in pending.iter().enumerate() {
                for (tx2, _) in pending.iter().skip(i + 1) {
                    if self.is_sandwich_candidate(tx1, new_tx, tx2) {
                        let profit = unsafe {
                            ffi::simulate_sandwich(
                                &self.simulator,
                                tx1,
                                new_tx,
                                tx2
                            )
                        };

                        if profit >= self.thresholds.min_profit_eth {
                            alerts.push(self.build_alert(
                                MevType::Sandwich,
                                profit,
                                json!({
                                    "tx1": tx1,
                                    "tx2": tx2,
                                    "target": new_tx
                                }),
                            ));
                        }
                    }
                }
            }
        }

        alerts
    }

    fn is_frontrun_candidate(&self, existing: &Tx, new: &Tx) -> bool {
        existing.input == new.input &&
        new.gas_price > existing.gas_price * 1.1 &&
        new.gas_price <= self.thresholds.max_gas_price_gwei * 1e9
    }

    fn is_sandwich_candidate(&self, tx1: &Tx, tx2: &Tx, tx3: &Tx) -> bool {
        tx1.input == tx3.input &&
        tx2.input.len() >= 4 && 
        tx1.gas_price < tx2.gas_price &&
        tx3.gas_price > tx2.gas_price
    }

    fn build_alert(&self, mev_type: MevType, profit: f64, metadata: serde_json::Value) -> MevAlert {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();

        MevAlert {
            mev_type,
            profit_eth: profit,
            risk_score: self.calculate_risk(profit),
            timestamp,
            metadata,
        }
    }

    fn calculate_risk(&self, profit: f64) -> f8 {
        (profit.log10() / 2.0).clamp(0.0, 1.0) 
    }
}
