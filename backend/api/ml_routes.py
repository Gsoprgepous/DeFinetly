from fastapi import APIRouter, UploadFile
from ml_models.gnn.model import ValidatorGNN
from ml_models.nlp.code_analyzer import CodeRiskAnalyzer
import json

router = APIRouter()
gnn_model = ValidatorGNN()
code_analyzer = CodeRiskAnalyzer()

@router.post("/gnn/predict")
async def predict_risk(graph_data: dict):
    return gnn_model.predict_risk(graph_data)

@router.post("/code/analyze")
async def analyze_code(file: UploadFile):
    content = await file.read()
    return {
        "overall_risk": code_analyzer.analyze_contract(content.decode()),
        "vulnerabilities": code_analyzer.detect_vulnerabilities(content.decode())
    }
