from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

class CodeRiskAnalyzer:
    def __init__(self, model_path: str = "microsoft/codebert-base"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path).to(self.device)

    def analyze_contract(self, solidity_code: str) -> dict:
        inputs = self.tokenizer(
            solidity_code,
            truncation=True,
            padding=True,
            max_length=512,
            return_tensors="pt"
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)

        return {
            "safe": probs[0][0].item(),
            "risky": probs[0][1].item(),
            "critical": probs[0][2].item()
        }

    def detect_vulnerabilities(self, code: str) -> list:
        """Поиск конкретных уязвимостей"""
        results = []
        patterns = {
            "reentrancy": ["call.value", "send(", "transfer("],
            "overflow": ["unchecked", "++", "--"],
            "access_control": ["tx.origin", "public"]
        }

        for vuln_type, keywords in patterns.items():
            if any(keyword in code for keyword in keywords):
                results.append(vuln_type)

        return results
