use ethers::types::Address;
use revm::Inspector;
use serde::Serialize;

#[derive(Debug, Serialize)]
pub struct ZkAuditReport {
    pub zk_type: String,
    pub risky_ops: Vec<String>,
    pub math_checks: MathChecks,
    pub security_score: f64,
}

#[derive(Debug, Serialize)]
pub struct MathChecks {
    pub curve_type: String,
    pub overflow_protected: bool,
}

/// Проверка контракта на zk-сигнатуры
pub fn is_zk_contract(code: &[u8]) -> bool {
    let zk_signatures = [
        "verifyProof".as_bytes(),
        "pairing(".as_bytes(),
        "bn254.".as_bytes(),
    ];

    zk_signatures.iter().any(|sig| code.windows(sig.len()).any(|w| w == *sig))
}

/// Полный аудит zk-контракта
pub fn audit_zk_contract(address: Address, code: Vec<u8>) -> ZkAuditReport {
    let mut report = ZkAuditReport {
        zk_type: detect_zk_type(&code),
        risky_ops: find_risky_operations(&code),
        math_checks: check_math(&code),
        security_score: 1.0,
    };

    // Корректировка security score
    report.security_score -= report.risky_ops.len() as f64 * 0.1;
    if !report.math_checks.overflow_protected {
        report.security_score -= 0.2;
    }

    report.security_score = report.security_score.max(0.0);
    report
}

// Детекция типа zk-контракта
fn detect_zk_type(code: &[u8]) -> String {
    if code.contains("verifyProof".as_bytes()) {
        "SNARK (Groth16)".to_string()
    } else if code.contains("stark_proof".as_bytes()) {
        "STARK".to_string()
    } else {
        "Unknown zk".to_string()
    }
}
