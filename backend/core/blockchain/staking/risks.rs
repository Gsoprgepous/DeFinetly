use ethers::types::{Address, U256};
use serde::Serialize;
use std::collections::HashMap;

/// Параметры риска для валидатора
#[derive(Debug, Serialize, Clone)]
pub struct RiskParams {
    pub slashing_risk: f64,       // 0.0-1.0
    pub liquidity_risk: f64,      // 0.0-1.0
    pub concentration_risk: f64,  // 0.0-1.0
}

#[derive(Debug, Clone)]
pub struct ValidatorData {
    pub total_staked: U256,
    pub restaked_assets: Vec<Address>,
    pub slash_history: u32,
    pub avg_uptime: f64,  // 0.0-1.0
}

/// Конфигурация модели рисков
pub struct RiskModelConfig {
    pub max_slashing_penalty: U256,
    pub min_uptime_threshold: f64,
}

impl Default for RiskModelConfig {
    fn default() -> Self {
        Self {
            max_slashing_penalty: U256::from(1_000_000_000_000_000_000u64), // 1 ETH
            min_uptime_threshold: 0.95,
        }
    }
}

/// Анализатор рисков EigenLayer
pub struct RiskAnalyzer {
    config: RiskModelConfig,
    asset_volatility: HashMap<Address, f64>,  // Волатильность активов
}

impl RiskAnalyzer {
    pub fn new(config: RiskModelConfig) -> Self {
        Self {
            config,
            asset_volatility: Self::load_volatility_data(),
        }
    }

    /// Основная функция оценки рисков
    pub fn calculate_risks(&self, validator: &ValidatorData) -> RiskParams {
        RiskParams {
            slashing_risk: self.calculate_slashing_risk(validator),
            liquidity_risk: self.calculate_liquidity_risk(validator),
            concentration_risk: self.calculate_concentration_risk(validator),
        }
    }

    /// Риск слэшинга (0.0-1.0)
    fn calculate_slashing_risk(&self, validator: &ValidatorData) -> f64 {
        let base_risk = if validator.slash_history > 0 {
            0.7 + (validator.slash_history as f64 * 0.1)
        } else {
            0.1
        };

        let uptime_penalty = if validator.avg_uptime < self.config.min_uptime_threshold {
            (self.config.min_uptime_threshold - validator.avg_uptime) * 2.0
        } else {
            0.0
        };

        (base_risk + uptime_penalty).min(1.0)
    }

    /// Риск ликвидности (0.0-1.0)
    fn calculate_liquidity_risk(&self, validator: &ValidatorData) -> f64 {
        if validator.restaked_assets.is_empty() {
            return 0.0;
        }

        let total_value = self.estimate_portfolio_value(validator);
        let eth_value = validator.total_staked.as_u64() as f64 / 1e18;

        if total_value == 0.0 {
            return 0.0;
        }

        // Чем выше доля ETH, тем ниже риск
        1.0 - (eth_value / total_value).min(1.0)
    }

    /// Риск концентрации (0.0-1.0)
    fn calculate_concentration_risk(&self, validator: &ValidatorData) -> f64 {
        if validator.restaked_assets.len() <= 1 {
            return 0.0;
        }

        let mut unique_assets = std::collections::HashSet::new();
        let mut total_volatility = 0.0;

        for asset in &validator.restaked_assets {
            unique_assets.insert(asset);
            total_volatility += self.asset_volatility.get(asset).unwrap_or(&0.5);
        }

        let avg_volatility = total_volatility / validator.restaked_assets.len() as f64;
        let diversity_factor = 1.0 - (unique_assets.len() as f64 / validator.restaked_assets.len() as f64);

        (avg_volatility * 0.7 + diversity_factor * 0.3).min(1.0)
    }

    /// Загрузка данных о волатильности 
    fn load_volatility_data() -> HashMap<Address, f64> {
        let mut data = HashMap::new();
        data.insert(Address::zero(), 0.5); // Пример для тестов
        data
    }

    /// Оценка стоимости портфеля (очень очень упрощенная)
    fn estimate_portfolio_value(&self, validator: &ValidatorData) -> f64 {
        validator.restaked_assets.len() as f64 * 1000.0 // Заглушка
    }
}

/// Тесты модуля
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_slashing_risk() {
        let analyzer = RiskAnalyzer::new(RiskModelConfig::default());
        let validator = ValidatorData {
            total_staked: U256::from(10u64.pow(18)), // 1 ETH
            restaked_assets: vec![],
            slash_history: 0,
            avg_uptime: 0.99,
        };

        let risks = analyzer.calculate_risks(&validator);
        assert!(risks.slashing_risk < 0.2);
    }
}
