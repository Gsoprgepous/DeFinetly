use cxx::UniquePtr;
use serde::{Serialize, Deserialize};
use std::collections::HashMap;

/// C++ FFI мост
#[cxx::bridge]
mod ffi {
    // Экспортируемые в C++ типы
    #[derive(Debug, Serialize, Deserialize)]
    pub struct Tx {
        pub to: String,
        pub value: f64,
        pub gas_price: f64,
        pub input: Vec<u8>,
    }

    extern "C++" {
        include!("mev-detector/cpp/simulator.h");
        
        type CppSimulator;

        fn new_simulator() -> UniquePtr<CppSimulator>;
        fn simulate_profit(sim: &CppSimulator, victim: &Tx, attacker: &Tx) -> f64;
    }
}

/// Результат детекции MEV
#[derive(Serialize, Deserialize)]
pub struct MevAlert {
    pub alert_type: String,
    pub profit_eth: f64,
    pub risk_score: f8,
}

pub struct MevDetector {
    simulator: UniquePtr<ffi::CppSimulator>,
    pending_pool: HashMap<String, Vec<ffi::Tx>>, // Адрес -> Ожидающие транзы
}

impl MevDetector {
    pub fn new() -> Self {
        Self {
            simulator: ffi::new_simulator(),
            pending_pool: HashMap::new(),
        }
    }

    pub fn analyze(&mut self, tx: ffi::Tx) -> Option<MevAlert> {
        let target = tx.to.clone();

        if let Some(alert) = self.check_frontrun(&target, &tx) {
            return Some(alert);
        }

        self.pending_pool.entry(target).or_default().push(tx);
        None
    }

    /// Детекция фронтраннинга
    fn check_frontrun(&self, target: &str, new_tx: &ffi::Tx) -> Option<MevAlert> {
        self.pending_pool.get(target).and_then(|pending| {
            pending.iter().find_map(|existing| {
                if self.is_frontrun_candidate(existing, new_tx) {
                    let profit = ffi::simulate_profit(
                        &self.simulator,
                        existing,
                        new_tx
                    );
                    
                    if profit > 0.0 {
                        Some(MevAlert {
                            alert_type: "frontrun".into(),
                            profit_eth: profit,
                            risk_score: self.calculate_risk(profit),
                        })
                    } else {
                        None
                    }
                } else {
                    None
                }
            })
        })
    }

    fn is_frontrun_candidate(&self, existing: &ffi::Tx, new: &ffi::Tx) -> bool {
        // 1. Тот же целевой контракт
        existing.to == new.to &&
        // 2. Похожий input (вызов той же функции)
        existing.input == new.input &&
        // 3. Более высокий gas price (минимум +10%)
        new.gas_price > existing.gas_price * 1.1
    }

    /// Расчет риска (0.0 - 1.0)
    fn calculate_risk(&self, profit: f64) -> f8 {
        (profit / 10.0).min(1.0) // Нормализуем к 10 ETH
    }
}

#[no_mangle]
pub extern "C" fn mev_detector_new() -> *mut MevDetector {
    Box::into_raw(Box::new(MevDetector::new()))
}

#[no_mangle]
pub extern "C" fn mev_detector_analyze(
    detector: *mut MevDetector,
    tx_json: *const c_char,
) -> *mut c_char {
    let detector = unsafe { &mut *detector };
    let tx_str = unsafe { CStr::from_ptr(tx_json).to_str().unwrap() };
    let tx: ffi::Tx = serde_json::from_str(tx_str).unwrap();

    if let Some(alert) = detector.analyze(tx) {
        let alert_json = serde_json::to_string(&alert).unwrap();
        CString::new(alert_json).unwrap().into_raw()
    } else {
        ptr::null_mut()
    }
}
