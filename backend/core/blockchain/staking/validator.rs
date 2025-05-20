use super::{EigenConfig, ValidatorInfo, RestakingStatus};
use ethers::{providers::Provider, contract::Contract};
use std::sync::Arc;

pub struct ValidatorManager {
    provider: Arc<Provider<Http>>,
    config: EigenConfig,
}

impl ValidatorManager {
    pub fn new(config: EigenConfig) -> Self {
        let provider = Provider::<Http>::try_from(config.eth_rpc_url.clone())
            .expect("Failed to connect to ETH RPC");
        Self {
            provider: Arc::new(provider),
            config,
        }
    }

    /// Получает данные валидатора
    pub async fn get_validator(&self, address: Address) -> Result<ValidatorInfo, String> {
        let contract = self.load_eigen_contract().await?;
        
        let staked_eth = contract
            .method::<_, U256>("getStakedETH", address)?
            .call()
            .await?;

        let status_code: u8 = contract
            .method::<_, u8>("getValidatorStatus", address)?
            .call()
            .await?;

        Ok(ValidatorInfo {
            address,
            staked_eth,
            restaked_assets: self.get_restaked_assets(address).await?,
            status: match status_code {
                0 => RestakingStatus::Active,
                1 => RestakingStatus::Paused,
                _ => RestakingStatus::Slashed,
            },
        })
    }
}
