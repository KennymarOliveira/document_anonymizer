import re
from typing import List, Dict, Any
from app.core.engines.base import BaseEngine

class RegexEngine(BaseEngine):
    def __init__(self) -> None:
        self.patterns = {
            "CPF": r"\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11}",
            "CNPJ": r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14}",
            "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        }

    def anonymize(self, text: str) -> tuple[str, List[Dict[str, Any]]]:
        entities = []
        anonymized_text = text

        for label, pattern in self.patterns.items():
            for match in re.finditer(pattern, text):
                entity_text = match.group()
                entities.append({"text": entity_text, "label": label, "engine": "Regex"})
                anonymized_text = anonymized_text.replace(entity_text, f"[{label}_ANONIMIZADO]")

        return anonymized_text, entities