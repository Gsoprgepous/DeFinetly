import ctypes
import json
from typing import Optional
from pydantic import BaseModel

class MevAlert(BaseModel):
    alert_type: str
    profit_eth: float
    details: dict

class RustDetector:
    def __init__(self):
        self.lib = ctypes.CDLL("./target/release/libmevdetector.so")
        
        # Настройка типов
        self.lib.frontrun_detect.argtypes = [
            ctypes.c_char_p,  # tx_json
            ctypes.c_char_p   # rpc_url
        ]
        self.lib.frontrun_detect.restype = ctypes.c_void_p
        
        self.lib.free_alert.argtypes = [ctypes.c_void_p]

    def detect_frontrun(self, tx_hash: str, rpc_url: str) -> Optional[MevAlert]:
        tx_data = self._fetch_tx(tx_hash, rpc_url)
        tx_json = json.dumps(tx_data).encode('utf-8')
        
        ptr = self.lib.frontrun_detect(
            ctypes.c_char_p(tx_json),
            ctypes.c_char_p(rpc_url.encode())
        )
        
        if ptr:
            alert = self._parse_alert(ptr)
            self.lib.free_alert(ptr)
            return alert
        return None

    def _parse_alert(self, ptr) -> MevAlert:
        # Реализация парсинка из C-структуры
        pass
