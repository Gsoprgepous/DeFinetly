from web3 import Web3
from .schemas import ReserveData, UserPosition

class AaveV3Lending:
    def __init__(self, w3: Web3, lending_pool_address: str):
        self.w3 = w3
        self.pool_abi = self._load_abi("aave_v3_pool")
        self.pool = w3.eth.contract(
            address=lending_pool_address,
            abi=self.pool_abi
        )

    def get_reserve_data(self, asset_address: str) -> ReserveData:
        """Получение данных резерва"""
        data = self.pool.functions.getReserveData(asset_address).call()
        return ReserveData(
            available_liquidity=data[0],
            total_debt=data[1],
            liquidity_rate=data[2],
            variable_borrow_rate=data[3]
        )

    def get_user_position(self, user_address: str) -> UserPosition:
        """Позиция пользователя"""
        reserves = self.pool.functions.getUserReservesData(user_address).call()
        return UserPosition(
            supplied=[(r[0], r[1]) for r in reserves[0]],
            borrowed=[(r[0], r[1]) for r in reserves[1]]
        )
