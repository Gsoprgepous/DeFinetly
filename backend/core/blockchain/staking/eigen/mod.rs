pub mod validator;
pub mod restaking;
pub mod risks;

use ethers::types::{Address, U256};
use serde::{Serialize, Deserialize};

/// Конфигурация EigenLayer
#[derive(Clone, Serialize, Deserialize)]
pub struct EigenConfig {
    pub eth_rpc_url: String,
    pub eigen_contract: Address,
    pub chain_id: u64,
}

/// Статус рестейкинга
#[derive(Debug, Serialize)]
pub enum RestakingStatus {
    Active,
    Paused,
    Slashed,
}

/// Информация о валидаторе
#[derive(Serialize)]
pub struct ValidatorInfo {
    pub address: Address,
    pub staked_eth: U256,
    pub restaked_assets: Vec<Address>,
    pub status: RestakingStatus,
}
