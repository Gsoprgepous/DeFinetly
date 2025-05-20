use ethers::{
    core::types::{TransactionRequest, Eip1559TransactionRequest},
    prelude::*,
    providers::{Middleware, Provider, Http},
    signers::{LocalWallet, Signer},
    utils::{format_units, parse_units},
};
use serde::Serialize;
use std::sync::Arc;
use thiserror::Error;

/// Конфигурация рестейкинга
#[derive(Clone)]
pub struct RestakingConfig {
    pub eigen_contract: Address,
    pub gas_limit: u64,
    pub max_priority_fee_per_gas: f64, // В Gwei
    pub max_fee_per_gas: f64,          // В Gwei
}

/// Ошибки модуля
#[derive(Debug, Error)]
pub enum RestakingError {
    #[error("Provider error: {0}")]
    ProviderError(#[from] ProviderError),
    
    #[error("Signing error: {0}")]
    SigningError(String),
    
    #[error("Invalid amount: {0}")]
    InvalidAmount(String),
    
    #[error("Transaction failed: {0}")]
    TransactionFailed(H256),
}

/// Результат рестейкинга
#[derive(Debug, Serialize)]
pub struct RestakingResult {
    pub tx_hash: H256,
    pub gas_used: u64,
    pub effective_gas_price: U256,
}

/// Основной клиент рестейкинга
pub struct RestakingClient<M> {
    provider: Arc<M>,
    config: RestakingConfig,
}

impl<M: Middleware> RestakingClient<M> {
    pub fn new(provider: Arc<M>, config: RestakingConfig) -> Self {
        Self { provider, config }
    }

    /// Выполняет рестейкинг ETH в EigenLayer
    pub async fn restake_eth(
        &self,
        wallet: LocalWallet,
        validator: Address,
        amount_eth: f64,
    ) -> Result<RestakingResult, RestakingError> {
        // 1. Конвертация ETH в Wei
        let amount = parse_units(amount_eth, "ether")
            .map_err(|_| RestakingError::InvalidAmount("Failed to parse ETH amount".into()))?;

        // 2. Формирование EIP-1559 транзакции
        let tx = Eip1559TransactionRequest::new()
            .to(self.config.eigen_contract)
            .chain_id(self.provider.get_chainid().await?.as_u64())
            .data(self.encode_restake_call(validator, amount))
            .gas(self.config.gas_limit)
            .max_priority_fee_per_gas(
                parse_units(self.config.max_priority_fee_per_gas, "gwei")?.into(),
            )
            .max_fee_per_gas(
                parse_units(self.config.max_fee_per_gas, "gwei")?.into(),
            );

        // 3. Подпись и отправка
        let signed_tx = wallet
            .sign_transaction(&tx)
            .await
            .map_err(|e| RestakingError::SigningError(e.to_string()))?;

        let pending_tx = self.provider.send_raw_transaction(signed_tx).await?;

        // 4. Ожидание подтверждения
        let receipt = pending_tx
            .await?
            .ok_or(RestakingError::TransactionFailed(pending_tx.tx_hash()))?;

        Ok(RestakingResult {
            tx_hash: receipt.transaction_hash,
            gas_used: receipt.gas_used.unwrap_or_default().as_u64(),
            effective_gas_price: receipt.effective_gas_price.unwrap_or_default(),
        })
    }

    /// Кодирует вызов метода `restake` в ABI
    fn encode_restake_call(&self, validator: Address, amount: U256) -> Bytes {
        use ethers::abi::AbiEncode;
        
        // Сигнатура: restake(address validator, uint256 amount)
        let mut data = vec![0x12, 0x34, 0x56, 0x78]; // Заглушка для примера
        data.extend(validator.encode());
        data.extend(amount.encode());
        Bytes::from(data)
    }
}

/// FFI-интерфейс для Python
#[cfg(feature = "ffi")]
pub mod ffi {
    use super::*;
    use pyo3::prelude::*;

    #[pyfunction]
    fn restake_eth(
        rpc_url: String,
        contract_addr: String,
        priv_key: String,
        validator_addr: String,
        amount_eth: f64,
    ) -> PyResult<String> {
        let provider = Provider::<Http>::try_from(rpc_url)?;
        let wallet = priv_key.parse::<LocalWallet>()?;
        let config = RestakingConfig {
            eigen_contract: contract_addr.parse()?,
            gas_limit: 300_000,
            max_priority_fee_per_gas: 2.0,
            max_fee_per_gas: 150.0,
        };

        let client = RestakingClient::new(Arc::new(provider), config);
        let result = tokio::runtime::Runtime::new()?
            .block_on(client.restake_eth(
                wallet,
                validator_addr.parse()?,
                amount_eth,
            ))?;

        Ok(serde_json::to_string(&result)?)
    }
}
