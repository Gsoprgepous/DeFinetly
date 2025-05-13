import ast
from typing import Dict, List, Tuple
import re
import logging
from pathlib import Path
from slither import Slither
from slither.detectors import all_detectors
from slither.core.declarations import Contract
from crytic_compile import cryticparser
from semantic_version import Version

logger = logging.getLogger(__name__)

class AdvancedSecurityDetector:
    """анализ безопасности для смарт-контрактов"""
    
    def __init__(self):
        self.compiler_version = None
        self.detectors_config = self._load_detectors_config()
        
    def _load_detectors_config(self) -> Dict:
        """Загружает конфигурацию детекторов из YAML"""
        config_path = Path(__file__).parent / "detectors_config.yml"
        try:
            import yaml
            with open(config_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load detectors config: {e}")
            return {}

    def analyze_contract(self, contract_path: str) -> Dict:
        """Полный анализ контракта"""
        results = {
            "vulnerabilities": [],
            "security_metrics": {},
            "gas_optimizations": [],
            "compliance": {}
        }
        
        try:
            # Инициализация Slither настройками
            slither = self._init_slither(contract_path)
            
            # Основной анализ
            results.update(self._run_detectors(slither))
            
            # Дополнительные проверки
            results["vulnerabilities"].extend(
                self._check_upgrade_patterns(slither))
            results["gas_optimizations"].extend(
                self._analyze_gas_usage(slither))
            results["compliance"] = self._check_standards_compliance(slither)
            
            # Анализ зависимостей
            results["dependencies"] = self._analyze_dependencies(slither)
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            
        return results

    def _init_slither(self, contract_path: str) -> Slither:
        """Инициализация с кастомными параметрами"""
        args = cryticparser.init(
            [
                contract_path,
                "--solc-solcs-select", "0.8.25",  
                "--json", "-",
                "--exclude-dependencies",
                "--filter-paths", "node_modules"
            ],
            "SmartGuard.AI Analysis"
        )
        return Slither(contract_path, **vars(args))

    def _run_detectors(self, slither: Slither) -> Dict:
        """Запуск кастомных и стандартных детекторов"""
        results = {"vulnerabilities": []}
        
        # Стандартные детекторы Slither
        for detector_class in all_detectors:
            detector = detector_class(slither)
            detector.detect()
            if detector.results:
                results["vulnerabilities"].extend(self._format_findings(detector.results))
        
        # детекторы
        results["vulnerabilities"].extend(self._detect_custom_issues(slither))
        
        return results

    def _detect_custom_issues(self, slither: Slither) -> List[Dict]:
        """Обнаружение специфичных для DeFi уязвимостей"""
        findings = []
        
        for contract in slither.contracts:
            # Проверка на backdoor-функции
            findings.extend(self._detect_backdoors(contract))
            
            # Проверка на неправильные математические операции
            findings.extend(self._detect_math_issues(contract))
            
            # Проверка интеграций с Oracle
            findings.extend(self._check_oracle_usage(contract))
            
        return findings

    def _detect_backdoors(self, contract: Contract) -> List[Dict]:
        """Поиск скрытых backdoor-функций"""
        backdoor_patterns = [
            (r"function\s+emergencyStop\(\)", "Emergency stop without timelock"),
            (r"function\s+upgradeTo\(address\)", "Upgrade pattern without authorization"),
            (r"\.call\(.*abi\.encodeWithSelector\(0x[0-9a-f]{8}", "Low-level call with selector")
        ]
        
        findings = []
        for pattern, description in backdoor_patterns:
            if re.search(pattern, contract.source_code):
                findings.append({
                    "check": "Backdoor Pattern",
                    "description": description,
                    "severity": "High",
                    "contract": contract.name
                })
        return findings

    def _analyze_gas_usage(self, slither: Slither) -> List[Dict]:
        """Анализ оптимизации"""
        gas_issues = []
        
        for function in slither.functions:
            # Проверка на дорогие циклы
            if any("for(" in node.source_mapping.content for node in function.nodes):
                gas_issues.append({
                    "issue": "Expensive loop",
                    "function": function.name,
                    "recommendation": "Consider using mappings instead"
                })
                
            # Проверка на повторяющиеся операции
            storage_access = sum(1 for node in function.nodes if "SLOAD" in str(node))
            if storage_access > 5:
                gas_issues.append({
                    "issue": "Excessive storage reads",
                    "function": function.name,
                    "count": storage_access
                })
                
        return gas_issues

    def _check_standards_compliance(self, slither: Slither) -> Dict:
        """Проверка соответствия стандартам (ERC-20, ERC-721 и т.д.)"""
        standards = {
            "ERC20": ["totalSupply", "balanceOf", "transfer"],
            "ERC721": ["ownerOf", "safeTransferFrom"]
        }
        
        compliance = {}
        for contract in slither.contracts:
            for standard, funcs in standards.items():
                compliance[standard] = all(
                    any(f.name == func for f in contract.functions)
                    for func in funcs
                )
        return compliance

    def _analyze_dependencies(self, slither: Slither) -> Dict:
        """Анализ зависимостей и их версий"""
        deps = {}
        for contract in slither.contracts:
            if "@openzeppelin" in contract.source_mapping.filename.absolute:
                version = self._extract_oz_version(contract.source_code)
                deps["OpenZeppelin"] = version
        return deps

    def _extract_oz_version(self, code: str) -> str:
        """Извлекает версию OpenZeppelin из кода"""
        match = re.search(r"@openzeppelin/contracts@(\d+\.\d+\.\d+)", code)
        return match.group(1) if match else "unknown"
