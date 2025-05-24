from abc import ABC, abstractmethod
from web3 import Web3

class BaseProtocol(ABC):
    def __init__(self, w3: Web3, contract_address: str):
        self.w3 = w3
        self.address = contract_address
        self.contract = self._init_contract()

    @abstractmethod
    def _init_contract(self):
        """Инициализация контракта"""
        pass

    @staticmethod
    def _load_abi(protocol_name: str) -> list:
        """Загрузка ABI из файла"""
        import json
        with open(f"abis/{protocol_name}.json") as f:
            return json.load(f)

    def _call_contract(self, function_name: str, *args):
        """Безопасный вызов контракта"""
        try:
            return getattr(self.contract.functions, function_name)(*args).call()
        except Exception as e:
            raise ProtocolError(f"Contract call failed: {str(e)}")
