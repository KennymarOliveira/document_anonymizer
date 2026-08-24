import re
from typing import List, Dict, Any
from app.core.engines.base import BaseEngine

class RegexEngine(BaseEngine):
    def __init__(self) -> None:
        self.patterns = {
            "CPF": r"(?<!\d)(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11})(?!\d)",
            "CNPJ": r"(?<!\d)(?:\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14})(?!\d)",
            "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        }

    def detect(self, text: str) -> List[Dict[str, Any]]:
        candidates = []
        for label, pattern in self.patterns.items():
            for match in re.finditer(pattern, text):
                candidates.append({
                    "start": match.start(),
                    "end": match.end(),
                    "text": match.group(),
                    "label": label,
                    "engine": "Regex"
                })

        candidates.sort(key=lambda c: (c["start"], -(c["end"] - c["start"])))

        selected: List[Dict[str, Any]] = []
        last_end = -1
        for ent in candidates:
            if ent["start"] < last_end:
                continue
            selected.append(ent)
            last_end = ent["end"]

        return selected

    def anonymize(self, text: str) -> tuple[str, List[Dict[str, Any]]]:
        matches = self.detect(text)

        anonymized_text = text
        for ent in reversed(matches):
            anonymized_text = (
                anonymized_text[:ent["start"]]
                + f"[{ent['label']}_ANONIMIZADO]"
                + anonymized_text[ent["end"]:]
            )

        clean_entities = [
            {"text": e["text"], "label": e["label"], "engine": e["engine"]}
            for e in matches
        ]

        return anonymized_text, clean_entities