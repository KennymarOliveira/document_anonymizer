from typing import List, Dict, Any
from app.core.engines.base import BaseEngine

class HybridEngine(BaseEngine):
    def __init__(self, engines: List[BaseEngine]) -> None:
        self.engines = engines

    def detect(self, text: str) -> List[Dict[str, Any]]:
        all_candidates: List[Dict[str, Any]] = []
        for engine in self.engines:
            all_candidates.extend(engine.detect(text))

        all_candidates.sort(key=lambda c: (c["start"], -(c["end"] - c["start"])))

        selected_entities: List[Dict[str, Any]] = []
        last_end = -1
        for ent in all_candidates:
            if ent["start"] < last_end:
                continue
            selected_entities.append(ent)
            last_end = ent["end"]

        return selected_entities

    def anonymize(self, text: str) -> tuple[str, List[Dict[str, Any]]]:
        selected_entities = self.detect(text)

        anonymized_text = text
        for ent in reversed(selected_entities):
            label_tag = f"[{ent['label'].upper()}_ANONIMIZADO]"
            anonymized_text = (
                anonymized_text[:ent["start"]]
                + label_tag
                + anonymized_text[ent["end"]:]
            )

        clean_entities = [
            {"text": e["text"], "label": e["label"], "engine": e["engine"]}
            for e in selected_entities
        ]

        return anonymized_text, clean_entities