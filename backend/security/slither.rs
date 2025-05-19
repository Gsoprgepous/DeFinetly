use std::process::Command;
use serde_json::Value;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum SlitherError {
    #[error("Slither execution failed: {0}")]
    ExecutionError(String),
    #[error("JSON parsing error: {0}")]
    ParseError(#[from] serde_json::Error),
}

/// Анализ контракта через Slither
pub fn analyze_contract(contract_path: &str, solc_version: &str) -> Result<Value, SlitherError> {
    let output = Command::new("solc-select")
        .args(["install", solc_version])
        .output()
        .map_err(|e| SlitherError::ExecutionError(e.to_string()))?;

    if !output.status.success() {
        return Err(SlitherError::ExecutionError(
            String::from_utf8_lossy(&output.stderr).into_owned(),
        ));
    }

    let slither_output = Command::new("slither")
        .args([contract_path, "--json", "-"])
        .output()
        .map_err(|e| SlitherError::ExecutionError(e.to_string()))?;

    let report: Value = serde_json::from_slice(&slither_output.stdout)?;
    Ok(report)
}

/// Расчёт security score
pub fn calculate_security_score(report: &Value) -> f64 {
    let detectors = report["results"]["detectors"].as_array().unwrap_or(&vec![]);
    let mut score = 1.0;

    for det in detectors {
        let impact = det["impact"].as_str().unwrap_or("Low");
        score -= match impact {
            "High" => 0.3,
            "Medium" => 0.1,
            _ => 0.0,
        };
    }

    score.max(0.0)
}
