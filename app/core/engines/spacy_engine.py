from typing import List, Dict, Any
import spacy
from app.core.engines.base import BaseEngine

class SpacyNerEngine(BaseEngine):
    def __init__(self) -> None:
        self.nlp = spacy.load("pt_core_news_lg")

    def detect(self, text: str) -> List[Dict[str, Any]]:
        doc = self.nlp(text)
        entities = []
        for ent in doc.ents:
            if ent.label_ in ["PER", "LOC", "ORG"]:
                entities.append({
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "text": ent.text,
                    "label": ent.label_,
                    "engine": "Spacy"
                })
        return entities

    def anonymize(self, text: str) -> tuple[str, List[Dict[str, Any]]]:
        entities = self.detect(text)
        entities_sorted = sorted(entities, key=lambda e: e["start"], reverse=True)
        anonymized_text = text

        for ent in entities_sorted:
            anonymized_text = (
                anonymized_text[:ent["start"]]
                + f"[{ent['label']}_ANONIMIZADO]"
                + anonymized_text[ent["end"]:]
            )

        clean_entities = [
            {"text": e["text"], "label": e["label"], "engine": e["engine"]}
            for e in reversed(entities_sorted)
        ]
        return anonymized_text, clean_entities