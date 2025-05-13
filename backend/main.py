from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging
from enum import Enum
import httpx
from web3 import Web3
import networkx as nx
import json
from datetime import datetime

# Логгер
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backend/logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Модели
class Blockchain(str, Enum):
    ETHEREUM = "ethereum"
    BSC = "bsc"
    POLYGON = "polygon"
    TRON = "tron"

class Protocol(str, Enum):
    UNISWAP = "uniswap"
    AAVE = "aave"
    COMPOUND = "compound"
    OTHER = "other"

class ContractAnalysisRequest(BaseModel):
    address: str
    blockchain: Blockchain
    protocol: Optional[Protocol] = None
    compare_with: Optional[str] = None

class VulnerabilityReport(BaseModel):
    severity: str
    description: str
    recommendation: str

class ContractAnalysisResponse(BaseModel):
    risk_score: float
    vulnerabilities: List[VulnerabilityReport]
    contract_graph: Dict
    summary: str
    last_updated: datetime
    protocol_info: Optional[Dict] = None

# Инициализация FastAPI
app = FastAPI(
    title="SmartGuard.AI API",
    description="API для анализа и мониторинга DeFi протоколов и смарт-контрактов",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Настройки CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API ключ
api_key_header = APIKeyHeader(name="X-API-KEY")

# Зависимости
async def get_api_key(api_key: str = Depends(api_key_header)):
    # проверяем API ключ
    return api_key

# подключаем клиентов для внешних API
etherscan_client = httpx.AsyncClient(base_url="https://api.etherscan.io/api")
bscscan_client = httpx.AsyncClient(base_url="https://api.bscscan.com/api")
defillama_client = httpx.AsyncClient(base_url="https://api.llama.fi")

# Web3
eth_w3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/YOUR_INFURA_KEY"))
bsc_w3 = Web3(Web3.HTTPProvider("https://bsc-dataseed.binance.org/"))

# Endpoints API
@app.get("/api/health", tags=["System"])
async def health_check():
    """Проверка работоспособности сервера"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow()
    }

@app.post("/api/analyze", response_model=ContractAnalysisResponse, tags=["Analysis"])
async def analyze_contract(
    request: ContractAnalysisRequest,
    api_key: str = Depends(get_api_key)
):
    """
    Анализ смарт-контрактов/DeFi протоколов
    """
    try:
        logger.info(f"Starting analysis for {request.address} on {request.blockchain}")
        
        # 1. Получение исходного кода контракта
        source_code = await get_contract_source(request.address, request.blockchain)
        
        # 2. проверка безопасности
        security_report = await analyze_security(source_code, request.blockchain)
        
        # 3. граф взаимодействий
        contract_graph = build_contract_graph(request.address, request.blockchain)
        
        # 4. Получение информации о протоколе
        protocol_info = None
        if request.protocol:
            protocol_info = await get_protocol_info(request.protocol)
        
        # 5. Сравнение версий 
        diff_report = None
        if request.compare_with:
            diff_report = await compare_versions(request.address, request.compare_with, request.blockchain)
        
        return {
            "risk_score": security_report["score"],
            "vulnerabilities": security_report["vulnerabilities"],
            "contract_graph": contract_graph,
            "summary": generate_summary(security_report, protocol_info),
            "last_updated": datetime.utcnow(),
            "protocol_info": protocol_info,
            "diff_report": diff_report
        }
        
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/protocols", tags=["Protocols"])
async def list_supported_protocols():
    """Возвращает список поддерживаемых DeFi протоколов"""
    return {
        "protocols": [
            {"name": "Uniswap", "id": "uniswap", "blockchains": ["ethereum", "polygon"]},
            {"name": "Aave", "id": "aave", "blockchains": ["ethereum", "avalanche"]},
            {"name": "Compound", "id": "compound", "blockchains": ["ethereum"]}
        ]
    }

# доп функции
async def get_contract_source(address: str, blockchain: Blockchain):
    """Получает исходный код контракта из блокчейн-эксплорера"""
    if blockchain == Blockchain.ETHEREUM:
        params = {
            "module": "contract",
            "action": "getsourcecode",
            "address": address,
            "apikey": "YOUR_ETHERSCAN_API_KEY"
        }
        response = await etherscan_client.get("", params=params)
        return response.json()["result"][0]["SourceCode"]
    elif blockchain == Blockchain.BSC:
        params = {
            "module": "contract",
            "action": "getsourcecode",
            "address": address,
            "apikey": "YOUR_BSCSCAN_API_KEY"
        }
        response = await bscscan_client.get("", params=params)
        return response.json()["result"][0]["SourceCode"]
    else:
        raise NotImplementedError(f"Blockchain {blockchain} not supported yet")

async def analyze_security(source_code: str, blockchain: Blockchain):
    """Анализирует код на уязвимости"""
    # Здесь должна быть интеграция с инстументами для анализа смарт-контрактов. А это очень упрощенная реализация для демонстрации
    
    vulnerabilities = []
    
    # Проверка на реентерабельность
    if "call.value" in source_code and not "require" in source_code:
        vulnerabilities.append({
            "severity": "high",
            "description": "Potential reentrancy vulnerability",
            "recommendation": "Use checks-effects-interactions pattern"
        })
    
    # проверка подлинности транзакции в смарт-контрактах Ethereum
    if "tx.origin" in source_code:
        vulnerabilities.append({
            "severity": "medium",
            "description": "Use of tx.origin for authorization",
            "recommendation": "Replace tx.origin with msg.sender"
        })
    
    # Расчет общей оценки риска
    score = min(1.0, len(vulnerabilities) * 0.2)
    
    return {
        "score": score,
        "vulnerabilities": vulnerabilities
    }

def build_contract_graph(address: str, blockchain: Blockchain):
    """Строит граф взаимодействий контракта"""
    # Здесь должна быть реальная логика построения графа
    # Это упрощенная реализация для демонстрации
    
    G = nx.DiGraph()
    G.add_node(address, type="main", label="Main Contract")

    G.add_node(f"{address}_token", type="token", label="Token Contract")
    G.add_node(f"{address}_oracle", type="oracle", label="Oracle")
    
    G.add_edge(address, f"{address}_token", label="transfer")
    G.add_edge(address, f"{address}_oracle", label="getPrice")
    
    # Конвертируем в JSON для фронтенда
    return {
        "nodes": [{"id": n, **G.nodes[n]} for n in G.nodes()],
        "edges": [{"from": u, "to": v, "label": G.edges[u, v]["label"]} for u, v in G.edges()]
    }

async def get_protocol_info(protocol: Protocol):
    """Получает информацию о DeFi протоколе"""
    if protocol == Protocol.UNISWAP:
        response = await defillama_client.get("/protocol/uniswap")
        return response.json()
    elif protocol == Protocol.AAVE:
        response = await defillama_client.get("/protocol/aave")
        return response.json()
    else:
        return None

def generate_summary(security_report, protocol_info):
    """текстовое описание результатов анализа"""
    vuln_count = len(security_report["vulnerabilities"])
    risk_level = "low" if security_report["score"] < 0.3 else "medium" if security_report["score"] < 0.7 else "high"
    
    summary = f"Contract security analysis completed. Found {vuln_count} vulnerabilities. "
    summary += f"Overall risk level: {risk_level}."
    
    if protocol_info:
        summary += f" Protocol TVL: ${protocol_info.get('tvl', 0):,.2f}."
    
    return summary

async def compare_versions(
    address1: str, 
    address2: str, 
    blockchain: Blockchain
) -> Dict[str, List[Dict[str, str]]:
    """
    Сравнивает две версии смарт-контракта и возвращает различия.
    
    Параметры:
        address1: Адрес старой версии контракта
        address2: Адрес новой версии контракта
        blockchain: Блокчейн (ethereum, bsc и т.д.)
    
    Возвращает:
        {
            "changes": [
                {"type": "function_added", "name": "newFunction", "details": "..."},
                {"type": "modifier_changed", "name": "onlyOwner", "old_value": "...", "new_value": "..."}
            ]
        }
    """
    # 1. Получаем исходный код обеих версий
    source1 = await get_contract_source(address1, blockchain)
    source2 = await get_contract_source(address2, blockchain)
    
    # 2. Парсим ABI и структуры контрактов
    abi1 = parse_abi(source1)
    abi2 = parse_abi(source2)
    
    # 3. Анализируем различия
    changes = []
    
    # Сравнение функций
    funcs1 = {f['name']: f for f in abi1 if f['type'] == 'function'}
    funcs2 = {f['name']: f for f in abi2 if f['type'] == 'function'}
    
    # Добавленные функции
    for name in funcs2.keys() - funcs1.keys():
        changes.append({
            "type": "function_added",
            "name": name,
            "details": f"New function with {len(funcs2[name]['inputs'])} params"
        })
    
    # Удаленные функции
    for name in funcs1.keys() - funcs2.keys():
        changes.append({
            "type": "function_removed",
            "name": name
        })
    
    # Измененные функции
    for name in funcs1.keys() & funcs2.keys():
        if funcs1[name] != funcs2[name]:
            diff = find_abi_diff(funcs1[name], funcs2[name])
            changes.append({
                "type": "function_changed",
                "name": name,
                "details": diff
            })
    
    # 4. Сравнение модификаторов 
    # to be continued ...
    
    # 5. Сравнение событий (Events)
    # ...
    
    return {"changes": changes}

# Вспомогательные функции
def parse_abi(source_code: str) -> List[Dict]:
    """Парсит ABI из исходного кода контракта"""
    #Например парсинг через solc или аналоги
    return [...]  # Пример: [{"type": "function", "name": "transfer", ...}]

def find_abi_diff(item1: Dict, item2: Dict) -> str:
    """Находит различия между двумя элементами ABI"""
    diffs = []
    for key in set(item1.keys()) | set(item2.keys()):
        if item1.get(key) != item2.get(key):
            diffs.append(f"{key}: {item1.get(key)} → {item2.get(key)}")
    return "; ".join(diffs)

# Обработчики событий
@app.on_event("startup")
async def startup_event():
    logger.info("Starting SmartGuard.AI API server")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down SmartGuard.AI API server")
    await etherscan_client.aclose()
    await bscscan_client.aclose()
    await defillama_client.aclose()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
