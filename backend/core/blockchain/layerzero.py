import requests
from typing import Dict, List, Optional
from web3 import Web3
from tenacity import retry, stop_after_attempt

class LayerZeroBridge:
    """
    Мониторинг и анализ кросс-чейн транзакций через LayerZero.
    Поддерживаемые цепи: Ethereum, BSC, Avalanche, Polygon, Arbitrum.
    """
    
    def __init__(self, config: Dict):
        """
        :param config: {
            "ethereum": {"rpc": "https://eth.llamarpc.com", "chain_id": 101},
            "bsc": {"rpc": "https://bsc-dataseed.binance.org", "chain_id": 102},
            "layerzero_endpoint": "0x66A71Dcef29A0fFBDBE3c6a460a3B5BC225Cd675"
        }
        """
        self.chains = {
            "ethereum": Web3(Web3.HTTPProvider(config["ethereum"]["rpc"])),
            "bsc": Web3(Web3.HTTPProvider(config["bsc"]["rpc"]))
        }
        self.endpoint = config["layerzero_endpoint"]
        
    @retry(stop=stop_after_attempt(3))
    def get_message_fee(self, from_chain: str, to_chain: str) -> int:
        """
        Получает预估 gas fee для кросс-чейн транзакции.
        """
        endpoint_contract = self.chains[from_chain].eth.contract(
            address=self.endpoint,
            abi=self._load_endpoint_abi()
        )
        fee = endpoint_contract.functions.estimateFees(
            self.chains[to_chain]["chain_id"],
            "0x",  # Пример payload
            False,  # Оплата в нативном токене
            "0x"    # Адрес получателя (пусто для расчета)
        ).call()
        return fee

    def track_message(self, tx_hash: str, from_chain: str) -> Dict:
        """
        Отслеживает статус кросс-чейн сообщения.
        
        :return: {
            "src_chain": "ethereum",
            "dst_chain": "bsc",
            "status": "delivered" | "pending" | "failed",
            "dst_tx_hash": str | None
        }
        """
        tx_receipt = self.chains[from_chain].eth.get_transaction_receipt(tx_hash)
        logs = self._parse_layerzero_logs(tx_receipt.logs)
        
        if not logs:
            return {"status": "failed", "error": "No LayerZero events"}
            
        message = {
            "src_chain": from_chain,
            "dst_chain": self._chain_id_to_name(logs["dstChainId"]),
            "status": "pending"
        }
        
        # Проверяем доставку в целевой цепи
        dst_chain = self.chains[message["dst_chain"]]
        dst_tx_hash = self._find_destination_tx(dst_chain, logs["nonce"])
        if dst_tx_hash:
            message.update({"status": "delivered", "dst_tx_hash": dst_tx_hash})
        
        return message

    def _load_endpoint_abi(self) -> List[Dict]:
        """ABI контракта LayerZero Endpoint (основные функции)."""
        return [{
            "inputs": [
                {"name": "dstChainId", "type": "uint16"},
                {"name": "payload", "type": "bytes"},
                {"name": "payInZRO", "type": "bool"},
                {"name": "adapterParams", "type": "bytes"}
            ],
            "name": "estimateFees",
            "outputs": [{"name": "fee", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function"
        }]

    def _parse_layerzero_logs(self, logs: List) -> Optional[Dict]:
        """Парсит логи контракта на события Send/Receive."""
        for log in logs:
            if log.address == self.endpoint:
                return {
                    "dstChainId": int(log.topics[1].hex(), 16),
                    "nonce": int(log.topics[2].hex(), 16)
                }
        return None

    def _chain_id_to_name(self, chain_id: int) -> str:
        """Конвертирует LayerZero chain_id в имя цепи."""
        mapping = {
            101: "ethereum",
            102: "bsc",
            109: "avalanche",
            110: "polygon",
            110: "arbitrum"
        }
        return mapping.get(chain_id, "unknown")
