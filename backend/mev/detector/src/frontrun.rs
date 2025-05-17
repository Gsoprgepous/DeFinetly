use ethers::types::{Transaction, H160};
use revm::db::CacheDB;
use serde::Serialize;

#[derive(Serialize)]
pub struct FrontrunAlert {
    pub victim_tx: String,
    pub profit_eth: f64,
    pub gas_used: u64,
}

pub struct FrontrunDetector {
    pending_pool: HashMap<H160, Vec<Transaction>>,
}

impl FrontrunDetector {
    pub fn new() -> Self {
        Self {
            pending_pool: HashMap::new(),
        }
    }

    pub fn analyze(&mut self, tx: &Transaction) -> Option<FrontrunAlert> {
        let target = tx.to?;
        
        if let Some(pending) = self.pending_pool.get(&target) {
            for victim in pending {
                if self.is_frontrun_candidate(victim, tx) {
                    let profit = self.simulate_frontrun(victim, tx);
                    if profit > 0.0 {
                        return Some(FrontrunAlert {
                            victim_tx: format!("0x{:x}", victim.hash),
                            profit_eth: profit,
                            gas_used: tx.gas.as_u64(),
                        });
                    }
                }
            }
        }

        self.pending_pool.entry(target).or_default().push(tx.clone());
        None
    }

    fn is_frontrun_candidate(&self, victim: &Transaction, attacker: &Transaction) -> bool {
        victim.input == attacker.input &&
        attacker.gas_price > victim.gas_price * 11 / 10 &&
        attacker.nonce > victim.nonce
    }

    fn simulate_frontrun(&self, victim: &Transaction, attacker: &Transaction) -> f64 {
        let mut db = CacheDB::default();
        let mut evm = revm::EVM::new();
        evm.database(db);

        evm.env.tx = victim.clone().into();
        let victim_result = evm.transact().unwrap();

        evm.env.tx = attacker.clone().into();
        let attacker_result = evm.transact().unwrap();

        (attacker_result.value - victim_result.value).as_u64() as f64 / 1e18
    }
}
