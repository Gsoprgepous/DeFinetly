import numpy as np
from dataclasses import dataclass
from web3.contract import Contract

@dataclass
class PoolMetrics:
    tvl: float
    volume_24h: float
    fee_apr: float
    impermanent_loss: float

class UniswapPoolAnalyzer:
    def __init__(self, pool_contract: Contract):
        self.pool = pool_contract

    def calculate_metrics(self) -> PoolMetrics:
        slot0 = self.pool.functions.slot0().call()
        liquidity = self.pool.functions.liquidity().call()
        
        return PoolMetrics(
            tvl=self._calculate_tvl(slot0, liquidity),
            volume_24h=self._estimate_volume(),
            fee_apr=self._calculate_apr(),
            impermanent_loss=self._calc_il_risk()
        )

    def _calculate_tvl(self, slot0, liquidity) -> float:
        """Расчет Total Value Locked"""
        sqrt_price = slot0[0]
        price = (sqrt_price ** 2) / (2 ** 192)
        return liquidity * price / 1e18
