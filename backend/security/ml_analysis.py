import logging
import numpy as np
import torch
import onnxruntime as ort
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from enum import Enum
import json
from pathlib import Path

from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    BitsAndBytesConfig,
    pipeline
)
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import pinecone  # Для векторного поиска
import tensorflow as tf  # Для анализа байткода
from web3 import Web3

logger = logging.getLogger(__name__)

class AnalysisMode(Enum):
    CODE = 1
    BYTECODE = 2
    BOTH = 3

class MLSecurityAnalyzer:

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._init_models()
        self._init_vector_db()
        self._load_known_attacks()
        self.executor = ThreadPoolExecutor(max_workers=8)
        self.w3 = Web3()

    def _init_models(self):
        """Инициализация всех ML моделей с квантованием"""
        self.quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4"
        )

        self.models = {
            "code_analysis": self._load_huggingface_model(
                "microsoft/codebert-base-mlm",
                "text-classification"
            ),
            "bytecode_analysis": self._load_onnx_model(
                "models/bytecode_analyzer.onnx"
            ),
            "explanation": self._load_huggingface_model(
                "mistralai/Mistral-7B-Instruct-v0.1",
                "text-generation",
                quant=self.quant_config
            ),
            "anomaly": self._load_tf_model(
                "models/anomaly_detector.h5"
            )
        }

    def _load_huggingface_model(self, model_name: str, task: str, quant=None):
        """Загрузка HF модели с обработкой ошибок"""
        try:
            return pipeline(
                task,
                model=model_name,
                device=self.device,
                model_kwargs={"quantization_config": quant} if quant else None,
                torch_dtype=torch.float16 if self.device == "cuda" else None
            )
        except Exception as e:
            logger.error(f"Failed to load {model_name}: {str(e)}")
            return None

    def _load_onnx_model(self, path: str):
        """Загрузка ONNX"""
        try:
            return ort.InferenceSession(
                path,
                providers=['CUDAExecutionProvider' if self.device == "cuda" else 'CPUExecutionProvider']
            )
        except Exception as e:
            logger.error(f"Failed to load ONNX model {path}: {str(e)}")
            return None

    def _load_tf_model(self, path: str):
        try:
            return tf.keras.models.load_model(path)
        except Exception as e:
            logger.error(f"Failed to load TF model {path}: {str(e)}")
            return None

    def _init_vector_db(self):
        """Инициализация Pinecone для векторного поиска"""
        try:
            pinecone.init(api_key="YOUR_PINECONE_KEY", environment="us-west1-gcp")
            self.vector_db = pinecone.Index("smart-contracts")
        except Exception as e:
            logger.error(f"Pinecone init failed: {str(e)}")
            self.vector_db = None

    def _load_known_attacks(self):
        """Загрузка известных атак"""
        try:
            with open("data/known_attacks.json") as f:
                self.known_attacks = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load attacks DB: {str(e)}")
            self.known_attacks = []

    async def full_analysis(self, contract: Dict, mode: AnalysisMode = AnalysisMode.BOTH) -> Dict:
        """Полный анализ контракта"""
        analysis = {
            "code_analysis": {},
            "bytecode_analysis": {},
            "similar_contracts": [],
            "known_attack_patterns": [],
            "risk_score": 0.0,
            "explanations": []
        }

        # Параллельный запуск анализаторов
        futures = []
        if mode in [AnalysisMode.CODE, AnalysisMode.BOTH] and "source_code" in contract:
            futures.append(self.executor.submit(
                self.analyze_source_code,
                contract["source_code"]
            ))

        if mode in [AnalysisMode.BYTECODE, AnalysisMode.BOTH] and "bytecode" in contract:
            futures.append(self.executor.submit(
                self.analyze_bytecode,
                contract["bytecode"]
            ))

        if self.vector_db:
            futures.append(self.executor.submit(
                self.find_similar_contracts,
                contract["source_code"] if "source_code" in contract else contract["bytecode"]
            ))

        # Обработка результатов
        for future in futures:
            try:
                result = future.result(timeout=120)
                analysis.update(result)
            except Exception as e:
                logger.warning(f"Analysis part failed: {str(e)}")

        # Дополнительные проверки
        analysis["known_attack_patterns"] = self._check_attack_patterns(
            analysis.get("code_analysis", {}),
            analysis.get("bytecode_analysis", {})
        )

        analysis["risk_score"] = self._calculate_risk_score(analysis)
        analysis["explanations"] = self._generate_explanations(analysis)

        return analysis

    def analyze_source_code(self, code: str) -> Dict:
        """Анализ исходного кода"""
        result = {}
        
        # Анализ уязвимостей
        if self.models["code_analysis"]:
            vuln_result = self.models["code_analysis"](code[:8192], truncation=True)
            result["vulnerabilities"] = vuln_result

        # Эмбеддинги для поиска
        result["code_embeddings"] = self._get_code_embeddings(code)

        return {"code_analysis": result}

    def analyze_bytecode(self, bytecode: str) -> Dict:
        """Анализ байткода"""
        result = {}
        
        try:
            # Нормализация байткода
            clean_bytecode = self.w3.toHex(self.w3.toBytes(hexstr=bytecode))
            
            # ONNX модели
            if self.models["bytecode_analysis"]:
                inputs = {"bytecode": np.array([clean_bytecode], dtype=np.float32)}
                outputs = self.models["bytecode_analysis"].run(None, inputs)
                result["bytecode_analysis"] = outputs[0].tolist()

            # Анализ аномалий
            if self.models["anomaly"]:
                anomaly_score = self.models["anomaly"].predict(
                    np.array([clean_bytecode])
                )
                result["anomaly_score"] = float(anomaly_score[0])

        except Exception as e:
            logger.error(f"Bytecode analysis failed: {str(e)}")

        return {"bytecode_analysis": result}

    @lru_cache(maxsize=10000)
    def _get_code_embeddings(self, code: str) -> List[float]:
        """Генерация эмбеддингов кода с кешированием"""
        model = SentenceTransformer("all-mpnet-base-v2", device=self.device)
        return model.encode(code[:8192]).tolist()

    def find_similar_contracts(self, code_or_bytecode: str) -> Dict:
        """Поиск похожих контрактов в векторной БД"""
        if not self.vector_db:
            return {}
            
        try:
            # Для байткода специальные эмбеддинги
            if code_or_bytecode.startswith("0x"):
                embedding = self._get_bytecode_embeddings(code_or_bytecode)
            else:
                embedding = self._get_code_embeddings(code_or_bytecode)

            results = self.vector_db.query(
                vector=embedding,
                top_k=5,
                include_metadata=True
            )

            return {
                "similar_contracts": [
                    {
                        "address": match["metadata"]["address"],
                        "similarity": match["score"],
                        "type": match["metadata"]["type"]
                    }
                    for match in results["matches"]
                ]
            }
        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            return {}

    def _check_attack_patterns(self, code_analysis: Dict, bytecode_analysis: Dict) -> List[Dict]:
        """Проверка на известные шаблоны атак"""
        detected = []
        
        for attack in self.known_attacks:
            # Проверка по исходному коду
            if "code_pattern" in attack:
                if re.search(attack["code_pattern"], str(code_analysis)):
                    detected.append(attack)

            # Проверка по байткоду
            if "bytecode_pattern" in attack and bytecode_analysis:
                if attack["bytecode_pattern"] in str(bytecode_analysis):
                    detected.append(attack)

        return detected

    def _calculate_risk_score(self, analysis: Dict) -> float:
        """Вычисление риска"""
        score = 0.0
        
        # Веса для разных компонентов
        weights = {
            "code_vulnerabilities": 0.4,
            "bytecode_anomalies": 0.3,
            "attack_patterns": 0.2,
            "similar_contracts": 0.1
        }

        # Оценка на основе кода
        if "code_analysis" in analysis and "vulnerabilities" in analysis["code_analysis"]:
            score += weights["code_vulnerabilities"] * analysis["code_analysis"]["vulnerabilities"]["score"]

        # Оценка
        if "bytecode_analysis" in analysis and "anomaly_score" in analysis["bytecode_analysis"]:
            score += weights["bytecode_anomalies"] * analysis["bytecode_analysis"]["anomaly_score"]

        # Штраф 
        if analysis["known_attack_patterns"]:
            score += weights["attack_patterns"] * min(1.0, len(analysis["known_attack_patterns"]) * 0.5)

        # Корректировка
        if analysis["similar_contracts"]:
            avg_similarity = sum(
                c["similarity"] for c in analysis["similar_contracts"]
            ) / len(analysis["similar_contracts"])
            score += weights["similar_contracts"] * avg_similarity

        return min(1.0, score)

    def _generate_explanations(self, analysis: Dict) -> List[str]:
        """Генерация объяснений nlp"""
        explanations = []
        
        if not self.models["explanation"]:
            return explanations

        try:
            # Генерация объяснения для кода
            if "code_analysis" in analysis:
                prompt = f"""
                Analyze these code vulnerabilities:
                {json.dumps(analysis['code_analysis']['vulnerabilities'], indent=2)}
                
                Provide:
                1. Risk assessment
                2. Potential impact
                3. Recommended fixes
                """
                explanations.append(
                    self.models["explanation"](prompt, max_length=500)[0]["generated_text"]
                )

            # Генерация объяснения для байткода
            if "bytecode_analysis" in analysis:
                prompt = f"""
                Analyze these bytecode anomalies (score: {analysis['bytecode_analysis']['anomaly_score']}):
                {json.dumps(analysis['bytecode_analysis'], indent=2)}
                
                Explain potential issues in the bytecode.
                """
                explanations.append(
                    self.models["explanation"](prompt, max_length=500)[0]["generated_text"]
                )

        except Exception as e:
            logger.error(f"Explanation generation failed: {str(e)}")

        return explanations

ml_analyzer = MLSecurityAnalyzer()
